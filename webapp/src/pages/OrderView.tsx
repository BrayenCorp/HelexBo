import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtTime, tokensText } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { Back, KIND_LABEL, Stages, uuid, useOrderPoll } from "../pf";
import { haptic, tg } from "../telegram";
import type { GenParams, Order } from "../types";
import { ErrorBox, Loading, Modal } from "../ui";

const PARAM_LABELS: Record<string, string> = { format: "Соотношение сторон", quality: "Качество", style: "Стиль", resolution: "Разрешение", duration: "Длительность", seed: "Зерно", negative: "Исключить", voice: "Голос", emotion: "Эмоция", tone: "Интонация", speed: "Скорость" };
const VOICES: Record<string, string> = { alina: "Алина", maxim: "Максим", olga: "Ольга", igor: "Игорь", sofia: "Софья" };

function paramRows(p: GenParams): [string, string][] {
  return Object.entries(p).filter(([, v]) => v !== undefined && v !== "" && v !== null).map(([k, v]) => [PARAM_LABELS[k] ?? k, k === "voice" ? VOICES[String(v)] ?? String(v) : k === "duration" ? `${v} с` : k === "speed" ? `${v}×` : String(v)]);
}

function useBlobUrl(load: () => Promise<Blob>, deps: unknown[]) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    let u: string | null = null;
    setUrl(null); setFailed(false);
    load().then((b) => { if (alive) { u = URL.createObjectURL(b); setUrl(u); } }).catch(() => alive && setFailed(true));
    return () => { alive = false; if (u) URL.revokeObjectURL(u); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { url, failed };
}

function ResultMedia({ order }: { order: Order }) {
  const { url, failed } = useBlobUrl(() => api.resultBlob(order.id), [order.id]);
  const mime = order.result_mime ?? "";
  return (
    <div className="result-box">
      {order.is_stub && <span className="demo-flag">Демо</span>}
      {failed ? <div className="result-ph"><Icon name="image" size={30} />Файл недоступен или удалён</div>
        : !url ? <div className="result-ph">Загружаем…</div>
        : mime.startsWith("video/") ? <video src={url} controls autoPlay loop muted playsInline />
        : mime.startsWith("audio/") ? <div style={{ width: "100%" }}><div className="result-ph"><Icon name="audio" size={34} /></div><audio src={url} controls /></div>
        : <img src={url} alt="Результат" />}
    </div>
  );
}

function FrameThumb({ orderId, i, label, onClick, version }: { orderId: number; i: number; label: string; onClick: () => void; version: number }) {
  const { url } = useBlobUrl(() => api.frameBlob(orderId, i), [orderId, i, version]);
  return <button className="frame" onClick={onClick} aria-label={`Перегенерировать кадр: ${label}`}>{url && <img src={url} alt={label} />}<span>{label}</span></button>;
}

