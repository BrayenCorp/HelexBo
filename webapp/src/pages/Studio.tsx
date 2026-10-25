import { useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { tokensText } from "../format";
import { Icon } from "../icons";
import { Back, Dropdown, Empty2, Hdr, uuid } from "../pf";
import type { Opt } from "../pf";
import type { AiModel, AvatarRow, CatalogItem, GenParams, Kind, Quote, Route } from "../types";
import { Loading, useDebounced, useLoad } from "../ui";

const DEFAULT_SLUG: Record<string, string> = { photo: "nano-banana-2", video: "seedance-2-0", audio: "eleven" };
const RATIOS = ["1:1", "3:4", "4:3", "9:16", "16:9", "21:9"];
const RES_IMG = ["1k", "2k", "4k"];
const RES_VID = ["480p", "720p", "1080p"];
const DURS = ["5", "8", "10", "15"];
const STYLES: [string, string][] = [["", "Авто"], ["realistic", "Реалистичный"], ["cinematic", "Киноплёнка"], ["luxury", "Люкс"], ["studio", "Студийный"], ["street", "Уличный"], ["portrait", "Портрет"], ["anime", "Аниме"]];

type CreateRoute = Extract<Route, { name: "create" }>;

/** Файл с превью и кнопкой выбора. */
function Upload({ label, hint, file, onFile, icon = "upload", big = false }: { label: string; hint?: string; file: File | null; onFile: (f: File | null) => void; icon?: "upload" | "image"; big?: boolean }) {
  const ref = useRef<HTMLInputElement>(null);
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) { setUrl(null); return; }
    const u = URL.createObjectURL(file);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [file]);
  return (
    <div>
      <input ref={ref} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={(e) => { onFile(e.target.files?.[0] ?? null); e.target.value = ""; }} />
      <button type="button" className={`upl ${big ? "big" : ""}`} onClick={() => ref.current?.click()}>
        {url ? <img src={url} alt="" /> : <span className="upl-ic"><Icon name={icon} size={20} /></span>}
        <span className="grow"><b>{file ? file.name : label}</b><span>{file ? "Нажмите, чтобы заменить" : hint ?? "JPG, PNG или WebP"}</span></span>
        {file && <span role="button" aria-label="Убрать" onClick={(e) => { e.stopPropagation(); onFile(null); }}><Icon name="close" size={18} /></span>}
      </button>
    </div>
  );
}

