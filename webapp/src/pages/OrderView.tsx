import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { Icon } from "../icons";
import { haptic, openExternal, tg } from "../telegram";
import type { GenParams, Order } from "../types";
import { tokensText } from "../format";
import { AuthMedia, Cover, ErrorBox, Loading, Mark, Modal, PageHeader, formatDate, useLoad } from "../ui";

const PARAM_LABELS: Record<string, string> = { format: "Формат", quality: "Качество", style: "Стиль", lighting: "Освещение", camera: "Камера" };
const VALUE_LABELS: Record<string, string> = {
  standard: "Стандарт", high: "Высокое", realistic: "Реалистичный", cinematic: "Кинематографичный", luxury: "Luxury", studio: "Студийный",
  street: "Уличный", anime: "Аниме", portrait: "Портретный", natural: "Естественное", soft: "Мягкое", contrast: "Контрастное",
  sunset: "Закат", wide: "Широкий угол", closeup: "Крупный план", topdown: "Вид сверху",
};

function paramRows(p: GenParams): [string, string][] {
  return Object.entries(p).filter(([, v]) => v).map(([k, v]) => [PARAM_LABELS[k] ?? k, VALUE_LABELS[v as string] ?? (v as string)]);
}

export function OrderView({ id }: { id: number }) {
  const { me, nav, refreshMe, toggleFavorite } = useApp();
  const q = useLoad<Order>(() => api.order(id), [id]);
  const status = q.data?.status;
  const settled = useRef(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (status === "created" || status === "processing") {
      const timer = setInterval(q.reload, 2500);
      return () => clearInterval(timer);
    }
    if ((status === "done" || status === "failed") && !settled.current) {
      settled.current = true;
      refreshMe(); // баланс и бесплатные попытки могли измениться (возврат при ошибке)
      haptic(status === "done" ? "success" : "warning");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  if (!q.data) return q.error ? <ErrorBox message={q.error} onRetry={q.reload} /> : <Loading />;
  const o = q.data;
  const tplId = o.is_system ? undefined : o.template_id;
  const fav = me.favorites.orders.includes(o.id);
  const reopen = (extra: { prompt?: string; edit?: boolean; withPrompt: boolean }) =>
    nav.go({ name: "generate", kind: o.kind, templateId: tplId, params: o.params, prompt: extra.withPrompt ? o.prompt || undefined : undefined, edit: extra.edit });

  /* ---- в процессе: красивый экран ожидания, а не пустота ---- */
  if (o.status === "created" || o.status === "processing") {
    return (
      <div className="gen-screen">
        <div className="page-head"><button className="back-btn" onClick={() => nav.reset({ name: "history" })} aria-label="К истории"><Icon name="back" size={20} /></button><span /></div>
        <div className="gen-card">
          <Cover url={o.preview_url} seed={o.template_id} className="gen-bg" />
          <span className="shimmer" aria-hidden />
          <span className="gen-mark"><Mark size={56} /></span>
        </div>
        <h1>{o.kind === "photo" ? "Создаём ваше изображение..." : "Генерируем видео..."}</h1>
        <p className="muted">Это может занять несколько минут. Можно закрыть приложение — результат придёт в чат с ботом и появится в истории.</p>
        {o.prompt && <p className="gen-prompt">«{o.prompt}»</p>}
        {me.modes.ai === "mock" && <div className="notice"><p>Тестовый режим: это демонстрационный результат. Для реальной генерации нужно подключить AI API.</p></div>}
        <button className="btn outline block" onClick={() => nav.reset({ name: "history" })}>Открыть историю</button>
      </div>
    );
  }

  if (o.status === "failed") {
    return (
      <>
        <PageHeader title="Не получилось" onBack={() => nav.reset({ name: "history" })} />
        <ErrorBox message={o.error ?? "Не получилось создать результат."} />
        <button className="btn orange block" onClick={() => reopen({ withPrompt: true })}>Попробовать ещё раз</button>
      </>
    );
  }

  /* ---- результат / просмотр из истории ---- */
  async function download() {
    setBusy("download");
    try {
      if (tg) { // в Telegram файл надёжнее всего получить из чата с ботом
        await api.sendToChat(o.id);
        showToast("Отправили файл в чат с ботом — сохраните его оттуда");
      } else {
        const blob = await api.resultBlob(o.id);
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `nolla-${o.id}.${o.result_mime === "image/gif" ? "gif" : o.result_mime?.startsWith("video/") ? "mp4" : "jpg"}`;
        a.click();
      }
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось скачать"); }
    finally { setBusy(null); }
  }

  async function share() {
    setBusy("share");
    try {
      const blob = await api.resultBlob(o.id);
      const file = new File([blob], `nolla-${o.id}.${blob.type.includes("gif") ? "gif" : blob.type.startsWith("video") ? "mp4" : "jpg"}`, { type: blob.type });
      if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], text: "Создано в Nolla AI" }); return; }
    } catch { /* пользователь закрыл окно или браузер не умеет — падаем на ссылку */ }
    finally { setBusy(null); }
    const link = me.bot_link || window.location.origin;
    openExternal(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent("Создано в Nolla AI")}`);
  }

  async function remove() {
    try { await api.deleteOrder(o.id); showToast("Работа удалена"); refreshMe(); nav.reset({ name: "history" }); }
    catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось удалить"); setConfirmDel(false); }
  }

  const rows = paramRows(o.params);
  return (
    <>
      <PageHeader title={o.kind === "photo" ? "Изображение" : "Видео"} onBack={() => nav.back()}
        right={o.has_result ? <button className={`round-icon ${fav ? "on" : ""}`} onClick={() => toggleFavorite("order", o.id)} aria-label="Избранное"><Icon name="heart" size={18} fill={fav} /></button> : undefined} />

      <div className="result-media">
        {o.has_result ? <AuthMedia orderId={o.id} mime={o.result_mime} fallback={o.preview_url} /> : <Cover seed={o.id} />}
        {o.is_stub && <span className="test-badge">Тестовый результат</span>}
      </div>
      {!o.has_result && <p className="muted center">Файл был удалён.</p>}

      {o.has_result && (
        <div className="actions3">
          <button className="act" disabled={busy !== null} onClick={download}><Icon name="download" size={20} />Скачать</button>
          <button className="act" disabled={busy !== null} onClick={share}><Icon name="share" size={20} />Поделиться</button>
          <button className={`act ${fav ? "on" : ""}`} onClick={() => toggleFavorite("order", o.id)}><Icon name="heart" size={20} fill={fav} />{fav ? "Сохранено" : "Сохранить"}</button>
        </div>
      )}
      <div className="actions3">
        <button className="act sec" onClick={() => reopen({ withPrompt: false })}><Icon name="wand" size={20} />Создать похожее</button>
        <button className="act sec" onClick={() => reopen({ withPrompt: true, edit: true })}><Icon name="edit" size={20} />Изменить</button>
        <button className="act sec" onClick={() => reopen({ withPrompt: true })}><Icon name="refresh" size={20} />Повторить</button>
      </div>

      <div className="meta-card">
        <div className="meta-row"><span className="muted">Дата</span><b>{formatDate(o.created_at)}, {new Date(o.created_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</b></div>
        <div className="meta-row"><span className="muted">Тип</span><b>{o.kind === "photo" ? "Фото" : "Видео"}</b></div>
        <div className="meta-row"><span className="muted">Стоимость</span><b>{o.used_free ? "Бесплатно" : tokensText(o.price_credits)}</b></div>
        {!o.is_system && o.title && <div className="meta-row"><span className="muted">Стиль</span><b>{o.title}</b></div>}
        {rows.map(([k, v]) => <div key={k} className="meta-row"><span className="muted">{k}</span><b>{v}</b></div>)}
        {o.prompt && <div className="meta-prompt"><span className="muted">Описание</span><p>{o.prompt}</p></div>}
      </div>

      <button className="btn ghost danger-text block" onClick={() => setConfirmDel(true)}><Icon name="trash" size={17} /> Удалить</button>
      {confirmDel && (
        <Modal onClose={() => setConfirmDel(false)}>
          <span className="modal-icon danger"><Icon name="trash" size={26} /></span>
          <h2>Удалить работу?</h2>
          <p className="muted">Файл будет удалён без возможности восстановления.</p>
          <button className="btn danger block" onClick={remove}>Удалить</button>
          <button className="btn outline block" onClick={() => setConfirmDel(false)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}

