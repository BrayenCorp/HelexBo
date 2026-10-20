import { useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "../api";
import { showToast, useApp } from "../ctx";
import { fmtDate, fmtShort, fmtTime, nf, tokensText, usd } from "../format";
import { Icon } from "../icons";
import { Dropdown } from "../pf";
import { ErrorBox, Loading, Modal, PageHeader, Section, useDebounced, useLoad } from "../ui";
import { ExportButton } from "./parts";
import { DataTable, Pager } from "./table";
import type { Col } from "./table";

interface UserRow { tg_id: number; name: string; username: string | null; created_at: string; last_seen_at: string | null; tariff: string; balance: number; spent_stars: number; spent_credits: number; generations: number; photos: number; videos: number; audios: number; via_bot: number; signup_from: string; source_label: string; status: string }
interface UserPage { items: UserRow[]; total: number; page: number; size: number }

const FILTERS: [string, string][] = [["all", "Все"], ["new", "Новые"], ["active", "Активные"], ["inactive", "Неактивные"], ["pro", "PRO"], ["free", "Бесплатные"], ["paying", "Платящие"], ["nonpaying", "Неплатящие"], ["top_active", "Самые активные"], ["top_spenders", "Самые дорогие"], ["blocked", "Заблокированные"]];

export function UsersList() {
  const { nav } = useApp();
  const [text, setText] = useState("");
  const [flt, setFlt] = useState("all");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<{ key: string; desc: boolean }>({ key: "created_at", desc: true });
  const qs = useDebounced(text.trim(), 300);
  const path = `users?q=${encodeURIComponent(qs)}&flt=${flt}&page=${page}&size=25&sort=${sort.key}&desc=${sort.desc}`;
  const q = useLoad(() => api.admin.get<UserPage>(path), [path]);
  const cols: Col<UserRow>[] = [
    { key: "tg_id", title: "ID" },
    { key: "name", title: "Имя", render: (u) => <b>{u.name}</b> },
    { key: "username", title: "Username", render: (u) => (u.username ? `@${u.username}` : "—") },
    { key: "created_at", title: "Регистрация", sortable: true, render: (u) => fmtShort(u.created_at) },
    { key: "last_seen_at", title: "Последняя активность", sortable: true, render: (u) => fmtTime(u.last_seen_at) },
    { key: "tariff", title: "Тариф", render: (u) => <span className={`tag ${u.tariff === "PRO" ? "dark" : ""}`}>{u.tariff}</span> },
    { key: "balance", title: "Баланс", num: true, sortable: true, render: (u) => nf(u.balance) },
    { key: "spent_stars", title: "Потрачено, ⭐", num: true, render: (u) => nf(u.spent_stars) },
    { key: "spent_credits", title: "Потрачено токенов", num: true, sortable: true, render: (u) => nf(u.spent_credits) },
    { key: "generations", title: "Генераций", num: true, sortable: true, render: (u) => nf(u.generations) },
    { key: "photos", title: "Фото", num: true, render: (u) => nf(u.photos) },
    { key: "videos", title: "Видео", num: true, render: (u) => nf(u.videos) },
    { key: "audios", title: "Аудио", num: true, render: (u) => nf(u.audios) },
    { key: "signup_from", title: "Откуда пришёл" },
    { key: "source_label", title: "Источник перехода" },
    { key: "status", title: "Статус", render: (u) => <span className={`status ${u.status === "blocked" ? "failed" : ""}`}>{u.status === "blocked" ? "Заблокирован" : "Активен"}</span> },
  ];
  return (
    <>
      <div className="toolbar">
        <label className="search"><Icon name="search" size={18} /><input placeholder="Поиск: Telegram ID, username или имя" value={text} onChange={(e) => { setText(e.target.value); setPage(1); }} /></label>
        <span className="select-wrap"><Dropdown value={flt} onChange={(v) => { setFlt(v); setPage(1); }} options={FILTERS.map(([id, label]) => ({ id, label }))} /></span>
        <ExportButton kind="users" />
      </div>
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.loading && !q.data ? <Loading /> : (
        <>
          <DataTable cols={cols} rows={q.data?.items ?? []} onRow={(u) => nav.go({ name: "admin", page: "user", id: String(u.tg_id) })}
            empty={qs || flt !== "all" ? "Никого не нашли — измените запрос или фильтр" : "Пользователей пока нет"}
            sort={sort} onSort={(key) => { setSort((s) => ({ key, desc: s.key === key ? !s.desc : true })); setPage(1); }} />
          <Pager page={page} size={25} total={q.data?.total ?? 0} onPage={setPage} />
        </>
      )}
    </>
  );
}

