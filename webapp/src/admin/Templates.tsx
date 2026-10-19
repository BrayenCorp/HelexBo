import { useEffect, useState } from "react";
import { api } from "../api";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import { Chips, ErrorBox, Loading, PageHeader, Toggle, useLoad } from "../ui";
import {
  Card, ConfirmModal, Field, ListRow, MediaGallery, MediaPicker, SaveBar, SelectInput, Stepper, SwitchRow, TextArea, TextInput, errText, useDraft,
} from "./kit";

interface Meta { categories: { id: string; title: string }[]; models: string[] }
interface TplRow { id: number; uses: number; title: string; style_label: string; category: string; kind: string; price_credits: number; preview_url: string; is_published: number; is_popular: number; is_trend: number; styles_count: number }
interface TplList extends Meta { items: TplRow[] }
interface Style { id?: string; title: string; prompt: string }
interface TplFull {
  id?: number; title: string; style_label: string; description: string; category: string; kind: "photo" | "video"; model: string; prompt: string;
  preview_url: string; price_credits: number; is_published: boolean; is_popular: boolean; is_trend: boolean; sort_order: number;
  styles: Style[]; examples: string[];
}

type TplApi = Omit<TplFull, "is_published" | "is_popular" | "is_trend"> & { is_published: number; is_popular: number; is_trend: number };

type Filter = "all" | "published" | "hidden" | "photo" | "video";

export function TemplatesList({ trend = false }: { trend?: boolean }) {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<TplList>("templates"), []);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  const cat = (id: string) => q.data!.categories.find((c) => c.id === id)?.title ?? id;
  const items = q.data.items.filter((t) =>
    (!trend || t.is_trend) && (filter === "all" || (filter === "published" && t.is_published) || (filter === "hidden" && !t.is_published) || t.kind === filter)
    && (!search || t.title.toLowerCase().includes(search.toLowerCase())));

  async function toggle(t: TplRow, v: boolean) {
    try { await api.admin.send("PUT", `templates/${t.id}`, { is_published: v }); q.reload(); }
    catch (e) { showToast(errText(e, "Не удалось изменить")); }
  }

  return (
    <>
      <PageHeader title={trend ? "Тренды" : "Шаблоны"} onBack={nav.back} />
      <label className="search"><Icon name="search" size={18} /><input placeholder="Поиск по названию" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
      <Chips value={filter} onChange={setFilter} options={[["all", `Все ${q.data.items.length}`], ["published", "Опубликованы"], ["hidden", "Скрыты"], ["photo", "Фото"], ["video", "Видео"]]} />
      <ul className="list">
        {items.map((t) => (
          <ListRow key={t.id} thumb={t.preview_url} title={t.title}
            sub={`${cat(t.category)}${t.style_label ? ` · ${t.style_label}` : ""} · ${t.kind === "photo" ? "фото" : "видео"} · ${t.price_credits} ток. · использований: ${t.uses}${t.is_popular ? " · популярное" : ""}${t.is_trend ? " · тренд" : ""}`}
            right={<Toggle checked={!!t.is_published} onChange={(v) => toggle(t, v)} label="Опубликован" />}
            onClick={() => nav.go({ name: "admin", page: "template", id: String(t.id) })} />
        ))}
      </ul>
      {items.length === 0 && <p className="muted center pad">Ничего не найдено.</p>}
      <div className="fab-bar"><button className="btn gold block" onClick={() => nav.go({ name: "admin", page: "template", id: trend ? "new-trend" : "new" })}><Icon name="plus" size={18} /> {trend ? "Добавить тренд" : "Добавить шаблон"}</button></div>
    </>
  );
}

const EMPTY: TplFull = {
  title: "", style_label: "", description: "", category: "", kind: "photo", model: "image-default", prompt: "", preview_url: "",
  price_credits: 2, is_published: false, is_popular: false, is_trend: false, sort_order: 100, styles: [], examples: [],
};

