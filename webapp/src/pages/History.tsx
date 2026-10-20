import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtTime, tokensText } from "../format";
import { Icon } from "../icons";
import { Empty2, Hdr, KIND_LABEL, STATUS_LABEL, Tabs } from "../pf";
import { tg } from "../telegram";
import type { HistoryFilter, Order } from "../types";
import { ErrorBox, Loading, Modal, useLoad } from "../ui";

const FILTERS: [HistoryFilter, string][] = [["all", "Все"], ["images", "Фото"], ["video", "Видео"], ["audio", "Аудио"], ["fav", "Избранное"]];
const GROUPS: Record<string, HistoryFilter> = { effects: "images", avatars: "images", marketing: "images" };

export function Thumb({ o }: { o: Order }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (o.status !== "done" || !o.has_result || o.kind === "audio") return;
    let alive = true; let u: string | null = null;
    api.resultBlob(o.id).then((b) => { if (alive) { u = URL.createObjectURL(b); setUrl(u); } }).catch(() => undefined);
    return () => { alive = false; if (u) URL.revokeObjectURL(u); };
  }, [o.id, o.status, o.has_result, o.kind]);
  const video = o.result_mime?.startsWith("video/");
  return (
    <span className="hthumb">
      {url ? (video ? <video src={url} muted playsInline /> : <img src={url} alt="" />) : <Icon name={o.kind === "audio" ? "audio" : o.kind === "video" ? "film" : "image"} size={22} />}
    </span>
  );
}

export function HistoryRow({ o, onOpen }: { o: Order; onOpen: () => void }) {
  const cls = o.status === "done" ? "ok" : o.status === "failed" ? "err" : "";
  return (
    <button className="hrow" onClick={onOpen}>
      <Thumb o={o} />
      <span className="grow">
        <b>{o.prompt || o.title || KIND_LABEL[o.kind]}</b>
        <span>{KIND_LABEL[o.kind]}{o.model_name ? ` · ${o.model_name}` : ""} · {fmtTime(o.created_at)}</span>
        <span>{o.used_free ? "Бесплатно" : tokensText(o.price_credits)}</span>
      </span>
      <span className={`st ${cls}`}>{STATUS_LABEL[o.status]}</span>
    </button>
  );
}

/** «Мои генерации»: всё созданное — и в приложении, и в боте. */
export function History({ initial }: { initial?: HistoryFilter }) {
  const { me, nav, refreshMe, toggleFavorite } = useApp();
  const [filter, setFilter] = useState<HistoryFilter>(initial ?? "all");
  const [del, setDel] = useState<Order | null>(null);
  const [busy, setBusy] = useState(false);
  const q = useLoad(() => api.orders(), []);
  const list = q.data ?? [];
  const pending = list.some((o) => o.status === "created" || o.status === "processing");
  useEffect(() => { if (!pending) return; const t = setTimeout(q.reload, 3000); return () => clearTimeout(t); }, [pending, q.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => list.filter((o) => {
    if (filter === "all") return true;
    if (filter === "fav") return me.favorites.orders.includes(o.id);
    return (GROUPS[o.group] ?? o.group) === filter;
  }), [list, filter, me.favorites.orders]);

  async function download(o: Order) {
    setBusy(true);
    try {
      if (tg) { await api.sendToChat(o.id); showToast("Файл отправлен в чат с ботом"); return; }
      const blob = await api.resultBlob(o.id);
      const ext = blob.type.includes("gif") ? "gif" : blob.type.startsWith("video") ? "mp4" : blob.type.startsWith("audio") ? "wav" : "jpg";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = `nolla-${o.id}.${ext}`; a.click();
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось скачать"); } finally { setBusy(false); }
  }
  async function remove() {
    if (!del) return;
    try { await api.deleteOrder(del.id); showToast("Работа удалена"); setDel(null); q.reload(); refreshMe(); }
    catch { showToast("Не удалось удалить"); }
  }
  const again = (o: Order) => nav.go({ name: "create", kind: o.kind, templateId: o.is_system ? undefined : o.template_id, prompt: o.prompt, params: o.params, modelId: undefined });

  return (
    <>
      <Hdr title="Мои генерации" text="Всё, что вы создали — в приложении и в боте." />
      <Tabs value={filter} onChange={(v) => setFilter(v as HistoryFilter)} items={FILTERS.map(([id, label]) => ({ id, label }))} />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && shown.length === 0 && (
        <Empty2 title={filter === "all" ? "Работ пока нет" : "В этом разделе пусто"} text="Создайте первую работу — она появится здесь."
          action={<button className="btn orange" onClick={() => nav.go({ name: "create" })}>Создать</button>} />
      )}
      <div className="hlist">
        {shown.map((o) => {
          const fav = me.favorites.orders.includes(o.id);
          return (
            <div key={o.id} className="gcard">
              <HistoryRow o={o} onOpen={() => nav.go({ name: "order", id: o.id })} />
              <div className="hacts">
                <button onClick={() => nav.go({ name: "order", id: o.id })}><Icon name="eye" size={15} />Открыть</button>
                {o.status === "done" && o.has_result && <button disabled={busy} onClick={() => download(o)}><Icon name="download" size={15} />Скачать</button>}
                <button onClick={() => again(o)}><Icon name="refresh" size={15} />Заново</button>
                <button className={fav ? "on" : ""} onClick={() => toggleFavorite("order", o.id)}><Icon name="heart" size={15} fill={fav} />{fav ? "В избранном" : "В избранное"}</button>
                <button onClick={() => setDel(o)}><Icon name="trash" size={15} />Удалить</button>
              </div>
            </div>
          );
        })}
      </div>
      {del && (
        <Modal onClose={() => setDel(null)}>
          <h2>Удалить работу?</h2>
          <p className="muted">Файл будет удалён без возможности восстановления.</p>
          <button className="btn orange block" onClick={remove}>Удалить</button>
          <button className="btn outline block" onClick={() => setDel(null)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
