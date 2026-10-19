import { useState } from "react";
import { api } from "../api";
import { showToast } from "../ctx";
import { fmtTime, nf, pct, usd } from "../format";
import { Icon } from "../icons";
import { Chips, ErrorBox, Loading, Sheet, useLoad } from "../ui";
import { ConfirmModal, Field, MediaPicker, SelectInput, Stepper, SwitchRow, TextArea, TextInput, errText } from "./kit";
import { Kpi, stateLabel } from "./parts";
import { pq, usePeriod } from "./shell";
import { DataTable, Pager } from "./table";

/* ---------- Ошибки и журналы ---------- */
interface ErrPage { items: { id: number; created_at: string; user: string; order_id: number | null; provider: string | null; error_type: string; message: string; severity: string; source: string }[]; total: number; stats: { today: number; h24: number; d7: number; rate_24h: number | null; rate_7d: number | null }; providers: string[] }
const SEV: Record<string, string> = { error: "Ошибка", warning: "Предупреждение" };
const ETYPE: Record<string, string> = { provider_error: "Ошибка провайдера", provider_not_configured: "Провайдер не подключён", timeout: "Тайм-аут", restart: "Перезапуск сервиса", unknown: "Не определён" };

export function Errors() {
  const [sev, setSev] = useState("");
  const [page, setPage] = useState(1);
  const q = useLoad(() => api.admin.get<ErrPage>(`errors?severity=${sev}&page=${page}&size=25`), [sev, page]);
  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  const s = q.data.stats;
  return (
    <>
      <div className="kpi-groups">
        <Kpi title="Ошибок" big={nf(s.today)} bigLabel="Сегодня" orange rows={[["За 24 часа", nf(s.h24)], ["За 7 дней", nf(s.d7)]]} />
        <Kpi title="Процент ошибок" big={pct(s.rate_24h)} bigLabel="Генераций с ошибкой за 24 часа" rows={[["За 7 дней", pct(s.rate_7d)]]} />
      </div>
      <Chips value={sev} onChange={(v) => { setSev(v); setPage(1); }} options={[["", "Все"], ["error", "Ошибки"], ["warning", "Предупреждения"]]} />
      <DataTable rows={q.data.items} empty="Ошибок нет" cols={[
        { key: "id", title: "ID" }, { key: "created_at", title: "Дата", render: (e) => fmtTime(e.created_at) }, { key: "user", title: "Пользователь" },
        { key: "order_id", title: "Генерация", render: (e) => (e.order_id ? `№${e.order_id}` : "—") }, { key: "provider", title: "Провайдер", render: (e) => e.provider ?? "—" },
        { key: "error_type", title: "Тип", render: (e) => ETYPE[e.error_type] ?? e.error_type },
        { key: "message", title: "Сообщение", wrap: true, render: (e) => <code>{e.message}</code> },
        { key: "severity", title: "Серьёзность", render: (e) => <span className={`status ${e.severity === "error" ? "failed" : "processing"}`}>{SEV[e.severity] ?? e.severity}</span> },
      ]} />
      <Pager page={page} size={25} total={q.data.total} onPage={setPage} />
    </>
  );
}

/* ---------- AI-провайдеры и модели ---------- */
interface Prov { model: string; generations: number; ok: number; errors: number; success_rate: number | null; avg_seconds: number | null; cost_usd: number; cost_per_generation: number | null; credits: number }
interface Model { id?: number; slug?: string; tags?: string; name: string; kind: "photo" | "video" | "audio"; description: string; purpose: string; audience: string; image_url: string; provider_key: string; price_credits: number; is_active: number | boolean; sort_order: number; generations?: number }

