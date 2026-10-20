import { useEffect, useState } from "react";
import { api } from "../api";
import { Payments } from "./Lists";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import { fmtShort, nf, pct, usd } from "../format";
import { ErrorBox, Loading, useLoad } from "../ui";
import { BarChart, LineChart, palette } from "./charts";
import { Field, ListRow, TextInput, errText } from "./kit";
import { ChartCard, ExportButton, Kpi } from "./parts";
import type { Overview, SeriesData } from "./parts";
import { pq, usePeriod } from "./shell";
import { DataTable } from "./table";

/* ---------- Выручка ---------- */
interface RevenueReport { money: Overview["money"]; all_time_stars: number; arpu: number; arppu: number; payers: number; payers_all_time: number; conversion: number | null; by_product: { name: string; purchases: number; revenue: number }[]; by_method: { method: string; currency: string; purchases: number; revenue: number }[]; note: string }

export function Revenue() {
  const { period } = usePeriod();
  const q = pq(period);
  const r = useLoad(() => api.admin.get<RevenueReport>(`analytics/revenue?${q}`), [q]);
  const s = useLoad(() => api.admin.get<SeriesData>(`analytics/series?${q}`), [q]);
  if (!r.data) return r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : <Loading />;
  const m = r.data;
  return (
    <>
      <div className="toolbar"><span style={{ flex: 1 }} /><ExportButton kind="revenue" label="Экспорт выручки по дням" /></div>
      <div className="kpi-groups">
        <Kpi title="Выручка" big={`${nf(m.money.revenue_stars)} ⭐`} bigLabel={`≈ ${usd(m.money.revenue_usd_estimate)} за период (оценка)`} orange
          rows={[["Сегодня", `${nf(m.money.today)} ⭐`], ["7 дней", `${nf(m.money.d7)} ⭐`], ["30 дней", `${nf(m.money.d30)} ⭐`], ["За всё время", `${nf(m.all_time_stars)} ⭐`]]} />
        <Kpi title="Покупки" big={nf(m.money.purchases)} bigLabel="За период" rows={[["Средний чек", `${nf(m.money.avg_check)} ⭐`], ["Платящих за период", nf(m.payers)], ["Платящих за всё время", nf(m.payers_all_time)]]} />
        <Kpi title="Доход на пользователя" big={`${m.arpu} ⭐`} bigLabel="ARPU" rows={[["ARPPU", `${m.arppu} ⭐`], ["Конверсия в оплату", pct(m.conversion)]]} />
      </div>
      {s.data && (
        <div className="charts">
          <ChartCard title="Выручка по дням, Stars"><BarChart days={s.data.days} series={{ name: "Выручка", color: palette.orange, values: s.data.revenue }} /></ChartCard>
          <ChartCard title="Количество покупок"><LineChart days={s.data.days} series={[{ name: "Покупок", color: palette.black, values: s.data.purchases }]} /></ChartCard>
        </div>
      )}
      <div className="card"><h2>Выручка по продуктам</h2>
        <DataTable rows={m.by_product} empty="Нет данных" cols={[{ key: "name", title: "Продукт", render: (r) => <b>{r.name}</b> }, { key: "purchases", title: "Покупок", num: true }, { key: "revenue", title: "Выручка, ⭐", num: true, render: (r) => nf(r.revenue) }]} /></div>
      <div className="card"><h2>Выручка по способам оплаты</h2>
        <DataTable rows={m.by_method} empty="Нет данных" cols={[{ key: "method", title: "Способ", render: (r) => <b>{r.method}</b> }, { key: "currency", title: "Валюта" }, { key: "purchases", title: "Покупок", num: true }, { key: "revenue", title: "Сумма", num: true, render: (r) => nf(r.revenue) }]} /></div>
      <div className="card"><h2>Выручка по тарифам</h2><p className="muted">Нет данных: подписки пока назначаются вручную, платежей за тариф нет.</p></div>
      <p className="muted small">{m.note}</p>
    </>
  );
}

