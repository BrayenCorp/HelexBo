import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import { Empty2, Hdr, Media, Price, Skeletons, Tabs, usePreviews, pickPreview } from "../pf";
import type { CatalogItem } from "../types";
import { useDebounced, useLoad } from "../ui";

const KIND_LABEL: Record<string, string> = { photo: "Фото", video: "Видео", audio: "Аудио" };

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
    <div key={it.id} className="idea">
      <Media url={it.preview_url || (it.kind === "video" ? undefined : pickPreview(photos, it.id))}
        kind={it.preview_url ? it.preview_kind : "image"} icon={it.kind === "video" ? "film" : it.kind === "audio" ? "audio" : "image"}
        ratio={it.kind === "video" ? "wd" : ""} />
      <div className="idea-body">
        <div className="idea-tags">
          <span className="pf-badge">{KIND_LABEL[it.kind] ?? it.kind}</span>
          {it.tag_label && <span className="pf-badge">{it.tag_label}</span>}
          {it.featured && <span className="pf-badge w">Рекомендуем</span>}
        </div>
        <b>{it.title}</b>
        {it.description && <span className="idea-text">{it.description}</span>}
        <div className="idea-foot">
          <Price credits={it.price_credits} />
          <button className="btn orange sm" onClick={() => nav.go({ name: "tool", slug: it.slug })}><Icon name="sparkle" size={15} />Попробовать</button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <Hdr title="Идеи" text="Готовые образы, сцены и приёмы: нажмите «Попробовать» — генератор откроется с готовыми настройками." />
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
