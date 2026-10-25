import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { CatalogTile, Empty2, Hdr, Skeletons, Tabs } from "../pf";
import { useDebounced, useLoad } from "../ui";

/** Витрина «Идеи»: только снимки. Понравилось — нажал и повторил со своим фото. */
export function Ideas() {
  const { me, nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const [tag, setTag] = useState("all");
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const list = useLoad(() => api.ideas(tag === "all" || tag === "fav" ? undefined : tag, dq || undefined), [tag, dq]);
  const tags = (meta.data?.sections.idea?.tags ?? []).filter((t) => t.count > 0);
  const shown = (list.data ?? []).filter((it) => tag !== "fav" || me.favorites.templates.includes(it.id));

  return (
    <>
      <Hdr title="Идеи" text="Нравится кадр — нажмите на него и загрузите своё фото." />
      {tags.length > 0 && <Tabs value={tag} onChange={setTag} items={[{ id: "all", label: "Все" }, { id: "fav", label: "Избранное" }, ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))]} />}
      <div className="fld"><input type="search" placeholder="Найти идею..." aria-label="Поиск идей" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {list.loading && !list.data && <Skeletons n={4} />}
      {list.data && shown.length === 0 && (
        <Empty2 title="Идей пока нет" text="Карточки добавляются в файле app/showcase.py — или загляните в «Тренды» и «Фотосессии»."
          action={<button className="btn outline" onClick={() => nav.go({ name: "trends" })}>Открыть тренды</button>} />
      )}
      <div className="pf-grid">{shown.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => nav.go({ name: "tool", slug: it.slug })} />)}</div>
    </>
  );
}