/* ---------- Токены ---------- */
interface Flow { period: Overview["tokens"]; all_time: { sold: number; spent: number; refunded: number; bonus: number; admin: number; balance_total: number }; welcome_bonus: string }
interface PkgRow { id: string; title: string; credits: number; bonus: number; price_stars: number; old_price_stars: number | null; price_rub: number | null; badge: string; is_active: number; sales: number }

export function TokensAdmin() {
  const { nav } = useApp();
  const { period } = usePeriod();
  const q = pq(period);
  const f = useLoad(() => api.admin.get<Flow>(`analytics/tokens?${q}`), [q]);
  const s = useLoad(() => api.admin.get<SeriesData>(`analytics/series?${q}`), [q]);
  const pk = useLoad(() => api.admin.get<PkgRow[]>("packages"), []);
  const st = useLoad(() => api.admin.get<{ welcome_bonus: string; max_variants: string }>("settings"), []);
  const [bonus, setBonus] = useState("0");
  const [maxV, setMaxV] = useState("4");
  useEffect(() => { if (st.data) { setBonus(st.data.welcome_bonus || "0"); setMaxV(st.data.max_variants || "4"); } }, [st.data]);
  async function saveSettings() {
    try { await api.admin.send("PUT", "settings", { welcome_bonus: bonus, max_variants: maxV }); showToast("Сохранено"); st.reload(); }
    catch (e) { showToast(errText(e, "Не удалось сохранить")); }
  }
  if (!f.data) return f.error ? <ErrorBox message={f.error} onRetry={f.reload} /> : <Loading />;
  const p = f.data.period, a = f.data.all_time;
  return (
    <>
      <div className="kpi-groups">
        <Kpi title="За период" big={nf(p.spent)} bigLabel="Потрачено токенов" orange rows={[["Продано", nf(p.sold)], ["Возвращено", nf(p.refunded)], ["Выдано бонусами", nf(p.bonus)]]} />
        <Kpi title="За всё время" big={nf(a.balance_total)} bigLabel="Остаток у пользователей" rows={[["Продано", nf(a.sold)], ["Потрачено", nf(a.spent)], ["Возвращено", nf(a.refunded)], ["Бонусов", nf(a.bonus)], ["Корректировок админа", nf(a.admin)]]} />
        <Kpi title="Общий оборот" big={nf(a.sold + a.bonus)} bigLabel="Токенов поступило (покупки + бонусы)" rows={[["Оборот списаний", nf(a.spent)]]} />
      </div>
      <div className="card"><h2>Движение токенов</h2>
        <div className="flow"><span>Покупка</span><Icon name="chevron" size={16} /><span>Баланс</span><Icon name="chevron" size={16} /><span>Генерация</span><Icon name="chevron" size={16} /><span>Списание</span><Icon name="chevron" size={16} /><span>Возврат при ошибке</span></div>
        <p className="muted small">Каждая операция записывается в журнал токенов; баланс пользователя всегда равен сумме его операций.</p></div>
      {s.data && <ChartCard title="Токены по дням"><LineChart days={s.data.days} series={[{ name: "Куплено", color: palette.orange, values: s.data.tokens_bought }, { name: "Потрачено", color: palette.black, values: s.data.tokens_spent }, { name: "Возвращено", color: palette.soft, values: s.data.tokens_refunded }]} /></ChartCard>}
      <div className="card">
        <div className="card-head"><h2>Пакеты токенов</h2><button className="btn orange sm" onClick={() => nav.go({ name: "admin", page: "package", id: "new" })}><Icon name="plus" size={16} /> Добавить пакет</button></div>
        <ul className="list">
          {(pk.data ?? []).map((x) => (
            <ListRow key={x.id} thumb={null} title={`${x.title} · ${nf(x.credits)}${x.bonus ? ` +${nf(x.bonus)}` : ""} токенов`} sub={`${x.price_stars} ⭐${x.old_price_stars ? ` (было ${x.old_price_stars})` : ""}${x.price_rub ? ` · ${x.price_rub} ₽` : ""} · продано: ${x.sales}${x.badge ? ` · «${x.badge}»` : ""}${x.is_active ? "" : " · скрыт"}`}
              onClick={() => nav.go({ name: "admin", page: "package", id: x.id })} />
          ))}
        </ul>
        {pk.data?.length === 0 && <p className="muted">Пакетов нет — добавьте первый.</p>}
      </div>
      <div className="card"><h2>Настройки токенов</h2>
        <Field label="Стартовый бонус при регистрации, токенов" hint="0 — бонус выключен"><TextInput value={bonus} onChange={(v) => setBonus(v.replace(/\D/g, ""))} /></Field>
        <Field label="Максимум вариантов за один запрос (1–8)"><TextInput value={maxV} onChange={(v) => setMaxV(v.replace(/\D/g, ""))} /></Field>
        <button className="btn orange sm" onClick={saveSettings}>Сохранить</button>
      </div>
    </>
  );
}

