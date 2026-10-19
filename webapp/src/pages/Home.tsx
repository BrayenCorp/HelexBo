import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { CatalogTile, Empty2, Sec } from "../pf";
import { HistoryRow } from "./History";
import type { Kind, Route } from "../types";
import { useLoad } from "../ui";

const QA_ICONS: IconName[] = ["image", "video", "film", "edit", "user", "camera", "megaphone", "tag"];

function actionRoute(a: Record<string, unknown>): Route {
  switch (a.to) {
    case "create": return { name: "create", kind: a.kind as Kind };
    case "tool": return { name: "tool", slug: String(a.slug) };
    case "avatars": return { name: "avatars" };
    case "photoshoots": return { name: "photoshoots" };
    case "marketing": return { name: "marketing" };
    default: return { name: "create" };
  }
}

export function Home() {
  const { nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const home = useLoad(() => api.platformHome(), []);
  const [kind, setKind] = useState<Kind>("photo");
  const [prompt, setPrompt] = useState("");
  const h = home.data;
  const open = (it: { slug: string }) => nav.go({ name: "tool", slug: it.slug });
  const labels: [Kind, string][] = [["photo", "Изображение"], ["video", "Видео"], ["audio", "Аудио"]];

  return (
    <>
      <div className="hero-pf">
        <h1 className="pf-h1">Создавай всё,<br />что можешь представить.</h1>
        <p className="pf-lead">Изображения, видео и озвучка — в одном месте. Выбирайте лучшие AI-модели и получайте результат за секунды.</p>
      </div>

      <div className="composer">
        <h2>Что создаём?</h2>
        <div className="pf-seg" style={{ alignSelf: "flex-start" }} role="tablist">
          {labels.map(([k, l]) => <button key={k} role="tab" className={kind === k ? "on" : ""} onClick={() => setKind(k)}>{l}</button>)}
        </div>
        <textarea value={prompt} maxLength={kind === "audio" ? 2000 : 500} onChange={(e) => setPrompt(e.target.value)}
          placeholder={kind === "audio" ? "Введите текст для озвучки..." : "Опишите, что хотите создать..."} aria-label="Описание" />
        <div className="comp-row">
          {kind !== "audio" && <button className="btn outline" onClick={() => nav.go({ name: "create", kind, prompt })}><Icon name="upload" size={17} />Загрузить изображение</button>}
          {kind !== "audio" && <button className="btn outline" onClick={() => nav.go({ name: "create", kind, prompt })}><Icon name="image" size={17} />Добавить референс</button>}
          <button className="btn outline" onClick={() => nav.go({ name: "models", kind })}><Icon name="layers" size={17} />Выбрать модель</button>
          <span className="grow" />
          <button className="btn orange" onClick={() => nav.go({ name: "create", kind, prompt })}>Создать</button>
        </div>
        <div className="cost-line">Стоимость: <b>12 токенов</b> <span style={{ opacity: 0.7 }}>· точная цена зависит от модели</span></div>
      </div>

      {h?.demo && (
        <div className="demo-note"><Icon name="info" size={18} /><span>Работает демо-режим: результаты создаются локально и помечены как демонстрационные. Реальные AI-модели подключаются через настройки сервера.</span></div>
      )}

      <section className="pf-sec">
        <h2 className="pf-h2">Быстрые действия</h2>
        <div className="qa-grid">
          {(meta.data?.quick_actions ?? []).map((q, i) => {
            const a = q.action;
            return (
              <button key={q.title} className="qa" onClick={() => nav.go(actionRoute(a))}>
                <span className="qa-ic"><Icon name={QA_ICONS[i] ?? "sparkle"} size={18} /></span>
                <b>{q.title}</b><small>{q.text}</small>
              </button>
            );
          })}
        </div>
      </section>

      {h && h.popular.length > 0 && <Sec title="Популярное"><div className="pf-rail">{h.popular.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div></Sec>}
      {h && h.trends.length > 0 && <Sec title="Тренды" onAll={() => nav.go({ name: "trends" })}><div className="pf-rail">{h.trends.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div></Sec>}
      {h && h.photoshoots.length > 0 && <Sec title="Фотосессии" onAll={() => nav.go({ name: "photoshoots" })}><div className="pf-rail">{h.photoshoots.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div></Sec>}

      <Sec title="Последние работы" onAll={h && h.recent.length ? () => nav.go({ name: "history" }) : undefined}>
        {h && h.recent.length === 0 && <Empty2 title="Пока пусто" text="Здесь появятся ваши работы." action={<button className="btn orange" onClick={() => nav.go({ name: "create" })}>Создать первую</button>} />}
        <div className="hlist">{(h?.recent ?? []).slice(0, 6).map((o) => <HistoryRow key={o.id} o={o} onOpen={() => nav.go({ name: "order", id: o.id })} />)}</div>
      </Sec>
    </>
  );
}
