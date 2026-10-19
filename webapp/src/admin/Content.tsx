import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api";
import { showToast } from "../ctx";
import { Icon } from "../icons";
import { ErrorBox, Loading, Sheet, useLoad } from "../ui";
import { ShowcaseAdmin } from "./Catalogue";
import { Card, ConfirmModal, Field, MediaPicker, Stepper, SwitchRow, TextArea, TextInput, errText } from "./kit";

interface Item { title: string; text: string }
type Blocks = {
  hero: { title: string; text: string; primary: string; secondary: string }; capabilities: Item[]; steps: Item[]; why: Item[];
  about: { title: string; text: string }; tokens: { title: string; text: string }; payment: { title: string; text: string }; cta: { title: string; text: string; button: string };
};

function ObjectBlock({ name, title, hint, fields, value, onSaved, extra }: { name: string; title: string; hint?: string; fields: [string, string, boolean?][]; value: Record<string, string>; onSaved: () => void; extra?: ReactNode }) {
  const [v, setV] = useState(value);
  const [saving, setSaving] = useState(false);
  useEffect(() => setV(value), [value]);
  const dirty = JSON.stringify(v) !== JSON.stringify(value);
  async function save() {
    setSaving(true);
    try { await api.admin.send("PUT", `content/${name}`, { value: v }); showToast("Сохранено"); onSaved(); }
    catch (e) { showToast(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }
  return (
    <Card title={title} hint={hint}>
      {extra}
      {fields.map(([k, label, area]) => (
        <Field key={k} label={label}>{area ? <TextArea value={v[k] ?? ""} onChange={(x) => setV({ ...v, [k]: x })} rows={3} /> : <TextInput value={v[k] ?? ""} onChange={(x) => setV({ ...v, [k]: x })} />}</Field>
      ))}
      <button className="btn orange sm" disabled={!dirty || saving} onClick={save}>{saving ? "Сохраняем…" : "Сохранить"}</button>
    </Card>
  );
}

function ListBlock({ name, title, hint, value, onSaved }: { name: string; title: string; hint?: string; value: Item[]; onSaved: () => void }) {
  const [v, setV] = useState(value);
  const [saving, setSaving] = useState(false);
  useEffect(() => setV(value), [value]);
  const dirty = JSON.stringify(v) !== JSON.stringify(value);
  const set = (i: number, patch: Partial<Item>) => setV(v.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  async function save() {
    setSaving(true);
    try { await api.admin.send("PUT", `content/${name}`, { value: v }); showToast("Сохранено"); onSaved(); }
    catch (e) { showToast(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }
  return (
    <Card title={title} hint={hint}>
      <div className="rows-edit">
        {v.map((x, i) => (
          <div key={i} className="row-edit">
            <input className="input" value={x.title} onChange={(e) => set(i, { title: e.target.value })} placeholder="Заголовок" />
            <input className="input" value={x.text} onChange={(e) => set(i, { text: e.target.value })} placeholder="Описание" />
            <button className="icon-plain danger" onClick={() => setV(v.filter((_, j) => j !== i))} aria-label="Убрать"><Icon name="trash" size={18} /></button>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn outline sm" onClick={() => setV([...v, { title: "", text: "" }])}><Icon name="plus" size={16} /> Добавить</button>
        <button className="btn orange sm" disabled={!dirty || saving} onClick={save}>{saving ? "Сохраняем…" : "Сохранить"}</button>
      </div>
    </Card>
  );
}

function HomeBlocks() {
  const q = useLoad(() => api.admin.get<Blocks>("content"), []);
  const st = useLoad(() => api.admin.get<{ banner_image_url: string }>("settings"), []);
  const [img, setImg] = useState("");
  useEffect(() => setImg(st.data?.banner_image_url ?? ""), [st.data]);
  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  const b = q.data;
  async function saveImg(url: string) {
    setImg(url);
    try { await api.admin.send("PUT", "settings", { banner_image_url: url }); showToast("Фон главной сохранён"); }
    catch (e) { showToast(errText(e, "Не удалось сохранить")); }
  }
  return (
    <>
      <p className="muted small">Всё, что вы меняете здесь, сразу отображается на главной странице приложения.</p>
      <ObjectBlock name="hero" title="Первый экран (hero)" value={b.hero} onSaved={q.reload} fields={[["title", "Заголовок"], ["text", "Подзаголовок", true], ["primary", "Основная кнопка"], ["secondary", "Вторая кнопка"]]}
        extra={<MediaPicker label="Фон первого экрана (фото или видео)" value={img} onChange={saveImg} ratio="16 / 10" hint="Если пусто — берётся первая работа из «Популярных работ»" />} />
      <ListBlock name="capabilities" title="Что умеет Nolla AI" value={b.capabilities} onSaved={q.reload} />
      <ListBlock name="steps" title="Как это работает" hint="Шаги нумеруются автоматически" value={b.steps} onSaved={q.reload} />
      <ObjectBlock name="tokens" title="Блок «Токены»" value={b.tokens} onSaved={q.reload} fields={[["title", "Заголовок"], ["text", "Текст", true]]} />
      <ObjectBlock name="payment" title="Блок «Удобная оплата»" hint="Способы оплаты берутся из раздела «Платежи → Способы оплаты»" value={b.payment} onSaved={q.reload} fields={[["title", "Заголовок"], ["text", "Текст", true]]} />
      <ListBlock name="why" title="Почему Nolla AI" value={b.why} onSaved={q.reload} />
      <ObjectBlock name="about" title="О Nolla AI" value={b.about} onSaved={q.reload} fields={[["title", "Заголовок"], ["text", "Текст", true]]} />
      <ObjectBlock name="cta" title="Финальный призыв" value={b.cta} onSaved={q.reload} fields={[["title", "Заголовок"], ["text", "Подпись"], ["button", "Кнопка"]]} />
      <div className="notice info"><p>Модели, тренды, категории и пакеты токенов редактируются в своих разделах: «AI-провайдеры → Модели», «Тренды», «Категории», «Токены».</p></div>
    </>
  );
}

interface Faq { id?: number; question: string; answer: string; sort_order: number; is_active: number | boolean }

function FaqAdmin() {
  const q = useLoad(() => api.admin.get<Faq[]>("faq"), []);
  const [edit, setEdit] = useState<Faq | null>(null);
  const [del, setDel] = useState(false);
  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  async function save() {
    if (!edit) return;
    try {
      if (edit.id) await api.admin.send("PUT", `faq/${edit.id}`, edit); else await api.admin.send("POST", "faq", edit);
      setEdit(null); q.reload(); showToast("Сохранено");
    } catch (e) { showToast(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!edit?.id) return;
    await api.admin.del(`faq/${edit.id}`);
    setEdit(null); setDel(false); q.reload(); showToast("Вопрос удалён");
  }
  return (
    <>
      <div className="toolbar"><button className="btn orange sm" onClick={() => setEdit({ question: "", answer: "", sort_order: (q.data!.length + 1) * 10, is_active: true })}><Icon name="plus" size={16} /> Добавить вопрос</button></div>
      <ul className="list">
        {q.data.map((f) => (
          <li key={f.id}><button className="row-card" onClick={() => setEdit({ ...f })}>
            <span className="row-main"><b>{f.question}</b><span className="muted small">{f.answer.slice(0, 120)}{f.answer.length > 120 ? "…" : ""}</span></span>
            {!f.is_active && <span className="status off">Скрыт</span>}
          </button></li>
        ))}
      </ul>
      {q.data.length === 0 && <p className="muted center pad">Вопросов пока нет.</p>}
      {edit && (
        <Sheet title={edit.id ? "Вопрос" : "Новый вопрос"} onClose={() => setEdit(null)}>
          <div className="sheet-body">
            <Field label="Вопрос"><TextInput value={edit.question} onChange={(v) => setEdit({ ...edit, question: v })} /></Field>
            <Field label="Ответ"><TextArea value={edit.answer} onChange={(v) => setEdit({ ...edit, answer: v })} rows={5} /></Field>
            <Field label="Порядок"><Stepper value={edit.sort_order} onChange={(v) => setEdit({ ...edit, sort_order: v })} step={10} /></Field>
            <SwitchRow label="Показывать на главной" checked={!!edit.is_active} onChange={(v) => setEdit({ ...edit, is_active: v })} />
            <button className="btn orange block" onClick={save}>Сохранить</button>
            {edit.id && <button className="btn ghost danger-text block" onClick={() => setDel(true)}>Удалить вопрос</button>}
          </div>
        </Sheet>
      )}
      {del && <ConfirmModal title="Удалить вопрос?" text="Вопрос исчезнет с главной." confirm="Удалить" onConfirm={remove} onClose={() => setDel(false)} />}
    </>
  );
}

export function ContentAdmin() {
  const [tab, setTab] = useState<"home" | "faq" | "works">("home");
  return (
    <>
      <div className="tabs-line">
        <button className={tab === "home" ? "on" : ""} onClick={() => setTab("home")}>Главная страница</button>
        <button className={tab === "faq" ? "on" : ""} onClick={() => setTab("faq")}>Частые вопросы</button>
        <button className={tab === "works" ? "on" : ""} onClick={() => setTab("works")}>Популярные работы</button>
      </div>
      {tab === "home" && <HomeBlocks />}{tab === "faq" && <FaqAdmin />}{tab === "works" && <ShowcaseAdmin />}
    </>
  );
}