/* ---------- Подписки ---------- */
export function Subscriptions() {
  const { nav } = useApp();
  const { period } = usePeriod();
  const q = pq(period);
  const o = useLoad(() => api.admin.get<Overview>(`analytics/overview?${q}`), [q]);
  const pro = useLoad(() => api.admin.get<{ items: { tg_id: number; name: string; username: string | null; created_at: string; balance: number }[] }>("users?flt=pro&size=25"), []);
  if (!o.data) return <Loading />;
  const s = o.data.subscriptions;
  return (
    <>
      <div className="kpi-groups">
        <Kpi title="Пользователи" big={nf(s.free + s.pro)} bigLabel="Всего" rows={[["Бесплатные", nf(s.free)], ["PRO", nf(s.pro)]]} />
        <Kpi title="PRO за период" big={nf(s.granted)} bigLabel="Подключено" orange rows={[["Активные PRO сейчас", nf(s.pro)], ["Отменено", nf(s.cancelled)]]} />
        <Kpi title="Продления и выручка" big="Нет данных" rows={[["Продления", "Нет данных"], ["Истёкшие", "Нет данных"], ["Выручка от подписок", "Нет данных"]]} />
      </div>
      <div className="notice info"><p>Платной подписки пока нет: тариф PRO назначается администратором вручную (профиль пользователя → «Назначить PRO»). Продления, истечения и выручка по подпискам появятся, когда будет подключён биллинг.</p></div>
      <div className="card"><h2>Пользователи с PRO</h2>
        <DataTable rows={pro.data?.items ?? []} empty="Пользователей с PRO пока нет" onRow={(u) => nav.go({ name: "admin", page: "user", id: String(u.tg_id) })}
          cols={[{ key: "name", title: "Имя", render: (u) => <b>{u.name}</b> }, { key: "username", title: "Username", render: (u) => (u.username ? `@${u.username}` : "—") }, { key: "created_at", title: "Регистрация", render: (u) => fmtShort(u.created_at) }, { key: "balance", title: "Баланс", num: true, render: (u) => nf(u.balance) }]} /></div>
    </>
  );
}

/* ---------- Рефералы ---------- */
interface Refs { items: { tg_id: number; name: string; link: string; invited: number; active: number; paying: number; revenue: number; conversion: number | null }[]; totals: { invited: number; active: number; paying: number; revenue: number; conversion: number | null }; link_format: string }

export function Referrals() {
  const r = useLoad(() => api.admin.get<Refs>("referrals"), []);
  const { nav } = useApp();
  if (!r.data) return r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : <Loading />;
  const t = r.data.totals;
  return (
    <>
      <div className="toolbar"><span style={{ flex: 1 }} /><ExportButton kind="referrals" /></div>
      <div className="kpi-groups"><Kpi title="Реферальная система" big={nf(t.invited)} bigLabel="Привлечено пользователей" orange rows={[["Активных (30 дней)", nf(t.active)], ["Платящих", nf(t.paying)], ["Выручка", `${nf(t.revenue)} ⭐`], ["Конверсия в оплату", pct(t.conversion)]]} /></div>
      <div className="notice info"><p>Источник — «Реферальная ссылка». Формат ссылки: <code>{r.data.link_format}</code>. Пользователь копирует свою ссылку в профиле («Пригласить друзей»).</p></div>
      <DataTable rows={r.data.items} empty="Пока никто никого не пригласил" onRow={(x) => nav.go({ name: "admin", page: "user", id: String(x.tg_id) })} cols={[
        { key: "name", title: "Пригласивший", render: (x) => <b>{x.name}</b> },
        { key: "link", title: "Реферальная ссылка", wrap: true, render: (x) => <code>{x.link}</code> },
        { key: "invited", title: "Привлечено", num: true }, { key: "active", title: "Активных", num: true }, { key: "paying", title: "Платящих", num: true },
        { key: "revenue", title: "Выручка, ⭐", num: true, render: (x) => nf(x.revenue) }, { key: "conversion", title: "Конверсия", num: true, render: (x) => pct(x.conversion) },
      ]} />
    </>
  );
}

