import { useEffect, useState } from "react";
import { api } from "../api";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import { Coin, Cover, ErrorBox, Loading, PageHeader, Sheet, Toggle, useLoad } from "../ui";
import {
  Card, ConfirmModal, Field, ListRow, MediaPicker, SaveBar, SelectInput, Stepper, SwitchRow, TextArea, TextInput, errText, useDraft,
} from "./kit";

/* ---------- Категории ---------- */
interface CatRow { id: string; title: string; description: string; cover_url: string; sort_order: number; is_published: number; templates_count: number }

export function CategoriesList() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<CatRow[]>("categories"), []);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  async function toggle(c: CatRow, v: boolean) {
    try { await api.admin.send("PUT", `categories/${c.id}`, { is_published: v }); q.reload(); }
    catch (e) { showToast(errText(e, "Не удалось изменить")); }
  }
  return (
    <>
      <PageHeader title="Категории" onBack={nav.back} />
      <p className="muted small">Так категории выглядят в каталоге. Порядок задаётся числом в редакторе.</p>
      <ul className="list">
        {q.data.map((c) => (
          <ListRow key={c.id} thumb={c.cover_url} title={c.title} sub={`образов: ${c.templates_count}`}
            right={<Toggle checked={!!c.is_published} onChange={(v) => toggle(c, v)} label="Показывать" />}
            onClick={() => nav.go({ name: "admin", page: "category", id: c.id })} />
        ))}
      </ul>
      <div className="fab-bar"><button className="btn gold block" onClick={() => nav.go({ name: "admin", page: "category", id: "new" })}><Icon name="plus" size={18} /> Добавить категорию</button></div>
    </>
  );
}

interface CatForm { title: string; description: string; cover_url: string; sort_order: number; is_published: boolean }
const EMPTY_CAT: CatForm = { title: "", description: "", cover_url: "", sort_order: 100, is_published: true };

export function CategoryEditor({ id }: { id: string }) {
  const { nav } = useApp();
  const isNew = id === "new";
  const form = useDraft<CatForm>(EMPTY_CAT);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  const { reset } = form;

  useEffect(() => {
    if (isNew) return;
    api.admin.get<CatRow[]>("categories").then((all) => {
      const c = all.find((x) => x.id === id);
      if (c) reset({ title: c.title, description: c.description, cover_url: c.cover_url, sort_order: c.sort_order, is_published: !!c.is_published });
      else setError("Категория не найдена");
    }).catch((e) => setError(errText(e, "Не удалось загрузить"))).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) return <Loading />;
  const d = form.draft;

  async function save() {
    setSaving(true); setError(null);
    try {
      if (isNew) await api.admin.send("POST", "categories", d); else await api.admin.send("PUT", `categories/${id}`, d);
      showToast("Сохранено"); nav.back();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }
  async function remove() {
    try { await api.admin.del(`categories/${id}`); showToast("Категория удалена"); nav.back(); }
    catch (e) { setError(errText(e, "Не удалось удалить")); setConfirmDel(false); }
  }

  return (
    <>
      <PageHeader title={isNew ? "Новая категория" : "Редактирование категории"} onBack={nav.back} />
      <Card title="Обложка" hint="Пример генерации — фото или видео">
        <MediaPicker label="Обложка категории" value={d.cover_url} onChange={(v) => form.set("cover_url", v)} ratio="3 / 4" />
      </Card>
      <Card title="Основное">
        <Field label="Название"><TextInput value={d.title} onChange={(v) => form.set("title", v)} /></Field>
        <Field label="Описание" hint="Показывается на странице категории"><TextArea value={d.description} onChange={(v) => form.set("description", v)} /></Field>
        <Field label="Порядок" hint="Чем меньше число, тем выше"><Stepper value={d.sort_order} onChange={(v) => form.set("sort_order", v)} step={10} /></Field>
        <SwitchRow label="Показывать в каталоге" checked={d.is_published} onChange={(v) => form.set("is_published", v)} />
      </Card>
      {!isNew && <button className="btn ghost block danger-text" onClick={() => setConfirmDel(true)}><Icon name="trash" size={17} /> Удалить категорию</button>}
      <div className="savebar-gap" />
      <SaveBar dirty={form.dirty || isNew} saving={saving} onSave={save} error={error} label={isNew ? "Создать" : "Сохранить"} />
      {confirmDel && <ConfirmModal title="Удалить категорию?" text="Категорию с образами удалить нельзя — сначала перенесите или удалите образы, либо просто скройте категорию." confirm="Удалить" onConfirm={remove} onClose={() => setConfirmDel(false)} />}
    </>
  );
}

/* ---------- Пакеты кредитов ---------- */
interface PackRow { id: string; title: string; credits: number; bonus: number; price_stars: number; old_price_stars: number | null; price_rub: number | null; badge: string; is_active: number; sort_order: number; sales: number }

export function PackagesList() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<PackRow[]>("packages"), []);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;
  async function toggle(p: PackRow, v: boolean) {
    try { await api.admin.send("PUT", `packages/${p.id}`, { is_active: v }); q.reload(); }
    catch (e) { showToast(errText(e, "Не удалось изменить")); }
  }
  return (
    <>
      <PageHeader title="Пакеты токенов" onBack={nav.back} />
      <ul className="list">
        {q.data.map((p) => (
          <ListRow key={p.id} thumb={null} title={`${p.title} · ${p.credits} ток.`}
            sub={`${p.price_stars} ⭐ · продано: ${p.sales}${p.badge ? ` · «${p.badge}»` : ""}`}
            right={<Toggle checked={!!p.is_active} onChange={(v) => toggle(p, v)} label="Активен" />}
            onClick={() => nav.go({ name: "admin", page: "package", id: p.id })} />
        ))}
      </ul>
      <div className="fab-bar"><button className="btn gold block" onClick={() => nav.go({ name: "admin", page: "package", id: "new" })}><Icon name="plus" size={18} /> Добавить пакет</button></div>
    </>
  );
}

