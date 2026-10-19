import { useState } from "react";
import { api } from "../api";
import { useApp, showToast } from "../ctx";
import { Icon } from "../icons";
import { CatalogTile, Empty2, Hdr, Price, Skeletons, Tabs } from "../pf";
import type { CatalogItem, Section } from "../types";
import { useDebounced, useLoad } from "../ui";

interface Cfg { section: Section; title: string; text: string; all?: boolean; popular?: boolean; search?: boolean }

/** Общий каталог: вкладки по категориям, поиск, карточки с ценой. */
export function Catalog({ cfg, tag: initTag }: { cfg: Cfg; tag?: string }) {
  const { nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const [tag, setTag] = useState(initTag ?? "all");
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const list = useLoad(() => api.catalog(cfg.section, { tag: tag === "all" ? undefined : tag, q: dq || undefined }), [cfg.section, tag, dq]);
  const tags = (meta.data?.sections[cfg.section]?.tags ?? []).filter((t) => t.count > 0);
  const items: [string, string, number | undefined][] = [["all", "Все", undefined]];
  const tabs = [{ id: "all", label: "Все" }, ...(cfg.popular ? [{ id: "popular", label: "Популярные" }] : []), ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))];
  void items;
  return (
    <>
      <Hdr title={cfg.title} text={cfg.text} />
      <Tabs value={tag} onChange={setTag} items={tabs} />
      {cfg.search && (
        <div className="fld"><input type="search" placeholder="Найти по названию..." aria-label="Поиск" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      )}
      {list.loading && !list.data && <Skeletons />}
      {list.error && <Empty2 title="Не удалось загрузить" text={list.error} action={<button className="btn outline" onClick={list.reload}>Повторить</button>} />}
      {list.data && list.data.length === 0 && <Empty2 title="Ничего не найдено" text="Попробуйте другую категорию или запрос." />}
      <div className="pf-grid">{(list.data ?? []).map((it) => <CatalogTile key={it.id} item={it} onOpen={() => nav.go({ name: "tool", slug: it.slug })} />)}</div>
    </>
  );
}

export const EFFECTS_CFG: Cfg = { section: "effect", title: "Эффекты", text: "Инструменты для фото и видео: правки, улучшение, раскадровка, ракурсы и примерка." };
export const TRENDS_CFG: Cfg = { section: "trend", title: "Тренды", text: "Готовые образы и сцены. Загрузите фото — остальное сделаем мы.", popular: true };
export const SHOOTS_CFG: Cfg = { section: "photoshoot", title: "Фотосессии", text: "Выберите стиль съёмки и получите серию кадров.", popular: true };

/** Промпты: сохраните удачный текст или сразу создайте по нему. */
export function Prompts() {
  const { nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const [tag, setTag] = useState("all");
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const list = useLoad(() => api.catalog("prompt", { tag: tag === "all" ? undefined : tag, q: dq || undefined }), [tag, dq]);
  const tags = (meta.data?.sections.prompt?.tags ?? []).filter((t) => t.count > 0);
  const copy = (p: CatalogItem) => { navigator.clipboard?.writeText(p.prompt ?? "").then(() => showToast("Промпт скопирован"), () => showToast("Не удалось скопировать")); };
  return (
    <>
      <Hdr title="Промпты" text="Проверенные описания для красивых результатов. Скопируйте или сразу создайте." />
      <Tabs value={tag} onChange={setTag} items={[{ id: "all", label: "Все" }, ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))]} />
      <div className="fld"><input type="search" placeholder="Найти промпт..." aria-label="Поиск" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {list.loading && !list.data && <Skeletons n={4} />}
      {list.data && list.data.length === 0 && <Empty2 title="Ничего не найдено" />}
      <div className="pf-grid wide">
        {(list.data ?? []).map((p) => (
          <div key={p.id} className="panel">
            <b>{p.title}</b>
            <span className="pf-badge" style={{ alignSelf: "flex-start" }}>{p.tag_label}</span>
            <p className="prompt-text">{p.prompt}</p>
            {p.supported_models && p.supported_models.length > 0 && <span className="hint">Подходит для: {p.supported_models.slice(0, 3).join(", ")}{p.supported_models.length > 3 ? ` и ещё ${p.supported_models.length - 3}` : ""}</span>}
            <div className="comp-row">
              <button className="btn orange sm" onClick={() => nav.go({ name: "create", kind: "photo", prompt: p.prompt })}>Использовать</button>
              <button className="btn outline sm" onClick={() => copy(p)}><Icon name="copy" size={15} />Копировать</button>
              <span className="grow" /><Price credits={p.price_credits} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/** Маркетинг: инструменты и шаблоны для рекламы, товаров, соцсетей и маркетплейсов. */
export function Marketing() {
  const { nav } = useApp();
  const meta = useLoad(() => api.meta(), []);
  const [tag, setTag] = useState("all");
  const tools = useLoad(() => api.catalog("mtool", { tag: tag === "all" ? undefined : tag }), [tag]);
  const tpls = useLoad(() => api.catalog("marketing", { tag: tag === "all" ? undefined : tag }), [tag]);
  const tags = (meta.data?.sections.marketing?.tags ?? []).filter((t) => t.count > 0);
  return (
    <>
      <Hdr title="Маркетинг" text="Рекламные изображения и видео, фото товаров, карточки для маркетплейсов и контент для соцсетей." />
      <Tabs value={tag} onChange={setTag} items={[{ id: "all", label: "Все" }, ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))]} />
      <section className="pf-sec"><h2 className="pf-h2">Инструменты</h2>
        {tools.loading && !tools.data && <Skeletons n={4} />}
        {tools.data && tools.data.length === 0 && <Empty2 title="В этой категории инструментов нет" />}
        <div className="pf-grid wide">{(tools.data ?? []).map((it) => (
          <button key={it.id} className="row-card" onClick={() => nav.go({ name: "tool", slug: it.slug })}>
            <span className="rc-ic"><Icon name={it.kind === "video" ? "film" : "megaphone"} size={20} /></span>
            <span className="grow"><b>{it.title}</b><span>{it.description}</span></span><Price credits={it.price_credits} />
          </button>))}</div>
      </section>
      <section className="pf-sec"><h2 className="pf-h2">Шаблоны</h2>
        {tpls.data && tpls.data.length === 0 && <Empty2 title="В этой категории шаблонов нет" />}
        <div className="pf-grid">{(tpls.data ?? []).map((it) => <CatalogTile key={it.id} item={it} onOpen={() => nav.go({ name: "tool", slug: it.slug })} />)}</div>
      </section>
    </>
  );
}