/* ---------- Профиль пользователя ---------- */
interface Profile {
  info: { tg_id: number; username: string | null; name: string; created_at: string; registered_at: string | null; last_seen_at: string | null; tariff: string; is_pro: boolean; status: string; source: string; campaign: string | null; material: string | null; language: string | null; invited: number; referrer: { tg_id: number; name: string } | null };
  money: { spent_stars: number; spent_usd_estimate: number; purchases: number; avg_check: number; first: string | null; last: string | null; ltv_stars: number; ltv_usd_estimate: number };
  tokens: { balance: number; bought: number; spent: number; refunded: number; bonus: number };
  generations: { total: number; photo: number; video: number; success: number; errors: number };
  timeline: { ts: string; text: string }[];
  orders: { id: number; created_at: string; kind: string; status: string; prompt: string; style: string | null; price_credits: number; model: string; template: string; is_system: number; seconds: number | null; error: string | null }[];
  payments: { id: number; amount: number; currency: string; credits: number; bonus: number; provider: string; status: string; created_at: string; paid_at: string | null; product: string }[];
}

const ACTIONS: { key: string; label: string; needAmount?: boolean; danger?: boolean; icon: "plus" | "crown" | "shield" | "refresh" | "trash" }[] = [
  { key: "credits_add", label: "Добавить токены", needAmount: true, icon: "plus" },
  { key: "credits_sub", label: "Убрать токены", needAmount: true, icon: "trash", danger: true },
  { key: "pro_on", label: "Назначить PRO", icon: "crown" },
  { key: "pro_off", label: "Снять PRO", icon: "crown" },
  { key: "block", label: "Заблокировать", icon: "shield", danger: true },
  { key: "unblock", label: "Разблокировать", icon: "shield" },
  { key: "reset_free", label: "Сбросить бесплатные попытки", icon: "refresh" },
];
const PAY_STATUS: Record<string, string> = { pending: "Ожидает", paid: "Оплачен", failed: "Ошибка", refunded: "Возврат", cancelled: "Отменён" };
const GEN_STATUS: Record<string, string> = { created: "В очереди", processing: "В обработке", done: "Успешно", failed: "Ошибка" };

