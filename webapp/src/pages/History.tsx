import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtTime } from "../format";
import { Icon } from "../icons";
import { Empty2, Hdr, KIND_LABEL, STATUS_LABEL, Tabs } from "../pf";
import type { HistoryFilter, Order } from "../types";
import { ErrorBox, Loading, useLoad } from "../ui";

const FILTERS: [HistoryFilter, string][] = [["all", "Все"], ["images", "Изображения"], ["video", "Видео"], ["audio", "Аудио"], ["effects", "Эффекты"], ["avatars", "Аватары"], ["marketing", "Маркетинг"], ["fav", "Избранное"]];

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
        <span>{o.is_system ? KIND_LABEL[o.kind] : o.title} · {fmtTime(o.created_at)}</span>
      </span>
      <span className={`st ${cls}`}>{STATUS_LABEL[o.status]}</span>
    </button>
  );
}

export function History({ initial }: { initial?: HistoryFilter }) {
  const { me, nav, refreshMe } = useApp();
  const [filter, setFilter] = useState<HistoryFilter>(initial ?? "all");
  const q = useLoad(() => api.orders(), []);
  const list = q.data ?? [];
  const pending = list.some((o) => o.status === "created" || o.status === "processing");
  useEffect(() => { if (!pending) return; const t = setTimeout(q.reload, 3000); return () => clearTimeout(t); }, [pending, q.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => list.filter((o) => filter === "all" ? true : filter === "fav" ? me.favorites.orders.includes(o.id) : o.group === filter), [list, filter, me.favorites.orders]);

  async function remove(o: Order) {
    try { await api.deleteOrder(o.id); showToast("Работа удалена"); q.reload(); refreshMe(); } catch { showToast("Не удалось удалить"); }
  }
  return (
    <>
      <Hdr title="История" text="Все ваши работы: статусы, результаты и повтор в один клик." />
      <Tabs value={filter} onChange={(v) => setFilter(v as HistoryFilter)} items={FILTERS.map(([id, label]) => ({ id, label }))} />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && shown.length === 0 && (
        <Empty2 title={filter === "all" ? "Работ пока нет" : "В этом разделе пусто"} text="Создайте первую работу — она появится здесь."
          action={<button className="btn orange" onClick={() => nav.go({ name: "create" })}>Создать</button>} />
      )}
      <div className="hlist">
        {shown.map((o) => (
          <div key={o.id} className="hwrap">
            <HistoryRow o={o} onOpen={() => nav.go({ name: "order", id: o.id })} />
            {(o.status === "done" || o.status === "failed") && <button className="btn outline" aria-label="Удалить" onClick={() => remove(o)}><Icon name="trash" size={16} /></button>}
          </div>
        ))}
      </div>
    </>
  );
}