function ProviderStats() {
  const { period } = usePeriod();
  const q = pq(period);
  const r = useLoad(() => api.admin.get<{ items: Prov[]; connected: { model: string; kind: string; provider: string; configured: boolean; stub: boolean }[] }>(`analytics/providers?${q}`), [q]);
  if (!r.data) return r.error ? <ErrorBox message={r.error} onRetry={r.reload} /> : <Loading />;
  return (
    <>
      <div className="card"><h2>Подключение провайдеров</h2>
        <DataTable rows={r.data.connected} cols={[{ key: "model", title: "Ключ", render: (p) => <b>{p.model}</b> }, { key: "kind", title: "Тип", render: (p) => (p.kind === "photo" ? "Фото" : "Видео") }, { key: "provider", title: "Провайдер" },
          { key: "configured", title: "Состояние", render: (p) => (p.stub ? <span className="status processing">Заглушка / тест</span> : p.configured ? <span className="status">Подключён</span> : <span className="status failed">Не подключён</span>) }]} /></div>
      <div className="card"><h2>Статистика за период</h2>
        <DataTable rows={r.data.items} empty="За период генераций не было" cols={[
          { key: "model", title: "Провайдер", render: (p) => <b>{p.model}</b> }, { key: "generations", title: "Генераций", num: true, render: (p) => nf(p.generations) },
          { key: "success_rate", title: "Успешность", num: true, render: (p) => pct(p.success_rate) }, { key: "errors", title: "Ошибок", num: true, render: (p) => nf(p.errors) },
          { key: "avg_seconds", title: "Среднее время, с", num: true, render: (p) => (p.avg_seconds !== null ? p.avg_seconds : "—") },
          { key: "cost_usd", title: "Стоимость, $", num: true, render: (p) => usd(p.cost_usd) }, { key: "cost_per_generation", title: "Стоимость одной, $", num: true, render: (p) => (p.cost_per_generation !== null ? usd(p.cost_per_generation) : "—") },
          { key: "credits", title: "Потрачено токенов", num: true, render: (p) => nf(p.credits) },
        ]} /></div>
    </>
  );
}