function Pills<T extends string>({ value, options, onChange }: { value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return <div className="pill-row">{options.map(([v, l]) => <button key={v} type="button" className={`pill ${v === value ? "on" : ""}`} onClick={() => onChange(v)}>{l}</button>)}</div>;
}

function materials(item: CatalogItem | null) {
  const codes = (item?.required ?? []).map((r) => r.code);
  const has = (c: string) => codes.includes(c);
  const tryon = has("person") && has("garment");
  return {
    tryon,
    idea: has("idea"),
    slotA: has("person") ? "Фото человека" : has("product") ? "Фото товара" : has("garment") ? "Фото одежды" : has("photo") ? "Фото" : "",
    slotB: tryon ? "Фото одежды" : "",
    anyImage: has("person") || has("product") || has("garment") || has("photo"),
  };
}

export function Studio({ init }: { init: CreateRoute }) {
  const { me, nav, refreshMe, ensureRegistered } = useApp();
  const slug = init.slug;
  const itemQ = useLoad(async () => {
    if (slug) return api.catalogSlug(slug);
    if (init.templateId) return api.catalogItem(init.templateId);
    return null;
  }, [slug, init.templateId]);
  const item: CatalogItem | null = itemQ.data;
  const [tabKind, setTabKind] = useState<Kind>(init.kind ?? "photo");
  const activeKind: Kind = item ? item.kind : tabKind;
  const free = !item;
  const mat = useMemo(() => materials(item), [item]);

  const modelsQ = useLoad(() => api.models(activeKind), [activeKind]);
  const [modelId, setModelId] = useState<number | undefined>(init.modelId);
  const models: AiModel[] = modelsQ.data ?? [];
  const model = models.find((m) => m.id === modelId) ?? (activeKind === "photo" ? models.find((m) => m.id === me.prefs.default_model_id) : undefined) ?? models.find((m) => m.slug === DEFAULT_SLUG[activeKind]) ?? models[0];

  const [prompt, setPrompt] = useState(init.prompt ?? "");
  const [params, setParams] = useState<GenParams>({ format: me.prefs.ratio, quality: me.prefs.quality, ...(init.params ?? {}) });
  const [count, setCount] = useState(1);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photo2, setPhoto2] = useState<File | null>(null);
  const [refOrderId, setRefOrderId] = useState<number | undefined>(init.refOrderId);
  const [avatarId, setAvatarId] = useState<number | undefined>(init.avatarId);
  const [advanced, setAdvanced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(uuid());

  const avatarsQ = useLoad(async () => (item?.needs_avatar ? api.avatars() : []), [item?.needs_avatar]);
  const readyAvatars: AvatarRow[] = (avatarsQ.data ?? []).filter((a) => a.status === "ready");
  useEffect(() => { if (item?.needs_avatar && !avatarId && readyAvatars[0]) setAvatarId(readyAvatars[0].id); }, [item?.needs_avatar, readyAvatars, avatarId]);

  const modelOptions: Opt[] = models.map((m) => ({ id: String(m.id), label: m.name, note: m.description.slice(0, 64), right: `${m.price_credits}` }));

  const set = (patch: Partial<GenParams>) => setParams((p) => ({ ...p, ...patch }));
  const hasImg = !!photo || !!refOrderId;
  const audio = activeKind === "audio";
  const videoK = activeKind === "video";

  // Стоимость считает сервер: бесплатная первая попытка, цена модели, число вариантов.
  const qKey = useDebounced(`${activeKind}|${item?.id ?? ""}|${model?.id ?? ""}|${count}`, 200);
  const quoteQ = useLoad<Quote | null>(async () => {
    if (itemQ.loading) return null;
    try { return await api.quote({ kind: item ? undefined : activeKind, templateId: item?.id, modelId: free ? model?.id : undefined, count: free ? count : 1 }); }
    catch { return null; }
  }, [qKey, itemQ.loading]);
  const quote = quoteQ.data;

  function ready(): string | null {
    if (item) {
      if (item.needs_avatar && !avatarId) return "Сначала создайте аватар";
      if (mat.tryon) return photo && photo2 ? null : "Загрузите фото человека и одежды";
      if (mat.anyImage && !mat.idea && !hasImg) return `Загрузите: ${mat.slotA.toLowerCase()}`;
      if (mat.anyImage && mat.idea && !hasImg && !prompt.trim()) return "Загрузите фото или опишите идею";
      if (!mat.anyImage && mat.idea && !prompt.trim() && !hasImg) return "Опишите идею";
      return null;
    }
    if (!prompt.trim() && !(hasImg && !audio)) return audio ? "Введите текст для озвучки" : "Опишите, что хотите создать";
    if (model?.needs_image && !hasImg) return "Для этой модели загрузите исходное изображение";
    return null;
  }
  const blocker = ready();

  async function submit() {
    if (blocker) { setError(blocker); return; }
    if (!(await ensureRegistered())) return;
    setBusy(true); setError(null);
    try {
      const p: GenParams = { ...params };
      if (audio) { delete p.format; delete p.quality; delete p.resolution; }
      if (!videoK) delete p.duration;
      if (!free) { delete p.format; delete p.quality; }
      if (videoK && p.format === "21:9") p.format = "16:9";
      const r = await api.createOrder({
        requestId: requestId.current, templateId: item?.id, kind: free ? activeKind : undefined, prompt: prompt.trim() || undefined,
        params: p, modelId: free ? model?.id : undefined, count: free && !audio ? count : 1,
        photo: audio ? null : photo, photo2: audio ? null : photo2, avatarId, refOrderId: photo ? undefined : refOrderId,
      });
      refreshMe();
      requestId.current = uuid();
      if (r.orders.length > 1) showToast(`Создаём ${r.orders.length} варианта — они появятся в истории`);
      nav.go({ name: "order", id: r.order.id });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось начать создание. Проверьте соединение.");
    } finally { setBusy(false); }
  }

  if (itemQ.loading) return <Loading />;
  if (itemQ.error) return <Empty2 title="Не удалось открыть" text={itemQ.error} action={<button className="btn outline" onClick={nav.back}>Назад</button>} />;

  const total = quote ? (quote.free ? 0 : quote.total) : null;
  const title = item ? item.title : "Создать";
  const lead = item ? item.description : "Опишите идею и выберите модель. Первый результат каждого типа — бесплатно.";
  const needMore = quote && !quote.enough;

  return (
    <>
      {item && <Back onClick={nav.back} />}
      <Hdr title={title} text={lead} />
      {me.modes.ai === "mock" && <div className="demo-note"><Icon name="info" size={18} /><span>Демо-режим: результат создаётся локально и помечается как демонстрационный.</span></div>}
      <div className="editor">
        <div className="panel">
          {free && (
            <div className="pf-seg wide2" role="tablist">
              {([["photo", "Фото", "image"], ["video", "Видео", "video"]] as const).map(([k, l, ic]) => (
                <button key={k} role="tab" className={tabKind === k ? "on" : ""} onClick={() => { setTabKind(k); setModelId(undefined); setCount(1); setError(null); }}><Icon name={ic} size={16} /><span>{l}</span></button>
              ))}
            </div>
          )}

          {item?.needs_avatar && (
            <div className="fld">
              <span className="lbl">Аватар</span>
              {avatarsQ.loading ? <span className="hint">Загружаем…</span> : readyAvatars.length === 0 ? (
                <div className="notice"><p>Готовых аватаров пока нет.</p><button className="btn orange sm" onClick={() => nav.go({ name: "avatars" })}>Создать аватар</button></div>
              ) : <Pills value={String(avatarId ?? "")} options={readyAvatars.map((a) => [String(a.id), a.name] as [string, string])} onChange={(v) => setAvatarId(Number(v))} />}
            </div>
          )}

          {!audio && mat.tryon && (
            <>
              <Upload label="Фото человека" file={photo} onFile={setPhoto} />
              <Upload label="Фото одежды" file={photo2} onFile={setPhoto2} icon="image" />
              <span className="hint">Фото людей используйте только с их согласия.</span>
            </>
          )}
          {!audio && !mat.tryon && (free || mat.anyImage) && (
            <Upload label={free ? "Загрузить изображение" : mat.slotA} hint={free ? (model?.needs_image ? "Для этой модели исходное изображение обязательно" : "По желанию — для редактирования или анимации") : mat.idea ? "Или опишите идею ниже" : "JPG, PNG или WebP"} file={photo} onFile={(f) => { setPhoto(f); if (f) setRefOrderId(undefined); }} />
          )}
          {!audio && free && <Upload label="Добавить референс" hint="Картинка, на которую нужно ориентироваться" file={photo2} onFile={setPhoto2} icon="image" />}
          {refOrderId && !photo && (
            <div className="notice"><p>Исходное изображение — ваша прошлая работа № {refOrderId}.</p><button className="btn ghost sm" onClick={() => setRefOrderId(undefined)}>Убрать</button></div>
          )}

          {audio ? (
            <>
              <div className="fld"><label htmlFor="at">Текст</label><textarea id="at" maxLength={2000} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Что должен сказать голос?" /><span className="hint">{prompt.length} / 2000</span></div>
              <div className="fld"><span className="lbl">Голос</span>
                <Pills value={params.voice ?? "alina"} options={[["alina", "Алина"], ["maxim", "Максим"], ["olga", "Ольга"], ["igor", "Игорь"], ["sofia", "Софья"]]} onChange={(v) => set({ voice: v })} /></div>
              <div className="fld-row">
                <div className="fld"><span className="lbl">Эмоция</span>
                  <Dropdown ariaLabel="Эмоция" value={params.emotion ?? "neutral"} onChange={(v) => set({ emotion: v })}
                    options={[["neutral", "Нейтрально"], ["joy", "Радостно"], ["calm", "Спокойно"], ["solemn", "Торжественно"], ["sad", "Грустно"], ["inspire", "Вдохновляюще"]].map(([id, label]) => ({ id, label }))} /></div>
                <div className="fld"><span className="lbl">Интонация</span>
                  <Dropdown ariaLabel="Интонация" value={params.tone ?? "even"} onChange={(v) => set({ tone: v })}
                    options={[["even", "Ровная"], ["question", "Вопросительная"], ["exclaim", "Восклицательная"], ["confidential", "Доверительная"], ["ad", "Рекламная"]].map(([id, label]) => ({ id, label }))} /></div>
              </div>
              <div className="fld"><label htmlFor="sp">Скорость: {(params.speed ?? 1).toLocaleString("ru-RU")}×</label>
                <input id="sp" type="range" min={0.5} max={2} step={0.1} value={params.speed ?? 1} onChange={(e) => set({ speed: Number(e.target.value) })} /></div>
            </>
          ) : (
            <div className="fld">
              <label htmlFor="pr">{free ? "Описание" : mat.idea ? "Описание идеи" : "Пожелания (по желанию)"}</label>
              <textarea id="pr" maxLength={500} value={prompt} onChange={(e) => setPrompt(e.target.value)}
                placeholder={free ? "Опишите, что хотите создать..." : "Например: утренний свет, спокойное настроение"} />
              <span className="hint">{prompt.length} / 500</span>
            </div>
          )}

          {free && (
            <div className="fld">
              <span className="lbl">Модель</span>
              <Dropdown ariaLabel="Выбрать модель" placeholder={modelsQ.loading ? "Загружаем…" : "Выберите модель"}
                value={model ? String(model.id) : ""} options={modelOptions} onChange={(v) => setModelId(Number(v))} />
              {model?.needs_image && <span className="hint">Этой модели нужно исходное изображение.</span>}
              {model?.text_only && <span className="hint">Эта модель работает только по тексту.</span>}
            </div>
          )}

          {free && !audio && (
            <>
              <div className="fld"><span className="lbl">Соотношение сторон</span>
                <Pills value={params.format ?? "1:1"} options={RATIOS.filter((r) => !(videoK && r === "21:9")).map((r) => [r, r] as [string, string])} onChange={(v) => set({ format: v })} /></div>
              <div className="adv">
                <button type="button" onClick={() => setAdvanced(!advanced)}>Все параметры<Icon name="chevron-down" size={18} /></button>
                {advanced && (
                  <div>
                    <div className="fld"><span className="lbl">Разрешение</span>
                <Pills value={params.resolution ?? ""} options={[["", "Авто"], ...(videoK ? RES_VID : RES_IMG).map((r) => [r, r.toUpperCase()] as [string, string])]} onChange={(v) => set({ resolution: v || undefined })} /></div>
                    {videoK && <div className="fld"><span className="lbl">Длительность</span>
                <Pills value={params.duration ?? ""} options={[["", "Авто"], ...DURS.map((d) => [d, `${d} с`] as [string, string])]} onChange={(v) => set({ duration: v || undefined })} /></div>}
                    {!videoK && (
                            <div className="fld"><span className="lbl">Количество результатов</span>
                  <Pills value={String(count)} options={Array.from({ length: Math.min(me.max_variants, 4) }, (_, i) => [String(i + 1), String(i + 1)] as [string, string])} onChange={(v) => setCount(Number(v))} /></div>
                    )}
                    <div className="fld"><span className="lbl">Качество</span>
                <Pills value={params.quality ?? "standard"} options={[["standard", "Стандарт"], ["high", "Высокое"]]} onChange={(v) => set({ quality: v })} /></div>
                    <div className="fld"><span className="lbl">Стиль</span>
                <Pills value={params.style ?? ""} options={STYLES} onChange={(v) => set({ style: v || undefined })} /></div>
                    <div className="fld"><label htmlFor="sd">Случайное зерно</label>
                      <input id="sd" inputMode="numeric" placeholder="Пусто — случайное" value={params.seed ?? ""} onChange={(e) => set({ seed: e.target.value === "" ? undefined : Math.max(0, Math.min(2147483647, Number(e.target.value.replace(/\D/g, "")))) })} /></div>
                    <div className="fld"><label htmlFor="ng">Чего не должно быть</label>
                      <input id="ng" maxLength={200} placeholder="Например: текст, размытие" value={params.negative ?? ""} onChange={(e) => set({ negative: e.target.value || undefined })} /></div>
                  </div>
                )}
              </div>
            </>
          )}
          {free && audio && (
            <div className="fld"><span className="lbl">Длительность</span><span className="hint">Определяется длиной текста.</span></div>
          )}
        </div>

        <div className="panel stick">
          <div className="cost-line">
            {quote ? (quote.free ? <>Стоимость: <b>бесплатно</b> — первая попытка этого типа</> : <>Стоимость: <b>{tokensText(quote.total)}</b></>) : "Считаем стоимость…"}
            {quote && <> · ваш баланс {tokensText(quote.balance)}</>}
          </div>
          {needMore && <div className="notice bad"><p>Не хватает токенов{total !== null ? `: нужно ${tokensText(total)}` : ""}.</p><button className="btn orange sm" onClick={() => nav.go({ name: "balance" })}>Пополнить баланс</button></div>}
          {error && <div className="notice bad" role="alert"><p>{error}</p></div>}
          {me.status === "blocked" && <div className="notice bad"><p>Аккаунт заблокирован: создание недоступно.</p></div>}
          <button className="btn orange big block" disabled={busy || !!needMore || me.status === "blocked"} onClick={submit}>
            {busy ? "Отправляем…" : audio ? "Создать аудио" : "Создать"}
          </button>
          {blocker && !error && <span className="hint">{blocker}</span>}
          <span className="hint">Если генерация не удастся, токены вернутся автоматически.</span>
        </div>
      </div>
    </>
  );
}
