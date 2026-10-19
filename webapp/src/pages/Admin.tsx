import { useState } from "react";
import { api, ApiError } from "../api";
import type { Me } from "../types";
import { Cover, ErrorBox, Loading, Section, useLoad } from "../ui";

type Tab = "overview" | "users" | "templates" | "categories" | "showcase" | "banner" | "errors" | "orders" | "diag";
const OWNER_TABS: [Tab, string][] = [
  ["overview", "Обзор"], ["templates", "Шаблоны"], ["categories", "Категории"],
  ["showcase", "Витрина"], ["banner", "Баннер"], ["users", "Пользователи"],
];
const DEV_TABS: [Tab, string][] = [["errors", "Ошибки"], ["orders", "Задачи"], ["diag", "Диагностика"]];

const errText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

export function Admin({ me }: { me: Me }) {
  const tabs = [...(me.roles.includes("owner") ? OWNER_TABS : []), ...(me.roles.includes("developer") ? DEV_TABS : [])];
  const [tab, setTab] = useState<Tab>(tabs[0]?.[0] ?? "overview");
  if (!tabs.length) return <ErrorBox message="Нет доступа" />;
  return (
    <>
      <h1 className="h1">Админ-панель</h1>
      <div className="chips scroll">
        {tabs.map(([id, title]) => (
          <button key={id} className={`chip ${tab === id ? "on" : ""}`} onClick={() => setTab(id)}>{title}</button>
        ))}
      </div>
      {tab === "overview" && <Overview />}
      {tab === "users" && <Users />}
      {tab === "templates" && <TemplatesAdmin />}
      {tab === "categories" && <CategoriesAdmin />}
      {tab === "showcase" && <ShowcaseAdmin />}
      {tab === "banner" && <BannerAdmin />}
      {tab === "errors" && <Errors />}
      {tab === "orders" && <DevOrders />}
      {tab === "diag" && <Diagnostics />}
    </>
  );
}

