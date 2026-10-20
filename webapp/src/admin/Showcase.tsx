import { useEffect, useState } from "react";
import { api } from "../api";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import { Chips, ErrorBox, Loading, PageHeader, Toggle, useLoad } from "../ui";
import { Card, ConfirmModal, Field, MediaPicker, SaveBar, SelectInput, Stepper, SwitchRow, TextArea, TextInput, errText, useDraft } from "./kit";

/** Витрина: карточки, которые видят пользователи в разделе «Идеи» и на главной. */
interface Row {
  id: number; title: string; description: string; kind: string; section: string; tag: string; price_credits: number;
  preview_url: string; is_published: number; is_popular: number; on_home: number; on_ideas: number; sort_order: number; uses: number;
}
interface Meta { categories: { id: string; title: string }[]; models: string[] }
interface ListData extends Meta { items: Row[] }

const SECTIONS: [string, string][] = [
  ["idea", "Идея"], ["effect", "Эффект"], ["photoshoot", "Фотосессия"], ["trend", "Тренд"], ["prompt", "Промпт"], ["marketing", "Маркетинг"],
];
const KINDS: [string, string][] = [["photo", "Фото"], ["video", "Видео"], ["audio", "Аудио"]];
const TAGS: [string, string][] = [
  ["photo", "Фото"], ["video", "Видео"], ["audio", "Аудио"], ["portrait", "Портрет"], ["fashion", "Мода"], ["couples", "Пары"],
  ["family", "Семья"], ["kids", "Дети"], ["lifestyle", "Образ жизни"], ["cinema", "Кино"], ["marketing", "Маркетинг"], ["other", "Другое"],
];

type Filter = "all" | "published" | "hidden" | "featured";

export function ShowcaseList() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<ListData>("templates"), []);
  const [filter, setFilter] = useState<Filter>("all");
  const [del, setDel] = useState<Row | null>(null);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;

  const all = q.data.items.filter((t) => t.section && t.section !== "legacy");
  const items = all.filter((t) => filter === "all" || (filter === "published" && t.is_published) || (filter === "hidden" && !t.is_published) || (filter === "featured" && t.is_popular));

  async function patch(t: Row, body: Record<string, unknown>) {
    try { await api.admin.send("PUT", `templates/${t.id}`, body); q.reload(); }
    catch (e) { showToast(errText(e, "Не удалось изменить")); }
  }
  async function move(t: Row, direction: "up" | "down") {
    try {
      const r = await api.admin.send<{ moved: boolean }>("POST", `templates/${t.id}/move`, { direction });
      if (!r.moved) showToast("Уже с краю");
      q.reload();
    } catch (e) { showToast(errText(e, "Не удалось переставить")); }
  }
  async function duplicate(t: Row) {
    try { const copy = await api.admin.send<Row>("POST", `templates/${t.id}/duplicate`, {}); showToast("Копия создана — она скрыта"); nav.go({ name: "admin", page: "template", id: String(copy.id) }); }
    catch (e) { showToast(errText(e, "Не удалось скопировать")); }
  }
  async function remove() {
    if (!del) return;
    try {
      const r = await api.admin.del<{ deleted: boolean; orders: number }>(`templates/${del.id}`);
      showToast(r.deleted ? "Карточка удалена" : `По карточке были заказы (${r.orders}) — она скрыта, история сохранена`);
      setDel(null); q.reload();
    } catch (e) { showToast(errText(e, "Не удалось удалить")); setDel(null); }
  }

  const sectionName = (s: string) => SECTIONS.find(([id]) => id === s)?.[1] ?? s;
  return (
    <>
      <PageHeader title="Витрина" onBack={nav.back} />
      <div className="notice info"><p>Здесь вы наполняете раздел «Идеи» и главную. «Рекомендуем» поднимает карточку выше остальных, стрелки меняют порядок.</p></div>
      <Chips value={filter} onChange={setFilter} options={[["all", `Все ${all.length}`], ["published", "Показаны"], ["hidden", "Скрыты"], ["featured", "Рекомендуем"]]} />
      <ul className="list">
        {items.map((t) => (
          <li key={t.id} className="sc-row">
            <span className="sc-thumb">{t.preview_url ? <img src={t.preview_url} alt="" /> : <Icon name="image" size={18} />}</span>
            <span className="row-main">
              <b>{t.title}</b>
              <span className="muted small">{sectionName(t.section)} · {KINDS.find(([k]) => k === t.kind)?.[1]} · {t.price_credits} ток. · порядок {t.sort_order} · использований: {t.uses}</span>
              <span className="sc-flags">
                {!!t.is_popular && <span className="tag dark">Рекомендуем</span>}
                {!t.on_home && <span className="tag">Не на главной</span>}
                {!t.on_ideas && <span className="tag">Не в идеях</span>}
              </span>
            </span>
            <span className="sc-acts">
              <button className="icon-plain" aria-label="Выше" onClick={() => move(t, "up")}><Icon name="chevron-down" size={18} className="rot" /></button>
              <button className="icon-plain" aria-label="Ниже" onClick={() => move(t, "down")}><Icon name="chevron-down" size={18} /></button>
              <button className="icon-plain" aria-label="Рекомендуем" onClick={() => patch(t, { is_popular: !t.is_popular })}><Icon name="heart" size={17} fill={!!t.is_popular} /></button>
              <button className="icon-plain" aria-label="Дублировать" onClick={() => duplicate(t)}><Icon name="copy" size={17} /></button>
              <button className="icon-plain" aria-label="Редактировать" onClick={() => nav.go({ name: "admin", page: "template", id: String(t.id) })}><Icon name="edit" size={17} /></button>
              <button className="icon-plain danger" aria-label="Удалить" onClick={() => setDel(t)}><Icon name="trash" size={17} /></button>
              <Toggle checked={!!t.is_published} onChange={(v) => patch(t, { is_published: v })} label="Показывать" />
            </span>
          </li>
        ))}
      </ul>
      {items.length === 0 && <p className="muted center pad">Пока пусто. Добавьте первую карточку.</p>}
      <div className="fab-bar"><button className="btn gold block" onClick={() => nav.go({ name: "admin", page: "showcase-new", id: "new" })}><Icon name="plus" size={18} /> Добавить на витрину</button></div>
      {del && <ConfirmModal title="Удалить карточку?" text="Если по ней были заказы, она не удалится, а скроется — чтобы сохранилась история." confirm="Удалить" onConfirm={remove} onClose={() => setDel(null)} />}
    </>
  );
}

