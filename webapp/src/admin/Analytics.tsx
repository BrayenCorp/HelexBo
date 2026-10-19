import { useState } from "react";
import { api } from "../api";
import { nf, pct, usd } from "../format";
import { Loading, useLoad } from "../ui";
import { Kpi } from "./parts";
import type { Overview } from "./parts";
import { pq, usePeriod } from "./shell";
import { DataTable } from "./table";

interface Retention { rows: { day: string; size: number; d1: Cell; d3: Cell; d7: Cell; d14: Cell; d30: Cell }[]; average: Record<string, number | null>; note: string }
type Cell = { pct: number | null; count: number } | null;
interface Funnel { cohort_size: number; stages: { stage: string; count: number; of_prev: number | null; of_total: number | null }[]; note: string }
interface PopRow { name: string; uses: number; users: number; credits: number; success_rate: number | null }
interface Popularity { categories: PopRow[]; styles: PopRow[]; templates: PopRow[]; freeform: PopRow }
interface Prov { model: string; generations: number; ok: number; errors: number; avg_seconds: number | null; cost_usd: number; cost_per_generation: number | null; credits: number; success_rate: number | null }
interface Revenue { money: Overview["money"]; arpu: number; arppu: number; payers: number; payers_all_time: number; conversion: number | null; note: string }
interface Bot { churned: number; returned: number; note: string }

const TABS: [string, string][] = [["users", "Пользователи"], ["gens", "Генерации"], ["money", "Деньги"], ["retention", "Удержание"], ["funnel", "Воронка"], ["pop", "Популярность"]];

function UsersTab() {
  const { period } = usePeriod();
  const q = pq(period);
  const sel = useLoad(() => api.admin.get<Overview>(`analytics/overview?${q}`), [q]);
  const d1 = useLoad(() => api.admin.get<Overview>("analytics/overview?period=today"), []);
  const d7 = useLoad(() => api.admin.get<Overview>("analytics/overview?period=7d"), []);
  const d30 = useLoad(() => api.admin.get<Overview>("analytics/overview?period=30d"), []);
  const bot = useLoad(() => api.admin.get<Bot>(`analytics/bot?${q}`), [q]);
  const rev = useLoad(() => api.admin.get<Revenue>(`analytics/revenue?${q}`), [q]);
  if (!sel.data) return <Loading />;
  const o = sel.data;
  return (
    <div className="kpi-groups">
      <Kpi title="Активность" big={nf(d1.data?.users.active ?? 0)} bigLabel="DAU — активных сегодня" orange rows={[["WAU — за 7 дней", nf(d7.data?.users.active ?? 0)], ["MAU — за 30 дней", nf(d30.data?.users.active ?? 0)]]} />
      <Kpi title="Пользователи за период" big={nf(o.users.total)} bigLabel="Всего" rows={[["Новые", nf(o.users.new)], ["Активные", nf(o.users.active)], ["Возвращающиеся", nf(o.users.returned)], ["Отток (не заходили 14 дн.)", nf(bot.data?.churned ?? 0)]]} />
      <Kpi title="Конверсия" big={pct(rev.data?.conversion)} bigLabel="В оплату (платящие / все пользователи)" rows={[["Платящих за всё время", nf(rev.data?.payers_all_time ?? 0)], ["Платящих за период", nf(rev.data?.payers ?? 0)]]} />
    </div>
  );
}

function GensTab() {
  const { period } = usePeriod();
  const q = pq(period);
  const ov = useLoad(() => api.admin.get<Overview>(`analytics/overview?${q}`), [q]);
  const pr = useLoad(() => api.admin.get<{ items: Prov[] }>(`analytics/providers?${q}`), [q]);
  if (!ov.data || !pr.data) return <Loading />;
  const g = ov.data.generations, items = pr.data.items;
  const ok = items.reduce((a, p) => a + (p.ok || 0), 0);
  const secs = items.filter((p) => p.avg_seconds !== null && p.ok);
  const avgSec = secs.length ? secs.reduce((a, p) => a + (p.avg_seconds as number) * p.ok, 0) / secs.reduce((a, p) => a + p.ok, 0) : null;
  const cost = items.reduce((a, p) => a + p.cost_usd, 0);
  return (
    <div className="kpi-groups">
      <Kpi title="Количество" big={nf(g.total)} bigLabel="Генераций за период" orange rows={[["Фото", nf(g.photo)], ["Видео", nf(g.video)], ["Успешных", nf(g.success)], ["Ошибок", nf(g.errors)], ["В обработке", nf(g.processing)]]} />
      <Kpi title="Качество и стоимость" big={pct(g.success + g.errors ? Math.round((g.success * 1000) / (g.success + g.errors)) / 10 : null)} bigLabel="Доля успешных"
        rows={[["Среднее время", avgSec !== null ? `${avgSec.toFixed(1)} с` : "Нет данных"], ["Расходы на AI", usd(cost)], ["Средняя стоимость", ok ? usd(cost / ok) : "Нет данных"]]} />
    </div>
  );
}

