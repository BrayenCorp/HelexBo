import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { Order } from "../types";
import { AuthMedia, Chips, Cover, Empty, ErrorBox, Heart, Loading, Skeleton, formatDuration, useLoad } from "../ui";

type Filter = "all" | "photo" | "video" | "fav";

function Card({ o }: { o: Order }) {
  const { me, nav, toggleFavorite } = useApp();
  const busy = o.status === "created" || o.status === "processing";
  return (
    <button className="hcard" onClick={() => nav.go({ name: "order", id: o.id })}>
      {busy && <><Skeleton className="sk-fill" /><span className="hcard-state">Создаётся…</span></>}
      {o.status === "failed" && <><Cover seed={o.id} /><span className="hcard-state bad">Ошибка</span></>}
      {o.status === "done" && (o.has_result
        ? <AuthMedia orderId={o.id} mime={o.result_mime} fallback={o.preview_url} controls={false} />
        : <Cover seed={o.id} />)}
      <span className="hcard-type"><Icon name={o.kind === "photo" ? "image" : "video"} size={13} /></span>
      {o.kind === "video" && o.status === "done" && <span className="hcard-dur">{formatDuration(o.duration_sec)}</span>}
      {o.status === "done" && o.has_result && (
        <span className="hcard-heart"><Heart on={me.favorites.orders.includes(o.id)} onClick={() => toggleFavorite("order", o.id)} /></span>
      )}
    </button>
  );
}

export function History({ initial = "all" }: { initial?: Filter }) {
  const { me, nav } = useApp();
  const [filter, setFilter] = useState<Filter>(initial);
  const q = useLoad(() => api.orders(), []);
  const working = q.data?.some((o) => o.status === "created" || o.status === "processing");
  const { reload } = q;
  useEffect(() => {
    if (!working) return;
    const t = setInterval(reload, 3000);
    return () => clearInterval(t);
  }, [working, reload]);

  const items = (q.data ?? []).filter((o) =>
    filter === "all" || (filter === "fav" ? me.favorites.orders.includes(o.id) : o.kind === filter));

  return (
    <>
      <h1 className="h1">История генераций</h1>
      <Chips compact value={filter} onChange={setFilter} options={[["all", "Все", "grid"], ["photo", "Фото", "image"], ["video", "Видео", "video"], ["fav", "Избранное", "heart"]]} />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && items.length === 0 && (
        <Empty icon={filter === "fav" ? "heart" : "sparkle"} title={filter === "fav" ? "В избранном пока пусто" : "Здесь появятся ваши работы"}
          text={filter === "fav" ? "Нажмите на сердечко у работы, чтобы сохранить её." : "Создайте первое изображение или видео."}
          action={<button className="btn orange sm" onClick={() => nav.go({ name: "generate", kind: filter === "video" ? "video" : "photo" })}>Создать</button>} />
      )}
      <div className="hgrid">{items.map((o) => <Card key={o.id} o={o} />)}</div>
    </>
  );
}