interface Form {
  title: string; description: string; section: string; kind: string; tag: string; prompt: string; preview_url: string;
  model: string; price_credits: number; sort_order: number; is_published: boolean; is_popular: boolean; on_home: boolean; on_ideas: boolean;
  category: string; required: string;
}
const EMPTY: Form = {
  title: "", description: "", section: "idea", kind: "photo", tag: "photo", prompt: "", preview_url: "", model: "image-default",
  price_credits: 12, sort_order: 100, is_published: true, is_popular: false, on_home: true, on_ideas: true, category: "", required: "",
};

/** Форма «Добавить на витрину» — всё, что видит пользователь на карточке. */
export function ShowcaseEditor() {
  const { nav } = useApp();
  const meta = useLoad(() => api.admin.get<Meta>("templates"), []);
  const form = useDraft<Form>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { reset, draft: d, set } = form;
  useEffect(() => { if (meta.data && !d.category) reset({ ...EMPTY, category: meta.data.categories[0]?.id ?? "" }); }, [meta.data]); // eslint-disable-line react-hooks/exhaustive-deps

  async function save() {
    setSaving(true); setError(null);
    try {
      await api.admin.send("POST", "templates", { ...d, required: d.required ? d.required.split(",").map((x) => x.trim()).filter(Boolean) : [] });
      showToast("Карточка добавлена на витрину");
      nav.back();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }

  if (!meta.data) return <Loading />;
  const videoKind = d.kind === "video";
  return (
    <>
      <PageHeader title="Добавить на витрину" onBack={nav.back} />
      <Card title="Что это" hint="Карточка появится в разделе «Идеи» и, если нужно, на главной">
        <Field label="Название"><TextInput value={d.title} onChange={(v) => set("title", v)} placeholder="Чёрно-белая кинематографическая фотосессия" /></Field>
        <Field label="Описание"><TextArea value={d.description} onChange={(v) => set("description", v)} rows={3} placeholder="Создайте портрет в стиле современной чёрно-белой редакционной съёмки." /></Field>
        <Field label="Раздел"><SelectInput value={d.section} onChange={(v) => set("section", v)} options={SECTIONS} /></Field>
        <Field label="Тип результата">
          <SelectInput value={d.kind} onChange={(v) => { set("kind", v); set("model", v === "photo" ? "image-default" : v === "video" ? "video-default" : "audio-default"); }} options={KINDS} />
        </Field>
        <Field label="Категория"><SelectInput value={d.tag} onChange={(v) => set("tag", v)} options={TAGS} /></Field>
      </Card>

      <Card title="Превью" hint={videoKind ? "Для видео лучше формат 16:9" : "Вертикальное изображение 9:16"}>
        <MediaPicker label={videoKind ? "Изображение или видео-превью" : "Изображение превью"} value={d.preview_url} onChange={(v) => set("preview_url", v)} ratio={videoKind ? "16 / 9" : "9 / 16"} />
        <p className="field-hint">Если превью не загрузить, подставится одно из ваших фото из «Контент → Фото для обложек».</p>
      </Card>

      <Card title="Генерация" hint="Что произойдёт, когда пользователь нажмёт «Попробовать»">
        <Field label="Промпт"><TextArea value={d.prompt} onChange={(v) => set("prompt", v)} rows={4} placeholder="Black and white editorial portrait, soft studio light…" /></Field>
        <Field label="Модель"><SelectInput value={d.model} onChange={(v) => set("model", v)} options={meta.data.models.map((m) => [m, m])} /></Field>
        <Field label="Нужные материалы" hint="Через запятую: photo, person, product, idea. Пусто — ничего не требуется."><TextInput value={d.required} onChange={(v) => set("required", v)} placeholder="person" /></Field>
        <Field label="Стоимость, токенов"><Stepper value={d.price_credits} onChange={(v) => set("price_credits", v)} /></Field>
      </Card>

      <Card title="Где показывать">
        <SwitchRow label="Показывать пользователям" hint="Снимите, чтобы подготовить карточку и опубликовать позже" checked={d.is_published} onChange={(v) => set("is_published", v)} />
        <SwitchRow label="Показывать на главной" hint="Блок «Популярные идеи»" checked={d.on_home} onChange={(v) => set("on_home", v)} />
        <SwitchRow label="Показывать в разделе «Идеи»" checked={d.on_ideas} onChange={(v) => set("on_ideas", v)} />
        <SwitchRow label="Рекомендуем" hint="Карточка поднимается выше остальных" checked={d.is_popular} onChange={(v) => set("is_popular", v)} />
        <Field label="Порядок" hint="Чем меньше число, тем выше"><Stepper value={d.sort_order} onChange={(v) => set("sort_order", v)} step={10} /></Field>
      </Card>

      <div className="savebar-gap" />
      <SaveBar dirty={true} saving={saving} onSave={save} error={error} label="Добавить" />
    </>
  );
}