export function OrderView({ id }: { id: number }) {
  const { me, nav, refreshMe, toggleFavorite } = useApp();
  const { order: o, error } = useOrderPoll(id);
  const [busy, setBusy] = useState(false);
  const [del, setDel] = useState(false);
  const [regen, setRegen] = useState<number | null>(null);
  const [version, setVersion] = useState(0);
  const [frames, setFrames] = useState<string[] | null>(null);

  useEffect(() => { if (o?.status === "done") { refreshMe(); haptic("success"); } }, [o?.status]); // eslint-disable-line react-hooks/exhaustive-deps
  const shown = frames ?? o?.frames ?? [];

  const download = useCallback(async () => {
    if (!o) return;
    setBusy(true);
    try {
      if (tg) { await api.sendToChat(o.id); showToast("Файл отправлен в чат с ботом"); return; }
      const blob = await api.resultBlob(o.id);
      const ext = blob.type.includes("gif") ? "gif" : blob.type.startsWith("video") ? "mp4" : blob.type.startsWith("audio") ? "wav" : "jpg";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = `nolla-${o.id}.${ext}`; a.click();
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось скачать"); } finally { setBusy(false); }
  }, [o]);

  async function remove() {
    try { await api.deleteOrder(id); showToast("Работа удалена"); refreshMe(); nav.reset({ name: "history" }); }
    catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось удалить"); setDel(false); }
  }
  async function doRegen() {
    if (regen === null) return;
    const i = regen; setRegen(null); setBusy(true);
    try {
      const r = await api.regenFrame(id, i, uuid());
      setFrames(r.order.frames); setVersion((v) => v + 1); refreshMe();
      showToast(`Кадр создан заново · списано ${tokensText(r.price)}`);
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось пересоздать кадр"); } finally { setBusy(false); }
  }

  if (error && !o) return <ErrorBox message={error} onRetry={() => nav.back()} />;
  if (!o) return <Loading />;

  const fav = me.favorites.orders.includes(o.id);
  const pending = o.status === "created" || o.status === "processing";
  const image = o.status === "done" && (o.result_mime ?? "").startsWith("image/");
  const again = () => nav.go({ name: "create", kind: o.kind, templateId: o.is_system ? undefined : o.template_id, prompt: o.prompt, params: o.params, avatarId: o.avatar_id ?? undefined });
  const next: [string, IconName, () => void][] = image ? [
    ["Изменить", "edit", () => nav.go({ name: "create", kind: "photo", refOrderId: o.id, prompt: o.prompt })],
    ["Улучшить", "sparkle", () => nav.go({ name: "tool", slug: "fx-enhance", refOrderId: o.id })],
    ["Оживить", "film", () => nav.go({ name: "tool", slug: "fx-animate", refOrderId: o.id })],
    ["Создать видео", "video", () => nav.go({ name: "create", kind: "video", refOrderId: o.id, prompt: o.prompt })],
    ["Создать рекламу", "megaphone", () => nav.go({ name: "tool", slug: "mt-ad-image", refOrderId: o.id })],
    ["Создать фотосессию", "camera", () => nav.go({ name: "photoshoots" })],
    ["Использовать как референс", "image", () => nav.go({ name: "create", kind: "photo", refOrderId: o.id })],
    ["Создать вариацию", "refresh", again],
  ] : [["Создать вариацию", "refresh", again]];

  return (
    <>
      <Back onClick={() => nav.back()} />
      <div className="pf-head"><h1 className="pf-h1">{pending ? "Создаём…" : o.status === "failed" ? "Не получилось" : "Готово"}</h1>
        <p className="pf-lead">{o.title && !o.is_system ? `${o.title} · ` : ""}{KIND_LABEL[o.kind]}{o.model_name ? ` · ${o.model_name}` : ""}</p></div>

      {pending && (
        <div className="stage-box">
          <Stages order={o} />
          {o.prompt && <p className="hint">«{o.prompt}»</p>}
          <p className="hint">Можно закрыть приложение: результат появится в истории{me.notify_chat ? " и придёт в чат с ботом" : ""}.</p>
          <button className="btn outline" onClick={() => nav.reset({ name: "history" })}>Открыть историю</button>
        </div>
      )}

      {o.status === "failed" && (
        <>
          <div className="notice bad"><p>{o.error ?? "Не удалось создать результат."} {o.price_credits && !o.used_free ? "Токены вернулись на баланс." : ""}</p></div>
          <div className="comp-row"><button className="btn orange" onClick={again}>Попробовать снова</button><button className="btn outline" onClick={() => nav.reset({ name: "history" })}>В историю</button></div>
        </>
      )}

      {o.status === "done" && (
        <div className="editor">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {o.has_result ? <ResultMedia order={o} /> : <div className="result-box"><div className="result-ph">Файл удалён</div></div>}
            {shown.length > 0 && (
              <div className="pf-sec">
                <h2 className="pf-h2">Кадры</h2>
                <div className="frames">{shown.map((l, i) => <FrameThumb key={i} orderId={o.id} i={i} label={l} version={version} onClick={() => setRegen(i)} />)}</div>
                <span className="hint">Нажмите на кадр, чтобы создать его заново.</span>
              </div>
            )}
          </div>
          <div className="panel stick">
            <div className="comp-row">
              <button className="btn orange grow" disabled={busy || !o.has_result} onClick={download}><Icon name="download" size={18} />Скачать</button>
              <button className="btn outline" onClick={() => toggleFavorite("order", o.id)} aria-pressed={fav} aria-label="В избранное"><Icon name="heart" size={18} fill={fav} /></button>
              <button className="btn outline" onClick={() => setDel(true)} aria-label="Удалить"><Icon name="trash" size={18} /></button>
            </div>
            <div className="next-title">Что хотите сделать дальше?</div>
            <div className="next-grid">{next.map(([l, ic, fn]) => <button key={l} onClick={fn}><Icon name={ic} size={18} />{l}</button>)}</div>
            <div className="meta-table">
              <div><span>Дата</span><b>{fmtTime(o.created_at)}</b></div>
              <div><span>Стоимость</span><b>{o.used_free ? "Бесплатно" : tokensText(o.price_credits)}</b></div>
              {paramRows(o.params).map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}
              {o.prompt && <div><span>Описание</span><b>{o.prompt}</b></div>}
            </div>
          </div>
        </div>
      )}

      {del && (
        <Modal onClose={() => setDel(false)}>
          <h2>Удалить работу?</h2>
          <p className="muted">Файл будет удалён без возможности восстановления.</p>
          <button className="btn orange block" onClick={remove}>Удалить</button>
          <button className="btn outline block" onClick={() => setDel(false)}>Отмена</button>
        </Modal>
      )}
      {regen !== null && (
        <Modal onClose={() => setRegen(null)}>
          <h2>Создать кадр заново?</h2>
          <p className="muted">Кадр «{shown[regen]}» будет заменён новым. Стоимость спишется с баланса; при ошибке токены вернутся.</p>
          <button className="btn orange block" onClick={doRegen}>Создать заново</button>
          <button className="btn outline block" onClick={() => setRegen(null)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
