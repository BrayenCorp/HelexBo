import { useState } from "react";
import { api } from "../api";
import { showToast, useApp } from "../ctx";
import { fmtTime, nf } from "../format";
import { Icon } from "../icons";
import { Chips, ErrorBox, Loading, Modal, useDebounced, useLoad } from "../ui";
import { Field, SelectInput, TextInput, errText } from "./kit";
import { ActivityFeed, ExportButton, TYPE_LABEL } from "./parts";
import type { ActivityItem } from "./parts";
import { pq, usePeriod } from "./shell";
import { DataTable, Pager } from "./table";

/* ---------- Активность пользователей ---------- */
interface BotStats { start: number; start_users: number; miniapp: number; miniapp_users: number; commands: Record<string, number>; returned: number; churned: number; note: string }

export function Activity() {
  const { nav } = useApp();
  const { period } = usePeriod();
  const [kind, setKind] = useState("all");
  const feed = useLoad(() => api.admin.get<ActivityItem[]>(`activity?limit=100${kind !== "all" ? `&kinds=${kind}` : ""}`), [kind]);
  const bot = useLoad(() => api.admin.get<BotStats>(`analytics/bot?${pq(period)}`), [pq(period)]);
  const b = bot.data;
  return (
    <>
      {b && (
        <div className="kpi-groups">
          <div className="kpi-group"><h3>Telegram-бот за период</h3><div className="kpi-rows">
            <div className="kpi-row"><span className="muted">Запусков /start</span><b>{nf(b.start)}</b></div>
            <div className="kpi-row"><span className="muted">Уникальных пользователей</span><b>{nf(b.start_users)}</b></div>
            <div className="kpi-row"><span className="muted">Открытий Mini App</span><b>{nf(b.miniapp)}</b></div>
            <div className="kpi-row"><span className="muted">Открыло Mini App</span><b>{nf(b.miniapp_users)}</b></div>
          </div></div>
          <div className="kpi-group"><h3>Команды бота</h3><div className="kpi-rows">
            {(["create", "profile", "history", "settings"] as const).map((c) => <div key={c} className="kpi-row"><span className="muted">/{c}</span><b>{nf(b.commands[c] ?? 0)}</b></div>)}
          </div></div>
          <div className="kpi-group"><h3>Возвращаемость</h3><div className="kpi-rows">
            <div className="kpi-row"><span className="muted">Вернулось</span><b>{nf(b.returned)}</b></div>
            <div className="kpi-row"><span className="muted">Перестало пользоваться</span><b>{nf(b.churned)}</b></div>
          </div></div>
        </div>
      )}
      {b && <p className="muted small">{b.note}</p>}
      <Chips value={kind} onChange={setKind} options={[["all", "Все"], ...Object.entries(TYPE_LABEL).map(([k, v]): [string, string] => [k, v])]} />
      <div className="card">
        {feed.error && <ErrorBox message={feed.error} onRetry={feed.reload} />}
        {feed.loading && !feed.data ? <Loading /> : <ActivityFeed items={feed.data ?? []} onUser={(id) => nav.go({ name: "admin", page: "user", id: String(id) })} />}
      </div>
    </>
  );
}

/* ---------- Генерации ---------- */
interface GenRow { id: number; user_id: number; user: string; kind: string; prompt: string; category: string | null; template: string; style_label: string | null; provider: string; status: string; status_label: string; price_credits: number; provider_cost_usd: number; seconds: number | null; created_at: string; error: string | null; is_stub: number; used_free: number }
interface GenPage { items: GenRow[]; total: number }

