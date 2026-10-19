import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { showToast } from "../ctx";
import { Chips, ErrorBox, Loading, PageHeader, Section, Toggle, useLoad } from "../ui";
import { Card, Field, SelectInput, StatTile, Stepper, SwitchRow, errText } from "./kit";
import { useEffect, useState as useS } from "react";

/* ---------- Дашборд ---------- */
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

function Tile({ icon, title, sub, onClick }: { icon: IconName; title: string; sub: string; onClick: () => void }) {
  return (
    <button className="admin-tile" onClick={onClick}>
      <span className="admin-tile-icon"><Icon name={icon} size={22} /></span>
      <b>{title}</b>
      <span className="muted small">{sub}</span>
    </button>
  );
}

export function Dashboard() {
  const { me, nav } = useApp();
  const owner = me.roles.includes("owner");
  const dev = me.roles.includes("developer");
  const ov = useLoad(() => (owner ? api.admin.get<OverviewData>("overview") : Promise.resolve(null)), [owner]);
  const go = (page: string) => nav.go({ name: "admin", page });
  const d = ov.data;
  return (
    <>
      <PageHeader title="Админ-панель" onBack={nav.back} />
      {owner && (
        <>
          {ov.loading && !d && <Loading />}
          {ov.error && <ErrorBox message={ov.error} onRetry={ov.reload} />}
          {d && (
            <>
              <div className="stat-grid">
                <StatTile label="Пользователи" value={d.users} />
                <StatTile label="Генерации" value={d.generations.photo.done + d.generations.video.done} sub={`фото ${d.generations.photo.done} · видео ${d.generations.video.done}`} />
                <StatTile label="Выручка (оценка)" value={`$${d.revenue_usd_estimate}`} sub={`${d.stars_received} ⭐ · покупок ${d.purchases}`} />
                <StatTile label="Прибыль (оценка)" value={`$${d.profit_usd_estimate}`} sub={`расходы на AI $${d.ai_cost_usd}`} />
              </div>
              <p className="muted small">{d.note} Тестовых покупок: {d.test_purchases}. Бесплатных генераций: {d.free_generations_done}. Кредитов у людей: {d.credits_in_circulation}.</p>
            </>
          )}
          <Section title="Содержимое">
            <div className="tiles">
              <Tile icon="wand" title="Стили и примеры" sub="Шаблоны, превью, цены" onClick={() => go("templates")} />
              <Tile icon="sparkle" title="Свободная генерация" sub="Цена и модель «+»" onClick={() => go("freeform")} />
              <Tile icon="grid" title="Категории" sub="Обложки и порядок" onClick={() => go("categories")} />
              <Tile icon="home" title="Главная" sub="Баннер и поддержка" onClick={() => go("content")} />
              <Tile icon="image" title="Популярные работы" sub="Ваши фото и видео" onClick={() => go("showcase")} />
              <Tile icon="coin" title="Пакеты кредитов" sub="Цены и плашки" onClick={() => go("packages")} />
              <Tile icon="users" title="Пользователи" sub="Балансы и активность" onClick={() => go("users")} />
            </div>
          </Section>
        </>
      )}
      {dev && (
        <Section title="Для разработчика">
          <div className="tiles">
            <Tile icon="bug" title="Ошибки" sub="Журнал сбоев" onClick={() => go("errors")} />
            <Tile icon="list" title="Задачи" sub="Статусы генераций" onClick={() => go("orders")} />
            <Tile icon="settings" title="Диагностика" sub="Режимы и провайдеры" onClick={() => go("diag")} />
          </div>
        </Section>
      )}
      {!owner && !dev && <ErrorBox message="Нет доступа" />}
    </>
  );
}

/* ---------- Пользователи ---------- */
interface UserRow { tg_id: number; username: string | null; first_name: string | null; balance: number; is_pro: number; photos: number; videos: number; stars_spent: number }

