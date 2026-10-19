import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import { haptic } from "../telegram";
import type { GenParams, GenerateOpts, Kind, TemplateDetail } from "../types";
import { tokensText } from "../format";
import { Coin, Cover, ErrorBox, Mark, Segmented, useLoad } from "../ui";

const MAX_MB = 10;
const MAX_PROMPT = 500;

const QUICK: [string, string][] = [
  ["Реалистичный", "реалистичный"], ["Кинематографичный", "кинематографичный"], ["Премиальный", "премиальный"],
  ["Студийный", "студийный"], ["Уличный", "уличный"], ["Аниме", "аниме"], ["Портрет", "портрет"],
];
const FORMATS = ["1:1", "3:4", "4:3", "9:16", "16:9"];
const SELECTS: { key: keyof GenParams; label: string; options: [string, string][] }[] = [
  { key: "style", label: "Стиль", options: [["realistic", "Реалистичный"], ["cinematic", "Кинематографичный"], ["luxury", "Премиальный"], ["studio", "Студийный"], ["street", "Уличный"], ["anime", "Аниме"], ["portrait", "Портретный"]] },
  { key: "lighting", label: "Освещение", options: [["natural", "Естественное"], ["studio", "Студийное"], ["soft", "Мягкое"], ["contrast", "Контрастное"], ["sunset", "Закат"]] },
  { key: "camera", label: "Камера", options: [["portrait", "Портретный объектив"], ["wide", "Широкий угол"], ["closeup", "Крупный план"], ["topdown", "Вид сверху"]] },
];

function toggleWord(prompt: string, word: string): string {
  const re = new RegExp(`(^|,\\s*)${word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?=,|$)`, "i");
  if (re.test(prompt)) return prompt.replace(re, "").replace(/^,\s*/, "").trim();
  const next = prompt.trim() ? `${prompt.trim().replace(/,$/, "")}, ${word}` : word;
  return next.slice(0, MAX_PROMPT);
}