/* ---------- Маркетинг ---------- */
interface Mkt { items: { source_label: string; campaign: string | null; material: string | null; users: number; registered: number; generated: number; paying: number; revenue: number; conversion: number | null }[]; link_format: string; note: string }

export function Marketing() {
  const m = useLoad(() => api.admin.get<Mkt>("marketing"), []);
  const cfg = useLoad(() => api.admin.get<{ bot_username: string }>("config"), []);
  const [src, setSrc] = useState("tiktok");
  const [camp, setCamp] = useState("");
  const [mat, setMat] = useState("");
  if (!m.data) return m.error ? <ErrorBox message={m.error} onRetry={m.reload} /> : <Loading />;
  const clean = (v: string) => v.toLowerCase().replace(/[^a-z0-9-]/g, "");
  const param = ["src", clean(src), clean(camp), clean(mat)].filter((x, i) => i < 2 || x).join("_");
  const link = `https://t.me/${cfg.data?.bot_username || "<бот>"}?start=${param}`;
  return (
    <>
      <div className="card"><h2>Создать рекламную ссылку</h2>
        <Field label="Источник (латиницей)" hint="Например: tiktok, instagram, telegram, youtube, vk"><TextInput value={src} onChange={setSrc} /></Field>
        <Field label="Кампания"><TextInput value={camp} onChange={setCamp} placeholder="spring" /></Field>
        <Field label="Рекламный материал"><TextInput value={mat} onChange={setMat} placeholder="video1" /></Field>
        <div className="notice info"><code>{link}</code>
          <button className="btn orange sm" onClick={() => { navigator.clipboard?.writeText(link).then(() => showToast("Ссылка скопирована"), () => showToast(link)); }}><Icon name="copy" size={16} /> Копировать</button></div>
      </div>
      <p className="muted small">{m.data.note}</p>
      <DataTable rows={m.data.items} empty="Нет данных" cols={[
        { key: "source_label", title: "Источник", render: (x) => <b>{x.source_label}</b> }, { key: "campaign", title: "Кампания", render: (x) => x.campaign ?? "—" }, { key: "material", title: "Материал", render: (x) => x.material ?? "—" },
        { key: "users", title: "Пользователей", num: true }, { key: "registered", title: "Вошли", num: true }, { key: "generated", title: "Создали", num: true }, { key: "paying", title: "Платящих", num: true },
        { key: "revenue", title: "Выручка, ⭐", num: true, render: (x) => nf(x.revenue) }, { key: "conversion", title: "Конверсия", num: true, render: (x) => pct(x.conversion) },
      ]} />
    </>
  );
}


/** Транзакции: пополнения и операции с токенами в одном месте. */
export function Transactions() {
  const [tab, setTab] = useState<"payments" | "tokens" | "revenue">("payments");
  return (
    <>
      <div className="tabs-line">
        <button className={tab === "payments" ? "on" : ""} onClick={() => setTab("payments")}>Пополнения</button>
        <button className={tab === "tokens" ? "on" : ""} onClick={() => setTab("tokens")}>Токены</button>
        <button className={tab === "revenue" ? "on" : ""} onClick={() => setTab("revenue")}>Выручка</button>
      </div>
      {tab === "payments" && <Payments />}
      {tab === "tokens" && <TokensAdmin />}
      {tab === "revenue" && <Revenue />}
    </>
  );
}