export function UsersAdmin() {
  const { nav } = useApp();
  const [search, setSearch] = useState("");
  const q = useLoad(() => api.admin.get<UserRow[]>(`users?search=${encodeURIComponent(search)}`), [search]);
  return (
    <>
      <PageHeader title="Пользователи" onBack={nav.back} />
      <label className="search"><Icon name="search" size={18} /><input placeholder="ID, имя или @username" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      <ul className="list">
        {(q.data ?? []).map((u) => (
          <li key={u.tg_id} className="hist boxed">
            <span className="row-main"><b>{u.first_name ?? "—"} {u.username ? <span className="muted">@{u.username}</span> : null}</b>
              <span className="muted small">ID {u.tg_id} · фото {u.photos} · видео {u.videos} · {u.stars_spent} ⭐</span></span>
            <span className="row-main" style={{ flex: "none", alignItems: "flex-end" }}>
              <b>{u.balance} кр.</b>
              <span className="muted small" style={{ display: "flex", alignItems: "center", gap: 6 }}>PRO <Toggle checked={!!u.is_pro} label="PRO" onChange={async (v) => {
                try { await api.admin.send("PUT", `users/${u.tg_id}/pro`, { on: v }); q.reload(); }
                catch (e) { showToast(errText(e, "Не удалось изменить")); }
              }} /></span>
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

/* ---------- Разработчик ---------- */
export function ErrorsAdmin() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<{ id: number; created_at: string; source: string; order_id: number | null; message: string }[]>("dev/errors"), []);
  return (
    <>
      <PageHeader title="Ошибки" onBack={nav.back} />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && q.data.length === 0 && <p className="muted center pad">Технических ошибок нет.</p>}
      <ul className="list">
        {(q.data ?? []).map((e) => (
          <li key={e.id} className="logrow">
            <span className="muted small">{new Date(e.created_at).toLocaleString("ru-RU")} · {e.source}{e.order_id ? ` · заказ #${e.order_id}` : ""}</span>
            <code>{e.message}</code>
          </li>
        ))}
      </ul>
    </>
  );
}

export function OrdersAdmin() {
  const { nav } = useApp();
  const [status, setStatus] = useState("");
  const q = useLoad(() => api.admin.get<{ id: number; user_id: number; status: string; title: string; model: string; provider: string | null; provider_cost_usd: number; is_stub: number; error: string | null }[]>(`dev/orders?status=${status}`), [status]);
  return (
    <>
      <PageHeader title="Задачи" onBack={nav.back} />
      <Chips value={status} onChange={setStatus} options={[["", "Все"], ["created", "В очереди"], ["processing", "В работе"], ["done", "Готово"], ["failed", "Ошибка"]]} />
      {q.loading && !q.data && <Loading />}
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

export function DiagAdmin() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<Diag>("dev/diagnostics"), []);
  const yn = (v: boolean) => (v ? "да" : "нет");
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const d = q.data;
  return (
    <>
      <PageHeader title="Диагностика" onBack={nav.back} />
      <div className="stat-grid">
        <StatTile label="AI_MODE" value={d.ai_mode} />
        <StatTile label="PAYMENTS_MODE" value={d.payments_mode} />
        <StatTile label="BOT_TOKEN задан" value={yn(d.bot_token_set)} />
        <StatTile label="DEV_MODE" value={yn(d.dev_mode)} />
      </div>
      <p className="muted small">WEBAPP_URL: {d.webapp_url ?? "не задан"}</p>
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
      <Section title="Заказы по статусам"><p>{Object.entries(d.order_status_counts).map(([k, v]) => `${k}: ${v}`).join(" · ") || "пока пусто"}</p></Section>
      <Section title="Стоимость генераций">
        <ul className="list">
          {d.costs.map((c) => (
            <li key={`${c.model}-${c.kind}`} className="hist boxed">
              <span className="row-main"><b>{c.model} · {c.kind}</b><span className="muted small">{c.generations} шт.</span></span>
              <span className="small">${c.avg_cost_usd.toFixed(4)} в среднем · ${c.total_cost_usd.toFixed(4)} всего</span>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}


/* ---------- Свободная генерация («+») ---------- */
interface FreeItem { id: number; kind: "photo" | "video"; title: string; model: string; price_credits: number; enabled: boolean }

function FreeCard({ item, models, onSaved }: { item: FreeItem; models: string[]; onSaved: () => void }) {
  const [price, setPrice] = useS(item.price_credits);
  const [model, setModel] = useS(item.model);
  const [enabled, setEnabled] = useS(item.enabled);
  const [saving, setSaving] = useS(false);
  const [error, setError] = useS<string | null>(null);
  useEffect(() => { setPrice(item.price_credits); setModel(item.model); setEnabled(item.enabled); }, [item]);
  const dirty = price !== item.price_credits || model !== item.model || enabled !== item.enabled;
  async function save() {
    setSaving(true); setError(null);
    try { await api.admin.send("PUT", `freeform/${item.kind}`, { price_credits: price, model, enabled }); showToast("Сохранено"); onSaved(); }
    catch (e) { setError(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }
  return (
    <Card title={item.kind === "photo" ? "Фото по описанию" : "Видео по описанию"} hint="Запрос из кнопки «+» без выбора готового стиля">
      <SwitchRow label="Включено" hint="Если выключить, «+» предложит выбрать готовый стиль" checked={enabled} onChange={setEnabled} />
      <Field label="Цена в кредитах"><Stepper value={price} onChange={setPrice} /></Field>
      <Field label="Модель"><SelectInput value={model} onChange={setModel} options={models.map((m) => [m, m])} /></Field>
      {error && <ErrorBox message={error} />}
      <button className="btn gold block" disabled={!dirty || saving} onClick={save}>{saving ? "Сохраняем…" : "Сохранить"}</button>
    </Card>
  );
}

export function FreeformAdmin() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<{ items: FreeItem[]; models: string[] }>("freeform"), []);
  return (
    <>
      <PageHeader title="Свободная генерация" onBack={nav.back} />
      <p className="muted small">Цена первой попытки — бесплатная для каждого пользователя. Дальше списывается цена из этих карточек.</p>
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {(q.data?.items ?? []).map((it) => <FreeCard key={it.kind} item={it} models={q.data!.models} onSaved={q.reload} />)}
    </>
  );
}