export function TemplateEditor({ id }: { id: string }) {
  const { nav } = useApp();
  const isNew = id.startsWith("new");
  const meta = useLoad(() => api.admin.get<TplList>("templates"), []);
  const form = useDraft<TplFull>(id === "new-trend" ? { ...EMPTY, is_trend: true } : EMPTY);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const { reset } = form;

  useEffect(() => {
    if (isNew) return;
    api.admin.get<TplApi>(`templates/${id}`)
      .then((t) => reset({ ...t, is_published: !!t.is_published, is_popular: !!t.is_popular, is_trend: !!t.is_trend }))
      .catch((e) => setError(errText(e, "Не удалось загрузить")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (isNew && meta.data && !form.draft.category) reset({ ...EMPTY, is_trend: id === "new-trend", category: meta.data.categories[0]?.id ?? "" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta.data]);

  if (loading || !meta.data) return <Loading />;
  const d = form.draft;
  const set = form.set;

  async function save() {
    setSaving(true); setError(null);
    try {
      const body = { ...d, styles: d.styles.map((s) => ({ ...s, title: s.title.trim() })).filter((s) => s.title) };
      if (isNew) await api.admin.send("POST", "templates", body);
      else await api.admin.send("PUT", `templates/${id}`, body);
      showToast("Сохранено");
      nav.back();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }

  async function remove() {
    try {
      const r = await api.admin.del<{ deleted: boolean; hidden: boolean; orders: number }>(`templates/${id}`);
      showToast(r.deleted ? "Шаблон удалён" : `По шаблону уже были заказы (${r.orders}) — он скрыт, история сохранена`);
      nav.back();
    } catch (e) { setError(errText(e, "Не удалось удалить")); setConfirmDel(false); }
  }

  const setStyle = (i: number, patch: Partial<Style>) => set("styles", d.styles.map((s, j) => (j === i ? { ...s, ...patch } : s)));

  return (
    <>
      <PageHeader title={isNew ? (id === "new-trend" ? "Новый тренд" : "Новый шаблон") : "Редактирование шаблона"} onBack={nav.back} />

      <Card title="Внешний вид" hint="Обложка видна в каталоге и на главной">
        <MediaPicker label="Обложка (фото или видео)" value={d.preview_url} onChange={(v) => set("preview_url", v)} hint="Лучше вертикальное фото 4:5" />
        <MediaGallery label="Примеры результата" value={d.examples} onChange={(v) => set("examples", v)} hint="Показываются на странице образа (до 8)" />
      </Card>

      <Card title="Основное">
        <Field label="Название"><TextInput value={d.title} onChange={(v) => set("title", v)} placeholder="Например, Маленький принц" /></Field>
        <Field label="Описание"><TextArea value={d.description} onChange={(v) => set("description", v)} rows={3} /></Field>
        <Field label="Категория"><SelectInput value={d.category} onChange={(v) => set("category", v)} options={meta.data.categories.map((c) => [c.id, c.title])} /></Field>
        <Field label="Стиль (подкатегория)" hint="Показывается фильтром внутри категории: Portrait, Fashion, Lifestyle, Studio…">
          <TextInput value={d.style_label} onChange={(v) => set("style_label", v)} placeholder="Например, Portrait" />
          <div className="wrap-chips">
            {["Portrait", "Fashion", "Lifestyle", "Studio", "Cinematic", "Street", "Beauty", "Editorial"].map((l) => (
              <button key={l} type="button" className={`chip ${d.style_label === l ? "on" : ""}`} onClick={() => set("style_label", l)}>{l}</button>
            ))}
          </div>
        </Field>
        <Field label="Тип результата">
          <div className="segmented">
            {(["photo", "video"] as const).map((k) => (
              <button key={k} className={d.kind === k ? "on" : ""} onClick={() => { set("kind", k); set("model", k === "photo" ? "image-default" : "video-default"); }}>{k === "photo" ? "Фото" : "Видео"}</button>
            ))}
          </div>
        </Field>
      </Card>

      <Card title="Генерация" hint="Видно только вам">
        <Field label="Модель"><SelectInput value={d.model} onChange={(v) => set("model", v)} options={meta.data.models.map((m) => [m, m])} /></Field>
        <Field label="Промпт" hint="Описание того, что должен нарисовать AI"><TextArea value={d.prompt} onChange={(v) => set("prompt", v)} rows={5} /></Field>
        <div className="styles-box">
          <span className="picker-label">Стили на экране «Параметры»</span>
          {d.styles.length === 0 && <span className="field-hint">Без стилей поле «Стиль» не показывается.</span>}
          {d.styles.map((s, i) => (
            <div key={i} className="style-row">
              <TextInput value={s.title} onChange={(v) => setStyle(i, { title: v })} placeholder="Название, например «Мягкий свет»" />
              <TextInput value={s.prompt} onChange={(v) => setStyle(i, { prompt: v })} placeholder="Добавка к промпту (необязательно)" />
              <button className="icon-plain danger" onClick={() => set("styles", d.styles.filter((_, j) => j !== i))} aria-label="Убрать стиль"><Icon name="trash" size={18} /></button>
            </div>
          ))}
          {d.styles.length < 8 && <button className="btn ghost sm" onClick={() => set("styles", [...d.styles, { title: "", prompt: "" }])}><Icon name="plus" size={16} /> Добавить стиль</button>}
        </div>
      </Card>

      <Card title="Цена и показ">
        <Field label="Цена в токенах"><Stepper value={d.price_credits} onChange={(v) => set("price_credits", v)} /></Field>
        <SwitchRow label="Опубликован" hint="Виден пользователям в каталоге" checked={d.is_published} onChange={(v) => set("is_published", v)} />
        <SwitchRow label="Популярное" hint="Блок «Популярные генерации» на главной" checked={d.is_popular} onChange={(v) => set("is_popular", v)} />
        <SwitchRow label="Новинка / тренд" hint="Блок «Сейчас в тренде» на главной" checked={d.is_trend} onChange={(v) => set("is_trend", v)} />
        <Field label="Порядок" hint="Чем меньше число, тем выше в списке"><Stepper value={d.sort_order} onChange={(v) => set("sort_order", v)} step={10} /></Field>
      </Card>

      {!isNew && <button className="btn ghost block danger-text" onClick={() => setConfirmDel(true)}><Icon name="trash" size={17} /> Удалить шаблон</button>}
      <div className="savebar-gap" />
      <SaveBar dirty={form.dirty || isNew} saving={saving} onSave={save} error={error} label={isNew ? "Создать" : "Сохранить"} />
      {confirmDel && <ConfirmModal title="Удалить шаблон?" text="Если по шаблону уже были заказы, он не удаляется, а скрывается — чтобы сохранились история и возвраты." confirm="Удалить" onConfirm={remove} onClose={() => setConfirmDel(false)} />}
    </>
  );
}