function Models() {
  const q = useLoad(() => api.admin.get<{ items: Model[]; provider_keys: string[] }>("models"), []);
  const [edit, setEdit] = useState<Model | null>(null);
  const [del, setDel] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  const tagText = (raw?: string): string => { try { const v = JSON.parse(raw || "[]"); return Array.isArray(v) ? v.join(", ") : ""; } catch { return raw ?? ""; } };
  const blank: Model = { slug: "", tags: "", name: "", kind: "photo", description: "", purpose: "", audience: "", image_url: "", provider_key: q.data.provider_keys[0], price_credits: 2, is_active: false, sort_order: (q.data.items.length + 1) * 10 };
  async function save() {
    if (!edit) return;
    setError(null);
    try {
      if (edit.id) await api.admin.send("PUT", `models/${edit.id}`, edit); else await api.admin.send("POST", "models", edit);
      setEdit(null); q.reload(); showToast("Сохранено");
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!edit?.id) return;
    const r = await api.admin.del<{ deleted: boolean }>(`models/${edit.id}`);
    setEdit(null); setDel(false); q.reload(); showToast(r.deleted ? "Модель удалена" : "У модели есть история генераций — она отключена");
  }
  return (
    <>
      <div className="notice info"><p>Карточки моделей показываются на главной и в генераторе. Новая карточка добавляется здесь, без правки интерфейса. Чтобы подключить нового провайдера, его нужно один раз реализовать в коде (<code>app/ai/external.py</code>).</p></div>
      <div className="toolbar"><button className="btn orange sm" onClick={() => { setEdit({ ...blank }); setError(null); }}><Icon name="plus" size={16} /> Добавить модель</button></div>
      <DataTable rows={q.data.items} empty="Моделей пока нет" onRow={(m) => { setEdit({ ...m, tags: tagText(m.tags) }); setError(null); }} cols={[
        { key: "name", title: "Название", render: (m) => <b>{m.name}</b> }, { key: "kind", title: "Тип", render: (m) => (m.kind === "photo" ? "Фото" : m.kind === "audio" ? "Аудио" : "Видео") },
        { key: "purpose", title: "Назначение", wrap: true }, { key: "provider_key", title: "Провайдер" }, { key: "price_credits", title: "Токены", num: true },
        { key: "generations", title: "Генераций", num: true, render: (m) => nf(m.generations ?? 0) },
        { key: "is_active", title: "Статус", render: (m) => <span className={`status ${m.is_active ? "" : "off"}`}>{m.is_active ? "Активна" : "Выключена"}</span> },
      ]} />
      {edit && (
        <Sheet title={edit.id ? "Модель" : "Новая модель"} onClose={() => setEdit(null)}>
          <div className="sheet-body">
            <MediaPicker label="Изображение карточки" value={edit.image_url} onChange={(v) => setEdit({ ...edit, image_url: v })} ratio="16 / 9" />
            <Field label="Название"><TextInput value={edit.name} onChange={(v) => setEdit({ ...edit, name: v })} /></Field>
            <Field label="Описание"><TextArea value={edit.description} onChange={(v) => setEdit({ ...edit, description: v })} rows={3} /></Field>
            <Field label="Назначение"><TextInput value={edit.purpose} onChange={(v) => setEdit({ ...edit, purpose: v })} placeholder="Например: реалистичные фото и портреты" /></Field>
            <Field label="Кому подходит (через запятую)"><TextInput value={edit.audience} onChange={(v) => setEdit({ ...edit, audience: v })} placeholder="фотографам, блогерам, бизнесу" /></Field>
            <Field label="Код модели (slug)" hint="Латиницей, например nano-banana-2. Нужен для моделей по умолчанию."><TextInput value={edit.slug ?? ""} onChange={(v) => setEdit({ ...edit, slug: v })} /></Field>
            <Field label="Категории (через запятую)" hint="Фото: photoreal, art, edit, fast, hq, new. Видео: t2v, i2v, anim, cine, motion, upscale. Аудио: voiceover, voice, ad, story, emotion. Ограничения ввода: in:image (нужно исходное изображение), in:text (только текст)."><TextInput value={edit.tags ?? ""} onChange={(v) => setEdit({ ...edit, tags: v })} /></Field>
            <Field label="Тип"><SelectInput value={edit.kind} onChange={(v) => setEdit({ ...edit, kind: v as "photo" | "video" | "audio" })} options={[["photo", "Фото"], ["video", "Видео"], ["audio", "Аудио"]]} /></Field>
            <Field label="Провайдер" hint="Ключ готового провайдера из app/ai"><SelectInput value={edit.provider_key} onChange={(v) => setEdit({ ...edit, provider_key: v })} options={q.data!.provider_keys.map((k): [string, string] => [k, k])} /></Field>
            <Field label="Стоимость, токенов"><Stepper value={edit.price_credits} onChange={(v) => setEdit({ ...edit, price_credits: v })} /></Field>
            <Field label="Порядок"><Stepper value={edit.sort_order} onChange={(v) => setEdit({ ...edit, sort_order: v })} step={10} /></Field>
            <SwitchRow label="Активна" hint="Показывается на главной и доступна в генераторе" checked={!!edit.is_active} onChange={(v) => setEdit({ ...edit, is_active: v })} />
            {error && <ErrorBox message={error} />}
            <button className="btn orange block" onClick={save}>Сохранить</button>
            {edit.id && <button className="btn ghost danger-text block" onClick={() => setDel(true)}>Удалить модель</button>}
          </div>
        </Sheet>
      )}
      {del && <ConfirmModal title="Удалить модель?" text="Если по модели уже есть генерации, она будет отключена, а статистика сохранится." confirm="Удалить" onConfirm={remove} onClose={() => setDel(false)} />}
    </>
  );
}

export function Providers() {
  const [tab, setTab] = useState<"stats" | "models">("stats");
  return (
    <>
      <div className="tabs-line"><button className={tab === "stats" ? "on" : ""} onClick={() => setTab("stats")}>Провайдеры</button><button className={tab === "models" ? "on" : ""} onClick={() => setTab("models")}>AI-модели в интерфейсе</button></div>
      {tab === "stats" ? <ProviderStats /> : <Models />}
    </>
  );
}

/* ---------- Система ---------- */
export function SystemPage() {
  const q = useLoad(() => api.admin.get<{ code: string; title: string; status: string; detail: string }[]>("system"), []);
  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  return (
    <>
      <div className="toolbar"><span style={{ flex: 1 }} /><button className="btn outline sm" onClick={q.reload}><Icon name="refresh" size={16} /> Обновить</button></div>
      <div className="sys-grid">
        {q.data.map((s) => (
          <div key={s.code} className={`sys-card ${s.status}`}><div className="card-head"><b style={{ fontSize: 17 }}>{s.title}</b><span className={`state ${s.status}`}>{stateLabel(s.status)}</span></div><span className="muted">{s.detail}</span></div>
        ))}
      </div>
    </>
  );
}