interface PackForm { title: string; credits: number; bonus: number; price_stars: number; old_price_stars: string; price_rub: string; badge: string; sort_order: number; is_active: boolean }

export function PackageEditor({ id }: { id: string }) {
  const { nav } = useApp();
  const isNew = id === "new";
  const form = useDraft<PackForm>({ title: "", credits: 100, bonus: 0, price_stars: 50, old_price_stars: "", price_rub: "", badge: "", sort_order: 100, is_active: true });
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  const { reset } = form;

  useEffect(() => {
    if (isNew) return;
    api.admin.get<PackRow[]>("packages").then((all) => {
      const p = all.find((x) => x.id === id);
      if (p) reset({ title: p.title, credits: p.credits, bonus: p.bonus, price_stars: p.price_stars, old_price_stars: p.old_price_stars ? String(p.old_price_stars) : "", price_rub: p.price_rub ? String(p.price_rub) : "", badge: p.badge, sort_order: p.sort_order, is_active: !!p.is_active });
    }).catch((e) => setError(errText(e, "Не удалось загрузить"))).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) return <Loading />;
  const d = form.draft;

  async function save() {
    setSaving(true); setError(null);
    try {
      if (isNew) await api.admin.send("POST", "packages", d); else await api.admin.send("PUT", `packages/${id}`, d);
      showToast("Сохранено"); nav.back();
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
    finally { setSaving(false); }
  }
  async function remove() {
    try {
      const r = await api.admin.del<{ deleted: boolean; hidden: boolean }>(`packages/${id}`);
      showToast(r.deleted ? "Пакет удалён" : "По пакету были покупки — он отключён, история сохранена");
      nav.back();
    } catch (e) { setError(errText(e, "Не удалось удалить")); setConfirmDel(false); }
  }

  return (
    <>
      <PageHeader title={isNew ? "Новый пакет" : "Редактирование пакета"} onBack={nav.back} />
      <div className="pack preview-pack">
        {d.badge && <span className="pack-badge">{d.badge}</span>}
        <Coin size={22} /><b className="pack-num">{d.credits}</b><span className="muted small">токенов</span><span className="pack-price">{d.price_stars} ⭐</span>
        <span className="muted small">так выглядит карточка</span>
      </div>
      <Card title="Пакет">
        <Field label="Название"><TextInput value={d.title} onChange={(v) => form.set("title", v)} /></Field>
        <Field label="Токенов в пакете"><Stepper value={d.credits} onChange={(v) => form.set("credits", v)} min={1} step={10} /></Field>
        <Field label="Бонус, токенов" hint="Начисляется сверх пакета и учитывается отдельно"><Stepper value={d.bonus} onChange={(v) => form.set("bonus", v)} step={10} /></Field>
        <Field label="Цена в Telegram Stars"><Stepper value={d.price_stars} onChange={(v) => form.set("price_stars", v)} min={1} step={5} /></Field>
        <Field label="Старая цена в Stars (зачёркнутая)" hint="Необязательно"><TextInput value={d.old_price_stars} onChange={(v) => form.set("old_price_stars", v.replace(/\D/g, ""))} /></Field>
        <Field label="Цена в рублях" hint="Понадобится, когда будут подключены СБП и карты"><TextInput value={d.price_rub} onChange={(v) => form.set("price_rub", v.replace(/\D/g, ""))} /></Field>
        <Field label="Плашка">
          <SelectInput value={["", "Популярный", "Лучший выбор", "Выгодно"].includes(d.badge) ? d.badge : "custom"} onChange={(v) => form.set("badge", v === "custom" ? d.badge : v)}
            options={[["", "Без плашки"], ["Популярный", "Популярный"], ["Лучший выбор", "Лучший выбор"], ["Выгодно", "Выгодно"], ["custom", "Свой текст…"]]} />
        </Field>
        <Field label="Текст плашки"><TextInput value={d.badge} onChange={(v) => form.set("badge", v)} placeholder="Необязательно" /></Field>
        <Field label="Порядок"><Stepper value={d.sort_order} onChange={(v) => form.set("sort_order", v)} step={10} /></Field>
        <SwitchRow label="Продаётся" hint="Выключите, чтобы скрыть пакет" checked={d.is_active} onChange={(v) => form.set("is_active", v)} />
      </Card>
      {!isNew && <button className="btn ghost block danger-text" onClick={() => setConfirmDel(true)}><Icon name="trash" size={17} /> Удалить пакет</button>}
      <div className="savebar-gap" />
      <SaveBar dirty={form.dirty || isNew} saving={saving} onSave={save} error={error} label={isNew ? "Создать" : "Сохранить"} />
      {confirmDel && <ConfirmModal title="Удалить пакет?" text="Если по пакету были покупки, он будет отключён, а история платежей сохранится." confirm="Удалить" onConfirm={remove} onClose={() => setConfirmDel(false)} />}
    </>
  );
}

/* ---------- Витрина ---------- */
interface ShowRow { id?: number; title: string; prompt?: string; media_url: string; media_kind?: string; template_id: number | null; sort_order: number; is_published: number | boolean }

export function ShowcaseAdmin() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<ShowRow[]>("showcase"), []);
  const tpls = useLoad(() => api.admin.get<{ items: { id: number; title: string }[] }>("templates"), []);
  const [edit, setEdit] = useState<ShowRow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDel, setConfirmDel] = useState(false);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Ошибка"} onRetry={q.reload} />;

  async function save() {
    if (!edit) return;
    setError(null);
    try {
      if (edit.id) await api.admin.send("PUT", `showcase/${edit.id}`, edit); else await api.admin.send("POST", "showcase", edit);
      setEdit(null); q.reload(); showToast("Сохранено");
    } catch (e) { setError(errText(e, "Не удалось сохранить")); }
  }
  async function remove() {
    if (!edit?.id) return;
    await api.admin.del(`showcase/${edit.id}`);
    setEdit(null); setConfirmDel(false); q.reload(); showToast("Убрано с витрины");
  }
  const blank: ShowRow = { title: "", prompt: "", media_url: "", template_id: null, sort_order: 100, is_published: true };

  return (
    <>
      <PageHeader title="Популярные работы" onBack={nav.back} />
      <p className="muted small">«Популярные работы» на главной: ваши лучшие фото и короткие видео. Нажмите на работу, чтобы изменить.</p>
      <div className="show-grid">
        {q.data.map((s) => (
          <button key={s.id} className={`show-item ${s.is_published ? "" : "off"}`} onClick={() => { setEdit({ ...s }); setError(null); }}>
            <Cover url={s.media_url} seed={s.id} />
            {s.media_kind === "video" && <span className="play-dot"><Icon name="play" size={14} /></span>}
            {!s.is_published && <span className="badge">Скрыто</span>}
            {s.title && <span className="cat-title">{s.title}</span>}
          </button>
        ))}
        <button className="show-add" onClick={() => { setEdit({ ...blank }); setError(null); }}><Icon name="plus" size={26} /><span>Добавить</span></button>
      </div>
      {edit && (
        <Sheet title={edit.id ? "Работа на витрине" : "Новая работа"} onClose={() => setEdit(null)}>
          <div className="sheet-body">
            <MediaPicker label="Ваше фото или видео" value={edit.media_url} onChange={(v) => setEdit({ ...edit, media_url: v })} ratio="4 / 5" />
            <Field label="Подпись (необязательно)"><TextInput value={edit.title} onChange={(v) => setEdit({ ...edit, title: v })} /></Field>
            <Field label="Описание для «Создать похожее»" hint="Подставится в генератор, когда пользователь нажмёт «Создать похожее»">
              <TextArea value={edit.prompt ?? ""} onChange={(v) => setEdit({ ...edit, prompt: v })} rows={3} />
            </Field>
            <Field label="Связанный стиль (необязательно)">
              <SelectInput value={String(edit.template_id ?? "")} onChange={(v) => setEdit({ ...edit, template_id: v ? Number(v) : null })}
                options={[["", "— ничего не открывать —"], ...(tpls.data?.items ?? []).map((t): [string, string] => [String(t.id), t.title])]} />
            </Field>
            <Field label="Порядок"><Stepper value={edit.sort_order} onChange={(v) => setEdit({ ...edit, sort_order: v })} step={10} /></Field>
            <SwitchRow label="Показывать на главной" checked={!!edit.is_published} onChange={(v) => setEdit({ ...edit, is_published: v })} />
            {error && <ErrorBox message={error} />}
            <button className="btn gold block" onClick={save}>Сохранить</button>
            {edit.id && <button className="btn ghost block danger-text" onClick={() => setConfirmDel(true)}>Убрать с витрины</button>}
          </div>
        </Sheet>
      )}
      {confirmDel && <ConfirmModal title="Убрать с витрины?" text="Работа исчезнет с главной. Файл останется на сервере." confirm="Убрать" onConfirm={remove} onClose={() => setConfirmDel(false)} />}
    </>
  );
}
