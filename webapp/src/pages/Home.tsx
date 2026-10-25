import { api } from "../api";
import { useApp, showToast } from "../ctx";
import { nf, tokensText } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { CatalogTile, Empty2, ModelTile, Sec } from "../pf";
import type { Kind, Route } from "../types";
import { useLoad } from "../ui";

/** Главные действия: три кнопки и ничего лишнего. */
const ACTIONS: [string, string, IconName, Route][] = [
  ["Создать фото", "Изображение по описанию или из вашего снимка", "image", { name: "create", kind: "photo" as Kind }],
  ["Создать видео", "Ролик по описанию или из фото", "video", { name: "create", kind: "video" as Kind }],
  ["Посмотреть идеи", "Готовые образы — нажал и повторил", "sparkle", { name: "ideas" }],
];

/** Что внутри: разделы приложения одним взглядом. */
const SECTIONS: [string, string, IconName, Route][] = [
  ["Идеи", "Готовые образы", "sparkle", { name: "ideas" }],
  ["Тренды", "Что повторяют сейчас", "flame", { name: "trends" }],
  ["Фотосессии", "Съёмка в любом стиле", "camera", { name: "photoshoots" }],
  ["Эффекты", "Замена фона, ракурсы, примерка", "wand", { name: "effects" }],
  ["Аватары", "Ваш цифровой двойник", "user", { name: "avatars" }],
  ["Маркетинг", "Реклама и фото товаров", "megaphone", { name: "marketing" }],
];

export function Home() {
  const { me, nav } = useApp();
  const home = useLoad(() => api.platformHome(), []);
  const h = home.data;
  const open = (it: { slug: string }) => nav.go({ name: "tool", slug: it.slug });
  const ref = me.referral;

  function copyRef() {
    navigator.clipboard?.writeText(me.ref_link).then(() => showToast("Ссылка скопирована"), () => showToast("Не удалось скопировать"));
  }

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

      {h?.demo && <div className="demo-note"><Icon name="info" size={18} /><span>Демо-режим: результаты создаются локально и помечены как демонстрационные.</span></div>}

      <Sec title="Что умеет Nolla AI">
        <div className="cap-list">
          {h && (
            <>
              <div className="cap-line">
                <span className="cap-ic"><Icon name="image" size={18} /></span>
                <span><b>Изображения</b> — по описанию, по вашему фото или по готовому образу. Модели: {h.models.photo.map((m) => m.name).join(", ") || "скоро"}.</span>
              </div>
              <div className="cap-line">
                <span className="cap-ic"><Icon name="video" size={18} /></span>
                <span><b>Видео</b> — из описания или из снимка. Модели: {h.models.video.map((m) => m.name).join(", ") || "скоро"}.</span>
              </div>
              <div className="cap-line">
                <span className="cap-ic"><Icon name="wand" size={18} /></span>
                <span><b>Готовые инструменты</b> — замена фона, 9 ракурсов, примерка одежды, раскадровка.</span>
              </div>
            </>
          )}
        </div>
        <div className="sec-grid">
          {SECTIONS.map(([title, text, icon, to]) => (
            <button key={title} className="sec-card" onClick={() => nav.go(to)}>
              <span className="sec-ic"><Icon name={icon} size={17} /></span>
              <b>{title}</b><span>{text}</span>
            </button>
          ))}
        </div>
      </Sec>

      {h && h.popular.length > 0 && (
        <Sec title="Популярные идеи" onAll={() => nav.go({ name: "ideas" })}>
          <div className="pf-rail">{h.popular.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div>
        </Sec>
      )}

      {h && h.video_cards.length > 0 && (
        <Sec title={`Что умеет ${h.models.video[0]?.name ?? "видео"}`} onAll={() => nav.go({ name: "models", kind: "video" })}>
          <div className="pf-rail">{h.video_cards.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div>
        </Sec>
      )}

      {h && h.photoshoots.length > 0 && (
        <Sec title="Фотосессии" onAll={() => nav.go({ name: "photoshoots" })}>
          <div className="pf-rail">{h.photoshoots.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div>
        </Sec>
      )}

      {h && h.trends.length > 0 && (
        <Sec title="Тренды" onAll={() => nav.go({ name: "trends" })}>
          <div className="pf-rail">{h.trends.map((it) => <CatalogTile key={it.id} item={it} onOpen={() => open(it)} />)}</div>
        </Sec>
      )}

      {h && (
        <Sec title="Модели" onAll={() => nav.go({ name: "models" })}>
          <div className="pf-rail">
            {[...h.models.photo, ...h.models.video].map((m) => (
              <ModelTile key={m.id} m={m} onPick={() => nav.go({ name: "create", kind: m.kind, modelId: m.id })} />
            ))}
          </div>
        </Sec>
      )}

      {ref && ref.bonus > 0 && (
        <section className="invite">
          <div className="invite-text">
            <b>Приведите друга — получите {tokensText(ref.bonus)}</b>
            <span>Токены начислим, как только он войдёт в приложение.{ref.joined > 0 ? ` Уже пришло друзей: ${nf(ref.joined)}, получено ${nf(ref.earned)}.` : ""}</span>
          </div>
          <div className="invite-link"><code>{me.ref_link}</code></div>
          <button className="btn orange" onClick={copyRef}><Icon name="copy" size={17} />Скопировать ссылку</button>
        </section>
      )}

      {h && h.popular.length === 0 && h.trends.length === 0 && (
        <Empty2 title="Каталог пока пуст" text="Карточки добавляются в файле app/showcase.py." />
      )}
    </>
  );
}