export function Generate(opts: GenerateOpts) {
  const { me, nav, refreshMe, ensureRegistered } = useApp();
  const [kind, setKind] = useState<Kind>(opts.kind);
  const [modelId, setModelId] = useState<number | undefined>(opts.modelId);
  const [count, setCount] = useState(1);
  const [tpl, setTpl] = useState<TemplateDetail | null>(null);
  const [tplId, setTplId] = useState<number | undefined>(opts.templateId);
  const [prompt, setPrompt] = useState(opts.prompt ?? "");
  const [params, setParams] = useState<GenParams>(opts.params ?? {});
  const [variant, setVariant] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [adv, setAdv] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef<string>(crypto.randomUUID());
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const models = useLoad(() => api.models(kind), [kind]);
  const modelList = models.data ?? [];
  const model = modelList.find((m) => m.id === modelId) ?? (tplId ? undefined : modelList[0]);

  useEffect(() => {
    if (!tplId) { setTpl(null); return; }
    api.template(tplId).then(setTpl).catch(() => { setTplId(undefined); setTpl(null); });
  }, [tplId]);

  useEffect(() => { if (opts.edit) promptRef.current?.focus(); }, [opts.edit]);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Любое изменение запроса — новый идентификатор. Повторное нажатие на тот же запрос остаётся идемпотентным.
  useEffect(() => { requestId.current = crypto.randomUUID(); }, [kind, tplId, prompt, params, variant, file, modelId, count]);

  function chooseKind(k: Kind) {
    setKind(k);
    setModelId(undefined);
    if (tpl && tpl.kind !== k) { setTplId(undefined); setTpl(null); }
  }
  function pick(f: File | undefined | null) {
    setError(null);
    if (!f) return;
    if (!f.type.startsWith("image/")) return setError("Выберите изображение (JPEG, PNG или WEBP).");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Файл больше ${MAX_MB} МБ — выберите фото поменьше.`);
    setFile(f);
  }
  const setParam = (key: keyof GenParams, value: string) =>
    setParams((p) => { const n = { ...p }; if (value) n[key] = value; else delete n[key]; return n; });

  const ff = me.freeform[kind];
  const enabled = tplId ? true : ff?.enabled !== false;
  const free = me.free[kind];
  const basePrice = tplId ? tpl?.price_credits ?? 0 : model?.price_credits ?? ff?.price ?? 0;
  const price = (free ? 0 : basePrice) + basePrice * (count - 1);
  const enough = me.balance >= price;
  const hasInput = Boolean(prompt.trim() || file || tplId);

  async function submit() {
    if (!hasInput || busy) return;
    if (!me.registered && !(await ensureRegistered())) return;
    setBusy(true); setError(null);
    try {
      const res = await api.createOrder({
        requestId: requestId.current, templateId: tplId, kind, prompt: prompt.trim(), params,
        style: variant || tpl?.styles[0]?.id, photo: file, modelId: tplId ? undefined : model?.id, count,
      });
      refreshMe();
      if (res.orders && res.orders.length > 1) { showToast(`Создаём ${res.orders.length} варианта — следите в истории`); nav.replace({ name: "history" }); }
      else nav.replace({ name: "order", id: res.order.id });
    } catch (e) {
      haptic("error");
      setError(e instanceof ApiError ? e.message : "Не удалось отправить запрос. Проверьте соединение и повторите.");
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <button className="back-btn" onClick={nav.back} aria-label="Назад"><Icon name="back" size={20} /><span>Назад</span></button>
        <h1 className="page-title">{kind === "photo" ? "Создание изображения" : "Создание видео"}</h1>
        <span className="page-head-right" />
      </div>

      <Segmented value={kind} onChange={chooseKind} options={[["photo", "Фото", "diamond"], ["video", "Видео", "video"]]} />

      {tplId && (
        <div className="style-chip">
          <span className="style-thumb"><Cover url={tpl?.preview_url} seed={tplId} /></span>
          <span className="row-main"><span className="muted small">Стиль</span><b>{tpl?.title ?? "…"}</b></span>
          <button className="icon-plain" onClick={() => { setTplId(undefined); setTpl(null); }} aria-label="Убрать стиль"><Icon name="close" size={18} /></button>
        </div>
      )}

      <h2 className="step"><Icon name="image" size={16} /><span>1. Загрузите изображение <span className="muted">(необязательно)</span></span></h2>
      {!preview ? (
        <label className="drop" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer?.files?.[0]); }}>
          <input type="file" accept="image/*" hidden onChange={(e) => pick(e.target.files?.[0])} />
          <Icon name="upload" size={26} />
          <span>Перетащите фото сюда<br />или выберите из галереи</span>
          <span className="btn outline sm">Выбрать фото</span>
        </label>
      ) : (
        <div className="photo-card">
          <div className="photo-frame"><img src={preview} alt="Выбранное фото" />
            <button className="photo-x" onClick={() => setFile(null)} aria-label="Убрать фото"><Icon name="close" size={14} /></button></div>
          <label className="link-btn"><Icon name="refresh" size={16} /> Заменить фото
            <input type="file" accept="image/*" hidden onChange={(e) => pick(e.target.files?.[0])} /></label>
        </div>
      )}
      {tplId && !preview && <p className="muted small">С вашим фото результат будет больше похож на вас.</p>}

      <h2 className="step"><Icon name="edit" size={16} /><span>2. Опишите, что хотите получить</span></h2>
      <div className="textbox">
        <textarea ref={promptRef} rows={4} maxLength={MAX_PROMPT} value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder="Например: девушка в студии, мягкий свет, реалистично..." />
        <span className="counter">{prompt.length}/{MAX_PROMPT}</span>
      </div>

      {!tplId && modelList.length > 0 && (
        <>
          <h2 className="step"><Icon name="wand" size={16} /><span>3. Выберите модель</span></h2>
          <div className="model-pick">
            {modelList.map((m) => (
              <button key={m.id} className={`model-opt ${model?.id === m.id ? "on" : ""}`} onClick={() => setModelId(m.id)}>
                <span className="row-main"><b>{m.name}</b><span className="muted small">{m.purpose || m.description}</span></span>
                <span className="price-row"><Coin size={14} /><b>{m.price_credits}</b></span>
              </button>
            ))}
          </div>
        </>
      )}

      <span className="muted small">Быстрые подсказки</span>
      <div className="wrap-chips">
        {QUICK.map(([label, word]) => (
          <button key={label} className={`chip ${new RegExp(`(^|,\\s*)${word}(?=,|$)`, "i").test(prompt) ? "on" : ""}`} onClick={() => setPrompt(toggleWord(prompt, word))}>{label}</button>
        ))}
      </div>

      <button className={`adv-toggle ${adv ? "open" : ""}`} onClick={() => setAdv(!adv)} aria-expanded={adv}>
        <Icon name="sliders" size={18} /><span>Дополнительные параметры</span><Icon name="chevron-down" size={18} />
      </button>
      {adv && (
        <div className="adv">
          <div className="field"><span>Формат</span>
            <div className="wrap-chips">
              <button className={`chip ${!params.format ? "on" : ""}`} onClick={() => setParam("format", "")}>Авто</button>
              {FORMATS.map((f) => <button key={f} className={`chip ${params.format === f ? "on" : ""}`} onClick={() => setParam("format", f)}>{f}</button>)}
            </div>
          </div>
          <div className="field"><span>Качество</span>
            <div className="segmented small">
              {([["", "Авто"], ["standard", "Стандарт"], ["high", "Высокое"]] as [string, string][]).map(([v, l]) => (
                <button key={v} className={(params.quality ?? "") === v ? "on" : ""} onClick={() => setParam("quality", v)}>{l}</button>
              ))}
            </div>
          </div>
          {SELECTS.map((s) => (
            <label key={s.key} className="field"><span>{s.label}</span>
              <span className="select"><select value={params[s.key] ?? ""} onChange={(e) => setParam(s.key, e.target.value)}>
                <option value="">Авто</option>
                {s.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select></span>
            </label>
          ))}
          {tpl && tpl.styles.length > 0 && (
            <label className="field"><span>Вариант стиля «{tpl.title}»</span>
              <span className="select"><select value={variant || tpl.styles[0].id} onChange={(e) => setVariant(e.target.value)}>
                {tpl.styles.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
              </select></span>
            </label>
          )}
        </div>
      )}

      <div className="field"><span>Количество вариантов</span>
        <span className="stepper">
          <button type="button" onClick={() => setCount(Math.max(1, count - 1))} aria-label="Меньше">−</button>
          <input type="number" value={count} readOnly aria-label="Количество вариантов" />
          <button type="button" onClick={() => setCount(Math.min(me.max_variants || 4, count + 1))} aria-label="Больше">+</button>
        </span>
      </div>
      <div className="cost-line">
        <span className="price-row"><Coin size={16} />{price === 0 ? <b>Бесплатно — первая попытка</b> : <b>Стоимость: {tokensText(price)}</b>}</span>
        <span className="muted small">Баланс: {tokensText(me.balance)}</span>
      </div>

      {error && <ErrorBox message={error} />}
      {!enabled && <div className="notice"><p>Свободная генерация сейчас недоступна. Выберите готовый стиль на вкладке «Создать».</p></div>}
      {enabled && !enough && (
        <div className="notice"><p>Недостаточно токенов: нужно {tokensText(price)}, у вас {tokensText(me.balance)}.</p>
          <button className="btn orange sm" onClick={() => nav.go({ name: "shop" })}>Пополнить баланс</button></div>
      )}
      <div className="cta-bar">
        <button className="btn orange block big" disabled={!hasInput || busy || !enough || !enabled} onClick={submit}>
          <Mark size={20} mono /> {busy ? "Отправляем…" : price === 0 ? "Создать" : `Создать за ${tokensText(price)}`}
        </button>
      </div>
      <p className="muted small center">Исходное фото удаляется сразу после создания результата.</p>
    </>
  );
}
