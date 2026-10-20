import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { CatalogTile, Empty2, Sec } from "../pf";
import { HistoryRow } from "./History";
import type { Kind, Route } from "../types";
import { useLoad } from "../ui";

/** Главные действия: коротко и крупно, без лишнего. */
const ACTIONS: [string, string, IconName, Route][] = [
  ["Создать фото", "Изображение по описанию", "image", { name: "create", kind: "photo" as Kind }],
  ["Создать видео", "По описанию или из фото", "video", { name: "create", kind: "video" as Kind }],
  ["Посмотреть идеи", "Готовые образы и сцены", "sparkle", { name: "ideas" }],
  ["Мои генерации", "Все ваши работы", "clock", { name: "history" }],
];

export function Home() {
  const { me, nav } = useApp();
  const home = useLoad(() => api.platformHome(), []);
  const h = home.data;
  const open = (it: { slug: string }) => nav.go({ name: "tool", slug: it.slug });

  return (
    <>
      <div className="hero-pf">
        <h1 className="pf-h1">Добро пожаловать<br />в Nolla AI</h1>
        <p className="pf-lead">Создавайте изображения и видео с помощью искусственного интеллекта.</p>
      </div>

      <div className="act-grid-home">
        {ACTIONS.map(([title, text, icon, to]) => (
          <button key={title} className="act-big" onClick={() => nav.go(to)}>
            <span className="act-ic"><Icon name={icon} size={20} /></span>
            <span className="act-txt"><b>{title}</b><span>{text}</span></span>
            <Icon name="chevron" size={16} />
          </button>
        ))}
      </div>

      {h?.demo && (
        <div className="demo-note"><Icon name="info" size={18} /><span>Демо-режим: результаты создаются локально и помечены как демонстрационные.</span></div>
      )}

      {h && h.popular.length > 0 && (
        <Sec title="Популярные идеи" onAll={() => nav.go({ name: "ideas" })}>
          <div className="pf-rail">{h.popular.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div>
        </Sec>
      )}
      {h && h.trends.length > 0 && <Sec title="Тренды" onAll={() => nav.go({ name: "trends" })}><div className="pf-rail">{h.trends.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div></Sec>}
      {h && h.photoshoots.length > 0 && <Sec title="Фотосессии" onAll={() => nav.go({ name: "photoshoots" })}><div className="pf-rail">{h.photoshoots.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div></Sec>}

      <Sec title="Последние работы" onAll={h && h.recent.length ? () => nav.go({ name: "history" }) : undefined}>
        {h && h.recent.length === 0 && <Empty2 title="Пока пусто" text="Здесь появятся ваши работы." action={<button className="btn orange" onClick={() => nav.go({ name: "create" })}>Создать первую</button>} />}
        <div className="hlist">{(h?.recent ?? []).slice(0, 6).map((o) => <HistoryRow key={o.id} o={o} onOpen={() => nav.go({ name: "order", id: o.id })} />)}</div>
      </Sec>
      {me.status === "blocked" && <p className="hint">Создание работ сейчас недоступно.</p>}
    </>
  );
}