export function UserProfile({ id }: { id: string }) {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<Profile>(`users/${id}`), [id]);
  const [action, setAction] = useState<(typeof ACTIONS)[number] | null>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const p = q.data;
  const i = p.info;

  async function run() {
    if (!action) return;
    setBusy(true); setError(null);
    try {
      await api.admin.send("POST", `users/${id}/action`, { action: action.key, amount: action.needAmount ? Number(amount) : undefined, note, confirm: true });
      showToast("Готово: действие выполнено и записано в журнал");
      setAction(null); setAmount(""); setNote(""); q.reload();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Не удалось выполнить"); }
    finally { setBusy(false); }
  }
  const row = (k: string, v: ReactNode) => <div className="kpi-row"><span className="muted">{k}</span><b>{v}</b></div>;

  return (
    <>
      <PageHeader title={i.name} onBack={nav.back} right={<span className={`tag ${i.is_pro ? "dark" : ""}`}>{i.tariff}</span>} />
      <div className="kpi-groups">
        <div className="kpi-group"><h3>Основная информация</h3><div className="kpi-rows">
          {row("Telegram ID", i.tg_id)}{row("Username", i.username ? `@${i.username}` : "—")}{row("Регистрация", fmtDate(i.registered_at ?? i.created_at))}
          {row("Последняя активность", fmtTime(i.last_seen_at))}{row("Тариф", i.tariff)}{row("Статус", i.status === "blocked" ? "Заблокирован" : "Активен")}
          {row("Источник", i.source + (i.campaign ? ` · ${i.campaign}` : ""))}{row("Пригласил", i.referrer ? i.referrer.name : "—")}{row("Привёл пользователей", i.invited)}
        </div></div>
        <div className="kpi-group"><h3>Деньги</h3><div className="kpi-rows">
          {row("Всего потрачено", `${nf(p.money.spent_stars)} ⭐ (≈ ${usd(p.money.spent_usd_estimate)})`)}{row("Покупок", p.money.purchases)}{row("Средний чек", `${nf(p.money.avg_check)} ⭐`)}
          {row("Первая покупка", fmtDate(p.money.first))}{row("Последняя покупка", fmtDate(p.money.last))}{row("LTV", `${nf(p.money.ltv_stars)} ⭐`)}
        </div></div>
        <div className="kpi-group"><h3>Токены</h3><div className="kpi-rows">
          {row("Текущий баланс", tokensText(p.tokens.balance))}{row("Куплено", nf(p.tokens.bought))}{row("Потрачено", nf(p.tokens.spent))}{row("Возвращено", nf(p.tokens.refunded))}{row("Бонусных", nf(p.tokens.bonus))}
        </div></div>
        <div className="kpi-group"><h3>Генерации</h3><div className="kpi-rows">
          {row("Всего", p.generations.total)}{row("Фото", p.generations.photo)}{row("Видео", p.generations.video)}{row("Успешных", p.generations.success)}{row("Ошибок", p.generations.errors)}
        </div></div>
      </div>

      <div className="card"><h2>Действия</h2>
        <div className="action-grid">
          {ACTIONS.filter((a) => !(a.key === "pro_on" && i.is_pro) && !(a.key === "pro_off" && !i.is_pro) && !(a.key === "block" && i.status === "blocked") && !(a.key === "unblock" && i.status !== "blocked")).map((a) => (
            <button key={a.key} className={`btn ${a.danger ? "ghost danger-text" : "outline"} sm`} onClick={() => { setAction(a); setError(null); }}><Icon name={a.icon} size={16} />{a.label}</button>
          ))}
        </div>
        <p className="muted small">Каждое действие требует подтверждения и записывается в журнал действий администраторов.</p>
      </div>

      <Section title="История действий пользователя">
        <div className="card"><div className="timeline">
          {[...p.timeline].reverse().map((t, k) => <div key={k} className="tl-item"><span className="tl-dot" /><span><b>{t.text}</b><div className="muted">{fmtTime(t.ts)}</div></span></div>)}
          {p.timeline.length === 0 && <p className="muted">Действий пока нет.</p>}
        </div></div>
      </Section>

      <Section title="История генераций">
        <DataTable rows={p.orders} empty="Генераций нет" cols={[
          { key: "id", title: "ID" }, { key: "created_at", title: "Дата", render: (o) => fmtTime(o.created_at) },
          { key: "kind", title: "Тип", render: (o) => (o.kind === "photo" ? "Фото" : "Видео") },
          { key: "prompt", title: "Запрос", wrap: true, render: (o) => o.prompt || (o.is_system ? "—" : o.template) },
          { key: "style", title: "Стиль / шаблон", render: (o) => (o.is_system ? "Свободная" : o.template) },
          { key: "model", title: "AI-провайдер" }, { key: "price_credits", title: "Токены", num: true },
          { key: "seconds", title: "Время, с", num: true, render: (o) => (o.seconds !== null ? o.seconds.toFixed(1) : "—") },
          { key: "status", title: "Статус", render: (o) => <span className={`status ${o.status}`}>{GEN_STATUS[o.status]}</span> },
        ]} />
      </Section>
      <Section title="История платежей">
        <DataTable rows={p.payments} empty="Платежей нет" cols={[
          { key: "id", title: "ID операции" }, { key: "product", title: "Продукт" },
          { key: "amount", title: "Сумма", num: true, render: (x) => `${nf(x.amount)} ${x.currency === "XTR" ? "⭐" : x.currency}` },
          { key: "credits", title: "Токены", num: true, render: (x) => nf(x.credits + x.bonus) }, { key: "provider", title: "Способ" },
          { key: "created_at", title: "Дата", render: (x) => fmtTime(x.paid_at ?? x.created_at) },
          { key: "status", title: "Статус", render: (x) => <span className={`status ${x.status}`}>{PAY_STATUS[x.status]}</span> },
        ]} />
      </Section>

      {action && (
        <Modal onClose={() => setAction(null)}>
          <span className={`modal-icon ${action.danger ? "danger" : ""}`}><Icon name={action.icon} size={26} /></span>
          <h2>{action.label}?</h2>
          <p className="muted">Пользователь: {i.name}. Действие будет записано в журнал.</p>
          {action.needAmount && <input className="input" inputMode="numeric" placeholder="Сколько токенов" value={amount} onChange={(e) => setAmount(e.target.value.replace(/\D/g, ""))} />}
          <input className="input" placeholder="Комментарий (необязательно)" value={note} onChange={(e) => setNote(e.target.value)} />
          {error && <ErrorBox message={error} />}
          <button className={`btn ${action.danger ? "danger" : "orange"} block`} disabled={busy || (action.needAmount && !amount)} onClick={run}>{busy ? "Выполняем…" : "Подтвердить"}</button>
          <button className="btn ghost block" onClick={() => setAction(null)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
