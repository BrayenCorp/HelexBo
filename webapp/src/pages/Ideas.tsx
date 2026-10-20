import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import { Empty2, Hdr, Media, Price, Skeletons, Tabs, usePreviews, pickPreview } from "../pf";
import type { CatalogItem } from "../types";
import { useDebounced, useLoad } from "../ui";

/** Витрина «Идеи»: карточки, которые владелец добавил в админке. */
export function Ideas() {
  const { nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const [tag, setTag] = useState("all");
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const list = useLoad(() => api.ideas(tag === "all" ? undefined : tag, dq || undefined), [tag, dq]);
  const photos = usePreviews();
  const tags = (meta.data?.sections.idea?.tags ?? []).filter((t) => t.count > 0);

  const card = (it: CatalogItem) => (
    <button key={it.id} className="idea" onClick={() => nav.go({ name: "tool", slug: it.slug })}>
      <Media url={it.preview_url || pickPreview(photos, it.id)} kind={it.preview_url ? it.preview_kind : "image"} icon="image" />
      <span className="idea-tags">
        {it.featured && <span className="pf-badge w">Рекомендуем</span>}
        {it.tag_label && <span className="pf-badge">{it.tag_label}</span>}
      </span>
      <span className="idea-body">
        <b>{it.title}</b>
        {it.description && <span className="idea-text">{it.description}</span>}
        <span className="idea-foot">
          <Price credits={it.price_credits} />
          <span className="btn orange sm"><Icon name="sparkle" size={15} />Попробовать</span>
        </span>
      </span>
    </button>
  );

  return (
    <>
      <Hdr title="Идеи" text="Нравится образ — нажмите «Попробовать» и загрузите своё фото. Остальное сделаем мы." />
      {tags.length > 0 && <Tabs value={tag} onChange={setTag} items={[{ id: "all", label: "Все" }, ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))]} />}
      <div className="fld"><input type="search" placeholder="Найти идею..." aria-label="Поиск идей" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {list.loading && !list.data && <Skeletons n={4} />}
      {list.data && list.data.length === 0 && (
        <Empty2 title="Идей пока нет" text="Владелец добавит их в админке — или загляните в «Тренды» и «Фотосессии»."
          action={<button className="btn outline" onClick={() => nav.go({ name: "trends" })}>Открыть тренды</button>} />
      )}
      <div className="idea-grid">{(list.data ?? []).map(card)}</div>
    </>
  );
}