export function Generations() {
  const { nav, me } = useApp();
  const [f, setF] = useState({ kind: "", status: "", provider: "", category: "", start: "", end: "", q: "" });
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<GenRow | null>(null);
  const q = useDebounced(f.q, 300);
  const cats = useLoad(() => (me.roles.includes("owner") ? api.admin.get<{ id: string; title: string }[]>("categories") : Promise.resolve([])), []);
  const prov = useLoad(() => api.admin.get<{ providers: { model: string }[] }>("models"), []);
  const path = `generations?kind=${f.kind}&status=${f.status}&provider=${f.provider}&category=${f.category}&start=${f.start}&end=${f.end}&q=${encodeURIComponent(q)}&page=${page}&size=25`;
  const res = useLoad(() => api.admin.get<GenPage>(path), [path]);
  const set = (k: keyof typeof f, v: string) => { setF({ ...f, [k]: v }); setPage(1); };
  const sel = (k: keyof typeof f, label: string, opts: [string, string][]) => (
    <span className="select"><select value={f[k]} onChange={(e) => set(k, e.target.value)} aria-label={label}><option value="">{label}</option>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></span>
  );
  return (
    <>
      <div className="toolbar">
        <label className="search"><Icon name="search" size={18} /><input placeholder="Поиск: ID, пользователь, запрос" value={f.q} onChange={(e) => set("q", e.target.value)} /></label>
        {sel("kind", "Все типы", [["photo", "Фото"], ["video", "Видео"]])}
        {sel("status", "Все статусы", [["done", "Успешные"], ["failed", "Ошибки"], ["processing", "В обработке"], ["created", "В очереди"]])}
        {prov.data && sel("provider", "Все провайдеры", prov.data.providers.map((p): [string, string] => [p.model, p.model]))}
        {(cats.data?.length ?? 0) > 0 && sel("category", "Все категории", cats.data!.map((c): [string, string] => [c.id, c.title]))}
        <input type="date" className="input" style={{ width: 150 }} value={f.start} onChange={(e) => set("start", e.target.value)} aria-label="С даты" />
        <input type="date" className="input" style={{ width: 150 }} value={f.end} onChange={(e) => set("end", e.target.value)} aria-label="По дату" />
        {me.roles.includes("owner") && <ExportButton kind="generations" />}
      </div>
      {res.error && <ErrorBox message={res.error} onRetry={res.reload} />}
      {res.loading && !res.data ? <Loading /> : (
        <>
          <DataTable rows={res.data?.items ?? []} onRow={setOpen} empty="Генераций не найдено" cols={[
            { key: "id", title: "ID" },
            { key: "user", title: "Пользователь", render: (g) => (me.roles.includes("owner") ? <button className="link" onClick={(e) => { e.stopPropagation(); nav.go({ name: "admin", page: "user", id: String(g.user_id) }); }}>{g.user}</button> : g.user) },
            { key: "kind", title: "Тип", render: (g) => (g.kind === "photo" ? "Фото" : "Видео") },
            { key: "prompt", title: "Запрос", wrap: true, render: (g) => g.prompt || "—" },
            { key: "category", title: "Категория", render: (g) => g.category ?? "—" },
            { key: "template", title: "Стиль / шаблон", render: (g) => g.template + (g.style_label ? ` · ${g.style_label}` : "") },
            { key: "provider", title: "Провайдер" },
            { key: "status", title: "Статус", render: (g) => <span className={`status ${g.status}`}>{g.status_label}</span> },
            { key: "price_credits", title: "Токены", num: true, render: (g) => (g.used_free ? "бесплатно" : nf(g.price_credits)) },
            { key: "provider_cost_usd", title: "Стоимость, $", num: true, render: (g) => g.provider_cost_usd.toFixed(4) },
            { key: "seconds", title: "Время, с", num: true, render: (g) => (g.seconds !== null ? g.seconds.toFixed(1) : "—") },
            { key: "created_at", title: "Дата", render: (g) => fmtTime(g.created_at) },
          ]} />
          <Pager page={page} size={25} total={res.data?.total ?? 0} onPage={setPage} />
        </>
      )}
      {open && (
        <Modal onClose={() => setOpen(null)}>
          <h2>Генерация №{open.id}</h2>
          <div style={{ textAlign: "left", width: "100%" }}>
            <p><b>Пользователь:</b> {open.user}</p><p><b>Запрос:</b> {open.prompt || "—"}</p><p><b>Провайдер:</b> {open.provider}{open.is_stub ? " (тестовая заглушка)" : ""}</p>
            <p><b>Статус:</b> {open.status_label}</p>{open.error && <p className="notice bad" style={{ marginTop: 8 }}>{open.error}</p>}
          </div>
          <button className="btn black block" onClick={() => setOpen(null)}>Закрыть</button>
        </Modal>
      )}
    </>
  );
}

/* ---------- Платежи и способы оплаты ---------- */
interface PayRow { id: number; user_id: number; user: string; product: string; amount: number; currency: string; credits: number; bonus: number; method: string; status: string; status_label: string; created_at: string; paid_at: string | null }
interface Method { code: string; title: string; description: string; status: "on" | "soon" | "off"; fee_percent: number | null; ready: boolean; payments: number; paid: number; errors: number; revenue: number; currency: string }