function MoneyTab() {
  const { period } = usePeriod();
  const q = pq(period);
  const r = useLoad(() => api.admin.get<Revenue>(`analytics/revenue?${q}`), [q]);
  if (!r.data) return <Loading />;
  const m = r.data;
  return (
    <>
      <div className="kpi-groups">
        <Kpi title="Выручка" big={`${nf(m.money.revenue_stars)} ⭐`} bigLabel="За период (реальные платежи)" orange rows={[["Покупок", nf(m.money.purchases)], ["Средний чек", `${nf(m.money.avg_check)} ⭐`], ["Платящих за период", nf(m.payers)]]} />
        <Kpi title="Доход на пользователя" big={`${m.arpu} ⭐`} bigLabel="ARPU — на всех пользователей" rows={[["ARPPU — на платящего", `${m.arppu} ⭐`], ["Конверсия в оплату", pct(m.conversion)]]} />
      </div>
      <p className="muted small">{m.note}</p>
    </>
  );
}

function RetentionTab() {
  const r = useLoad(() => api.admin.get<Retention>("analytics/retention?days=30"), []);
  if (!r.data) return <Loading />;
  const cell = (c: Cell) => (c === null ? <td className="heat none">—</td> : <td className="heat" style={{ background: `rgba(17,17,17,${Math.min(0.85, (c.pct ?? 0) / 100)})`, color: (c.pct ?? 0) > 45 ? "#fff" : "#111" }} title={`${c.count} польз.`}>{pct(c.pct)}</td>);
  return (
    <>
      <div className="table-wrap"><table className="tbl" style={{ minWidth: 520 }}>
        <thead><tr><th>Когорта (регистрация)</th><th className="num">Пользователей</th><th>1 день</th><th>3 дня</th><th>7 дней</th><th>14 дней</th><th>30 дней</th></tr></thead>
        <tbody>
          <tr><td><b>В среднем</b></td><td className="num">—</td>{(["d1", "d3", "d7", "d14", "d30"] as const).map((k) => <td key={k} className="heat">{pct(r.data!.average[k])}</td>)}</tr>
          {r.data.rows.map((row) => (<tr key={row.day}><td>{row.day}</td><td className="num">{nf(row.size)}</td>{cell(row.d1)}{cell(row.d3)}{cell(row.d7)}{cell(row.d14)}{cell(row.d30)}</tr>))}
          {r.data.rows.length === 0 && <tr><td colSpan={7} className="center muted" style={{ padding: 28 }}>Нет данных</td></tr>}
        </tbody>
      </table></div>
      <p className="muted small">{r.data.note} «—» — нужный день ещё не наступил.</p>
    </>
  );
}

function FunnelTab() {
  const { period } = usePeriod();
  const q = pq(period);
  const f = useLoad(() => api.admin.get<Funnel>(`analytics/funnel?${q}`), [q]);
  if (!f.data) return <Loading />;
  const max = Math.max(1, ...f.data.stages.map((s) => s.count));
  return (
    <div className="card">
      <p className="muted small">Пользователей, зарегистрированных за период: {nf(f.data.cohort_size)}</p>
      {f.data.stages.map((s) => (
        <div key={s.stage} className="funnel-row">
          <b>{s.stage}</b><div className="funnel-bar"><i style={{ width: `${(s.count / max) * 100}%` }} /></div>
          <span><b>{nf(s.count)}</b> <span className="muted small">· {pct(s.of_total)} от всех{s.of_prev !== null && s.of_prev <= 100 ? `, ${pct(s.of_prev)} от предыдущего` : ""}</span></span>
        </div>
      ))}
      <p className="muted small">{f.data.note}</p>
    </div>
  );
}

function PopTab() {
  const { period } = usePeriod();
  const q = pq(period);
  const p = useLoad(() => api.admin.get<Popularity>(`analytics/popularity?${q}`), [q]);
  if (!p.data) return <Loading />;
  const cols = (title: string) => [
    { key: "name", title, render: (r: PopRow) => <b>{r.name}</b> },
    { key: "uses", title: "Использований", num: true, render: (r: PopRow) => nf(r.uses) },
    { key: "users", title: "Пользователей", num: true, render: (r: PopRow) => nf(r.users) },
    { key: "credits", title: "Потрачено токенов", num: true, render: (r: PopRow) => nf(r.credits) },
    { key: "success_rate", title: "Успешность", num: true, render: (r: PopRow) => pct(r.success_rate) },
  ];
  return (
    <>
      <div className="card"><h2>Популярные категории</h2><DataTable rows={p.data.categories} cols={cols("Категория")} empty="Нет данных" /></div>
      <div className="card"><h2>Популярные стили</h2><DataTable rows={p.data.styles} cols={cols("Стиль")} empty="Нет данных" /></div>
      <div className="card"><h2>Популярные шаблоны</h2><DataTable rows={p.data.templates} cols={cols("Шаблон")} empty="Нет данных" /></div>
      <div className="card"><h2>Свободная генерация</h2><DataTable rows={[p.data.freeform]} cols={cols("Режим")} /></div>
    </>
  );
}

export function Analytics() {
  const [tab, setTab] = useState("users");
  return (
    <>
      <div className="tabs-line">{TABS.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === "users" && <UsersTab />}{tab === "gens" && <GensTab />}{tab === "money" && <MoneyTab />}{tab === "retention" && <RetentionTab />}{tab === "funnel" && <FunnelTab />}{tab === "pop" && <PopTab />}
    </>
  );
}