/** Загрузка своего фото или видео: файл уходит на сервер, поле получает готовый адрес. */
function MediaField({ label, value, onChange }: { label: string; value: string; onChange: (url: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function pick(f: File | undefined) {
    if (!f) return;
    setBusy(true); setErr(null);
    try { onChange((await api.admin.upload(f)).url); }
    catch (e) { setErr(errText(e, "Не удалось загрузить файл")); }
    finally { setBusy(false); }
  }
  return (
    <div className="media-field">
      <span className="label">{label}</span>
      <div className="media-preview"><Cover url={value} /></div>
      <div className="row">
        <label className="btn ghost filebtn">
          {busy ? "Загружаем…" : value ? "Заменить фото или видео" : "Загрузить фото или видео"}
          <input type="file" accept="image/*,video/mp4,video/webm" hidden onChange={(e) => pick(e.target.files?.[0])} />
        </label>
        {value && <button className="btn ghost" onClick={() => onChange("")}>Убрать</button>}
      </div>
      {err && <ErrorBox message={err} />}
    </div>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return <label className="check"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {label}</label>;
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return <div className="stat"><span className="muted small">{label}</span><b>{value}</b></div>;
}

function Row({ thumb, title, sub, badge, onClick }: { thumb?: string; title: string; sub: string; badge?: string; onClick: () => void }) {
  return (
    <li>
      <button className="row-item" onClick={onClick}>
        <span className="row-thumb"><Cover url={thumb} /></span>
        <span className="row-main"><b>{title}</b><span className="muted small">{sub}</span></span>
        {badge && <span className="status">{badge}</span>}
      </button>
    </li>
  );
}

/* ---------- Владелец ---------- */

interface OverviewData {
  users: number;
  generations: Record<string, Record<string, number>>;
  free_generations_done: number;
  purchases: number;
  stars_received: number;
  test_purchases: number;
  ai_cost_usd: number;
  revenue_usd_estimate: number;
  profit_usd_estimate: number;
  credits_in_circulation: number;
  note: string;
}

function Overview() {
  const q = useLoad(() => api.admin.get<OverviewData>("overview"), []);
  if (q.loading) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const d = q.data;
  return (
    <>
      <div className="stats">
        <Stat label="Пользователи" value={d.users} />
        <Stat label="Фото готово" value={d.generations.photo.done} />
        <Stat label="Видео готово" value={d.generations.video.done} />
        <Stat label="Ошибок генерации" value={d.generations.photo.failed + d.generations.video.failed} />
        <Stat label="Покупок (Stars)" value={d.purchases} />
        <Stat label="Получено Stars" value={`${d.stars_received} ⭐`} />
        <Stat label="Тестовых покупок" value={d.test_purchases} />
        <Stat label="Расходы на AI" value={`$${d.ai_cost_usd}`} />
        <Stat label="Выручка (оценка)" value={`$${d.revenue_usd_estimate}`} />
        <Stat label="Прибыль (оценка)" value={`$${d.profit_usd_estimate}`} />
        <Stat label="Кредитов у людей" value={d.credits_in_circulation} />
        <Stat label="Бесплатных выдано" value={d.free_generations_done} />
      </div>
      <p className="muted small">{d.note}</p>
    </>
  );
}

interface UserRow { tg_id: number; username: string | null; first_name: string | null; balance: number; photos: number; videos: number; stars_spent: number }

function Users() {
  const [search, setSearch] = useState("");
  const q = useLoad(() => api.admin.get<UserRow[]>(`users?search=${encodeURIComponent(search)}`), [search]);
  return (
    <>
      <input className="input" placeholder="Поиск: ID, имя или @username" value={search} onChange={(e) => setSearch(e.target.value)} />
      {q.loading && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      <ul className="list">
        {(q.data ?? []).map((u) => (
          <li key={u.tg_id} className="ledger">
            <span><b>{u.first_name ?? "—"}</b> {u.username ? `@${u.username}` : ""}<br />
              <span className="muted small">ID {u.tg_id} · фото {u.photos} · видео {u.videos} · {u.stars_spent} ⭐</span></span>
            <b>{u.balance} кр.</b>
          </li>
        ))}
      </ul>
    </>
  );
}

/* --- шаблоны --- */
interface TplRow {
  id: number; title: string; description: string; category: string; kind: string; model: string; prompt: string;
  preview_url: string; price_credits: number; is_published: number; is_popular: number; is_trend: number; sort_order: number;
}
interface TplList { items: TplRow[]; categories: { id: string; title: string }[]; models: string[] }
type TplDraft = Partial<TplRow>;

const EMPTY_TPL: TplDraft = { title: "", description: "", kind: "photo", model: "image-default", prompt: "", preview_url: "", price_credits: 2, is_published: 0, is_popular: 0, is_trend: 0, sort_order: 100 };

function TemplatesAdmin() {
  const q = useLoad(() => api.admin.get<TplList>("templates"), []);
  const [draft, setDraft] = useState<TplDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const data = q.data;
  const catTitle = (id: string) => data.categories.find((c) => c.id === id)?.title ?? id;
  const set = (k: keyof TplRow, v: string | number | boolean) => setDraft({ ...draft, [k]: v });
  const close = () => { setDraft(null); setError(null); setConfirmDel(false); };

  async function save() {
    if (!draft) return;
    setError(null);
    try {
      if (draft.id) await api.admin.send("PUT", `templates/${draft.id}`, draft);
      else await api.admin.send("POST", "templates", { ...draft, category: draft.category ?? data.categories[0]?.id });
      close(); setNote("Сохранено"); q.reload();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!draft?.id) return;
    try {
      const r = await api.admin.del<{ deleted: boolean; hidden: boolean; orders: number }>(`templates/${draft.id}`);
      close(); q.reload();
      setNote(r.deleted ? "Шаблон удалён" : `По шаблону уже были заказы (${r.orders}), поэтому он скрыт с публикации, а история сохранена.`);
    } catch (e) { setError(errText(e, "Не удалось удалить")); }
  }

  if (draft) {
    const d = draft;
    return (
      <div className="form">
        <h2>{d.id ? "Редактирование образа" : "Новый образ"}</h2>
        <MediaField label="Превью (фото или видео — пример результата)" value={d.preview_url ?? ""} onChange={(u) => set("preview_url", u)} />
        <label>Название<input className="input" value={d.title ?? ""} onChange={(e) => set("title", e.target.value)} /></label>
        <label>Описание<textarea className="input" rows={2} value={d.description ?? ""} onChange={(e) => set("description", e.target.value)} /></label>
        <label>Категория
          <select className="input" value={d.category ?? data.categories[0]?.id} onChange={(e) => set("category", e.target.value)}>
            {data.categories.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select></label>
        <label>Тип результата
          <select className="input" value={d.kind} onChange={(e) => set("kind", e.target.value)}>
            <option value="photo">Фото</option><option value="video">Видео</option>
          </select></label>
        <label>Модель генерации
          <select className="input" value={d.model} onChange={(e) => set("model", e.target.value)}>
            {data.models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select></label>
        <label>Промпт (виден только вам)<textarea className="input" rows={4} value={d.prompt ?? ""} onChange={(e) => set("prompt", e.target.value)} /></label>
        <label>Цена в кредитах<input className="input" type="number" min={0} value={d.price_credits ?? 0} onChange={(e) => set("price_credits", Number(e.target.value))} /></label>
        <label>Порядок (меньше — выше)<input className="input" type="number" value={d.sort_order ?? 100} onChange={(e) => set("sort_order", Number(e.target.value))} /></label>
        <Check label="Опубликован" checked={!!d.is_published} onChange={(v) => set("is_published", v)} />
        <Check label="Показывать в «Популярных генерациях»" checked={!!d.is_popular} onChange={(v) => set("is_popular", v)} />
        <Check label="Показывать в «Новых трендах»" checked={!!d.is_trend} onChange={(v) => set("is_trend", v)} />
        {error && <ErrorBox message={error} />}
        <div className="row">
          <button className="btn" onClick={save}>Сохранить</button>
          <button className="btn ghost" onClick={close}>Отмена</button>
        </div>
        {d.id && (confirmDel
          ? <button className="btn danger" onClick={remove}>Точно удалить?</button>
          : <button className="btn ghost danger-text" onClick={() => setConfirmDel(true)}>Удалить образ</button>)}
      </div>
    );
  }
  return (
    <>
      {note && <div className="notice good"><p>{note}</p></div>}
      <button className="btn" onClick={() => { setDraft({ ...EMPTY_TPL, category: data.categories[0]?.id }); setNote(null); }}>Добавить образ</button>
      <ul className="list">
        {data.items.map((t) => (
          <Row key={t.id} thumb={t.preview_url} title={t.title}
            sub={`${catTitle(t.category)} · ${t.kind === "photo" ? "фото" : "видео"} · ${t.price_credits} кр.${t.is_trend ? " · тренд" : ""}${t.is_popular ? " · популярное" : ""}`}
            badge={t.is_published ? undefined : "Скрыт"} onClick={() => { setDraft({ ...t }); setNote(null); }} />
        ))}
      </ul>
    </>
  );
}

/* --- категории --- */
interface CatRow { id: string; title: string; cover_url: string; sort_order: number; is_published: number; templates_count: number }
const EMPTY_CAT: Partial<CatRow> = { title: "", cover_url: "", sort_order: 100, is_published: 1 };

function CategoriesAdmin() {
  const q = useLoad(() => api.admin.get<CatRow[]>("categories"), []);
  const [draft, setDraft] = useState<Partial<CatRow> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const set = (k: keyof CatRow, v: string | number | boolean) => setDraft({ ...draft, [k]: v });
  const close = () => { setDraft(null); setError(null); setConfirmDel(false); };

  async function save() {
    if (!draft) return;
    try {
      if (draft.id) await api.admin.send("PUT", `categories/${draft.id}`, draft);
      else await api.admin.send("POST", "categories", draft);
      close(); setNote("Сохранено"); q.reload();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!draft?.id) return;
    try { await api.admin.del(`categories/${draft.id}`); close(); setNote("Категория удалена"); q.reload(); }
    catch (e) { setError(errText(e, "Не удалось удалить")); setConfirmDel(false); }
  }

  if (draft) {
    return (
      <div className="form">
        <h2>{draft.id ? "Редактирование категории" : "Новая категория"}</h2>
        <MediaField label="Обложка — пример генерации (фото или видео)" value={draft.cover_url ?? ""} onChange={(u) => set("cover_url", u)} />
        <label>Название<input className="input" value={draft.title ?? ""} onChange={(e) => set("title", e.target.value)} /></label>
        <label>Порядок (меньше — выше)<input className="input" type="number" value={draft.sort_order ?? 100} onChange={(e) => set("sort_order", Number(e.target.value))} /></label>
        <Check label="Показывать в каталоге" checked={!!draft.is_published} onChange={(v) => set("is_published", v)} />
        {error && <ErrorBox message={error} />}
        <div className="row">
          <button className="btn" onClick={save}>Сохранить</button>
          <button className="btn ghost" onClick={close}>Отмена</button>
        </div>
        {draft.id && (confirmDel
          ? <button className="btn danger" onClick={remove}>Точно удалить?</button>
          : <button className="btn ghost danger-text" onClick={() => setConfirmDel(true)}>Удалить категорию</button>)}
      </div>
    );
  }
  return (
    <>
      {note && <div className="notice good"><p>{note}</p></div>}
      <button className="btn" onClick={() => { setDraft({ ...EMPTY_CAT }); setNote(null); }}>Добавить категорию</button>
      <ul className="list">
        {q.data.map((c) => (
          <Row key={c.id} thumb={c.cover_url} title={c.title} sub={`образов: ${c.templates_count}`}
            badge={c.is_published ? undefined : "Скрыта"} onClick={() => { setDraft({ ...c }); setNote(null); }} />
        ))}
      </ul>
    </>
  );
}

/* --- витрина --- */
interface ShowRow { id: number; title: string; media_url: string; media_kind: string; template_id: number | null; sort_order: number; is_published: number }
const EMPTY_SHOW: Partial<ShowRow> = { title: "", media_url: "", template_id: null, sort_order: 100, is_published: 1 };

function ShowcaseAdmin() {
  const q = useLoad(() => api.admin.get<ShowRow[]>("showcase"), []);
  const tpls = useLoad(() => api.admin.get<TplList>("templates"), []);
  const [draft, setDraft] = useState<Partial<ShowRow> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const set = (k: keyof ShowRow, v: string | number | boolean | null) => setDraft({ ...draft, [k]: v });
  const close = () => { setDraft(null); setError(null); };

  async function save() {
    if (!draft) return;
    try {
      if (draft.id) await api.admin.send("PUT", `showcase/${draft.id}`, draft);
      else await api.admin.send("POST", "showcase", draft);
      close(); setNote("Сохранено"); q.reload();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!draft?.id) return;
    await api.admin.del(`showcase/${draft.id}`);
    close(); setNote("Удалено с витрины"); q.reload();
  }

  if (draft) {
    return (
      <div className="form">
        <h2>{draft.id ? "Работа на витрине" : "Новая работа на витрину"}</h2>
        <MediaField label="Ваше фото или видео" value={draft.media_url ?? ""} onChange={(u) => set("media_url", u)} />
        <label>Подпись (необязательно)<input className="input" value={draft.title ?? ""} onChange={(e) => set("title", e.target.value)} /></label>
        <label>По нажатию открывать образ
          <select className="input" value={draft.template_id ?? ""} onChange={(e) => set("template_id", e.target.value ? Number(e.target.value) : null)}>
            <option value="">— ничего не открывать —</option>
            {(tpls.data?.items ?? []).map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select></label>
        <label>Порядок (меньше — выше)<input className="input" type="number" value={draft.sort_order ?? 100} onChange={(e) => set("sort_order", Number(e.target.value))} /></label>
        <Check label="Показывать на главной" checked={!!draft.is_published} onChange={(v) => set("is_published", v)} />
        {error && <ErrorBox message={error} />}
        <div className="row">
          <button className="btn" onClick={save}>Сохранить</button>
          <button className="btn ghost" onClick={close}>Отмена</button>
        </div>
        {draft.id && <button className="btn ghost danger-text" onClick={remove}>Убрать с витрины</button>}
      </div>
    );
  }
  return (
    <>
      <p className="muted small">Витрина — блок «Работы студии» на главной: ваши лучшие примеры, фото и короткие видео.</p>
      {note && <div className="notice good"><p>{note}</p></div>}
      <button className="btn" onClick={() => { setDraft({ ...EMPTY_SHOW }); setNote(null); }}>Добавить фото или видео</button>
      {q.data.length === 0 && <p className="muted center pad">Витрина пуста.</p>}
      <ul className="list">
        {q.data.map((s) => (
          <Row key={s.id} thumb={s.media_url} title={s.title || (s.media_kind === "video" ? "Видео" : "Фото")}
            sub={s.media_kind === "video" ? "видео" : "фото"} badge={s.is_published ? undefined : "Скрыто"}
            onClick={() => { setDraft({ ...s }); setNote(null); }} />
        ))}
      </ul>
    </>
  );
}

/* --- баннер --- */
interface BannerData { banner_title: string; banner_text: string; banner_button: string; banner_image_url: string }

function BannerAdmin() {
  const q = useLoad(() => api.admin.get<BannerData>("settings"), []);
  const [draft, setDraft] = useState<BannerData | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const d = draft ?? q.data;
  const set = (k: keyof BannerData, v: string) => setDraft({ ...d, [k]: v });
  async function save() {
    try { await api.admin.send("PUT", "settings", d); setNote("Баннер обновлён"); setError(null); }
    catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  return (
    <div className="form">
      <h2>Приветственный баннер</h2>
      <MediaField label="Фоновое фото или видео (необязательно)" value={d.banner_image_url} onChange={(u) => set("banner_image_url", u)} />
      <label>Заголовок<input className="input" value={d.banner_title} onChange={(e) => set("banner_title", e.target.value)} /></label>
      <label>Текст<textarea className="input" rows={3} value={d.banner_text} onChange={(e) => set("banner_text", e.target.value)} /></label>
      <label>Текст кнопки<input className="input" value={d.banner_button} onChange={(e) => set("banner_button", e.target.value)} /></label>
      {note && <div className="notice good"><p>{note}</p></div>}
      {error && <ErrorBox message={error} />}
      <button className="btn" onClick={save}>Сохранить</button>
    </div>
  );
}

/* ---------- Разработчик ---------- */

function Errors() {
  const q = useLoad(() => api.admin.get<{ id: number; created_at: string; source: string; order_id: number | null; message: string }[]>("dev/errors"), []);
  if (q.loading) return <Loading />;
  if (q.error) return <ErrorBox message={q.error} onRetry={q.reload} />;
  if (!q.data?.length) return <p className="muted center pad">Технических ошибок нет.</p>;
  return (
    <ul className="list">
      {q.data.map((e) => (
        <li key={e.id} className="logrow">
          <span className="muted small">{new Date(e.created_at).toLocaleString("ru-RU")} · {e.source}{e.order_id ? ` · заказ #${e.order_id}` : ""}</span>
          <code>{e.message}</code>
        </li>
      ))}
    </ul>
  );
}

function DevOrders() {
  const [status, setStatus] = useState("");
  const q = useLoad(() => api.admin.get<{ id: number; user_id: number; kind: string; status: string; title: string; model: string; provider: string | null; provider_cost_usd: number; is_stub: number; error: string | null }[]>(`dev/orders?status=${status}`), [status]);
  return (
    <>
      <div className="chips scroll">
        {["", "created", "processing", "done", "failed"].map((s) => (
          <button key={s} className={`chip ${status === s ? "on" : ""}`} onClick={() => setStatus(s)}>{s || "Все"}</button>
        ))}
      </div>
      {q.loading && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      <ul className="list">
        {(q.data ?? []).map((o) => (
          <li key={o.id} className="logrow">
            <span><b>#{o.id}</b> {o.title} · <span className={`status ${o.status}`}>{o.status}</span></span>
            <span className="muted small">user {o.user_id} · {o.model} · {o.provider ?? "—"}{o.is_stub ? " (заглушка)" : ""} · ${o.provider_cost_usd}</span>
            {o.error && <code>{o.error}</code>}
          </li>
        ))}
      </ul>
    </>
  );
}

interface Diag {
  ai_mode: string; payments_mode: string; bot_token_set: boolean; webapp_url: string | null; dev_mode: boolean;
  providers: { model: string; kind: string; provider: string; configured: boolean; stub: boolean }[];
  order_status_counts: Record<string, number>;
  costs: { model: string; kind: string; generations: number; avg_cost_usd: number; total_cost_usd: number }[];
}

function Diagnostics() {
  const q = useLoad(() => api.admin.get<Diag>("dev/diagnostics"), []);
  if (q.loading) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const d = q.data;
  const yn = (v: boolean) => (v ? "да" : "нет");
  return (
    <>
      <div className="stats">
        <Stat label="AI_MODE" value={d.ai_mode} />
        <Stat label="PAYMENTS_MODE" value={d.payments_mode} />
        <Stat label="BOT_TOKEN задан" value={yn(d.bot_token_set)} />
        <Stat label="WEBAPP_URL" value={d.webapp_url ?? "не задан"} />
        <Stat label="DEV_MODE" value={yn(d.dev_mode)} />
      </div>
      <Section title="Провайдеры генерации">
        <ul className="list">
          {d.providers.map((p) => (
            <li key={`${p.model}-${p.kind}`} className="logrow">
              <span><b>{p.model}</b> · {p.kind} · {p.provider}</span>
              <span className="muted small">ключ/доступ: {yn(p.configured)}{p.stub ? " · заглушка/тест, не настоящая генерация" : ""}</span>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Заказы по статусам">
        <p>{Object.entries(d.order_status_counts).map(([k, v]) => `${k}: ${v}`).join(" · ") || "пока пусто"}</p>
      </Section>
      <Section title="Стоимость генераций">
        <ul className="list">
          {d.costs.map((c) => (
            <li key={`${c.model}-${c.kind}`} className="ledger">
              <span>{c.model} · {c.kind}<br /><span className="muted small">{c.generations} шт.</span></span>
              <span>${c.avg_cost_usd.toFixed(4)} в среднем · ${c.total_cost_usd.toFixed(4)} всего</span>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