function Methods() {
  const q = useLoad(() => api.admin.get<Method[]>("payment-methods"), []);
  const [edit, setEdit] = useState<Record<string, { status?: string; fee?: string }>>({});
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  async function save(m: Method) {
    const e = edit[m.code];
    if (!e) return;
    try { await api.admin.send("PUT", `payment-methods/${m.code}`, { ...(e.status ? { status: e.status } : {}), ...(e.fee !== undefined ? { fee_percent: e.fee } : {}) }); showToast("Сохранено"); setEdit({ ...edit, [m.code]: {} }); q.reload(); }
    catch (er) { showToast(errText(er, "Не удалось сохранить")); }
  }
  return (
    <div className="sys-grid">
      {q.data.map((m) => {
        const e = edit[m.code] ?? {};
        return (
          <div key={m.code} className={`sys-card ${m.ready ? "" : "warn"}`}>
            <div className="card-head"><b style={{ fontSize: 17 }}>{m.title}</b><span className={`state ${m.ready ? "" : "warn"}`}>{m.ready ? "Подключён" : "Не подключён"}</span></div>
            <span className="muted small">{m.description}</span>
            {!m.ready && <p className="small">Технически не подключён: пользователю он не показывается как рабочий. Для СБП и карт нужен платёжный провайдер и ключи.</p>}
            <Field label="Показ пользователям">
              <SelectInput value={e.status ?? m.status} onChange={(v) => setEdit({ ...edit, [m.code]: { ...e, status: v } })} options={[["on", "Включён"], ["soon", "Показывать «Скоро»"], ["off", "Выключен"]]} />
            </Field>
            <Field label="Комиссия, %"><TextInput value={e.fee ?? (m.fee_percent ?? "")} onChange={(v) => setEdit({ ...edit, [m.code]: { ...e, fee: v } })} placeholder="Не указана" /></Field>
            <div className="kpi-rows"><div className="kpi-row"><span className="muted">Платежей</span><b>{nf(m.payments)}</b></div><div className="kpi-row"><span className="muted">Оплачено</span><b>{nf(m.paid)}</b></div>
              <div className="kpi-row"><span className="muted">Ошибок</span><b>{nf(m.errors)}</b></div><div className="kpi-row"><span className="muted">Выручка</span><b>{m.code === "test" ? "тестовая" : `${nf(m.revenue)} ${m.currency === "XTR" ? "⭐" : m.currency}`}</b></div></div>
            <button className="btn orange sm" disabled={!e.status && e.fee === undefined} onClick={() => save(m)}>Сохранить</button>
          </div>
        );
      })}
    </div>
  );
}

export function Payments() {
  const { nav } = useApp();
  const [tab, setTab] = useState<"list" | "methods">("list");
  const [f, setF] = useState({ status: "", method: "", q: "" });
  const [page, setPage] = useState(1);
  const q = useDebounced(f.q, 300);
  const path = `payments?status=${f.status}&method=${f.method}&q=${encodeURIComponent(q)}&page=${page}&size=25`;
  const res = useLoad(() => api.admin.get<{ items: PayRow[]; total: number }>(path), [path]);
  return (
    <>
      <div className="tabs-line"><button className={tab === "list" ? "on" : ""} onClick={() => setTab("list")}>Платежи</button><button className={tab === "methods" ? "on" : ""} onClick={() => setTab("methods")}>Способы оплаты</button></div>
      {tab === "methods" ? <Methods /> : (
        <>
          <div className="toolbar">
            <label className="search"><Icon name="search" size={18} /><input placeholder="Поиск: ID платежа или пользователь" value={f.q} onChange={(e) => { setF({ ...f, q: e.target.value }); setPage(1); }} /></label>
            <span className="select"><select value={f.status} onChange={(e) => { setF({ ...f, status: e.target.value }); setPage(1); }} aria-label="Статус"><option value="">Все статусы</option><option value="pending">Ожидает</option><option value="paid">Оплачен</option><option value="failed">Ошибка</option><option value="refunded">Возврат</option><option value="cancelled">Отменён</option></select></span>
            <ExportButton kind="payments" />
          </div>
          {res.error && <ErrorBox message={res.error} onRetry={res.reload} />}
          {res.loading && !res.data ? <Loading /> : (
            <>
              <DataTable rows={res.data?.items ?? []} empty="Платежей пока нет" onRow={(p) => nav.go({ name: "admin", page: "user", id: String(p.user_id) })} cols={[
                { key: "id", title: "ID" }, { key: "user", title: "Пользователь" }, { key: "product", title: "Продукт" },
                { key: "amount", title: "Сумма", num: true, render: (p) => `${nf(p.amount)} ${p.currency === "XTR" ? "⭐" : p.currency === "TEST" ? "(тест)" : p.currency}` },
                { key: "credits", title: "Токены", num: true, render: (p) => nf(p.credits + p.bonus) }, { key: "method", title: "Платёжная система" },
                { key: "status", title: "Статус", render: (p) => <span className={`status ${p.status}`}>{p.status_label}</span> }, { key: "created_at", title: "Дата", render: (p) => fmtTime(p.paid_at ?? p.created_at) },
              ]} />
              <Pager page={page} size={25} total={res.data?.total ?? 0} onPage={setPage} />
            </>
          )}
        </>
      )}
    </>
  );
}

