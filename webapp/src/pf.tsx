import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { tokensText } from "./format";
import type { AiModel, CatalogItem, Order, Route } from "./types";
import { Skeleton } from "./ui";

/** Плашка вместо превью: пока админ не загрузил свои примеры, выдуманных картинок не показываем. */
export function Ph({ icon = "image", label = "Пример скоро" }: { icon?: IconName; label?: string }) {
  return <span className="tile-ph"><Icon name={icon} size={26} />{label}</span>;
}

export function Media({ url, kind = "image", icon = "image", ratio = "" }: { url?: string; kind?: "image" | "video"; icon?: IconName; ratio?: "sq" | "wd" | "" }) {
  return (
    <span className={`tile-media ${ratio}`}>
      {!url ? <Ph icon={icon} /> : kind === "video" || /\.(mp4|webm|mov)$/i.test(url) ? <video src={url} muted loop playsInline autoPlay preload="metadata" /> : <img src={url} alt="" loading="lazy" />}
    </span>
  );
}

export function Hdr({ title, text, right }: { title: string; text?: string; right?: ReactNode }) {
  return (
    <div className="pf-head-row">
      <div className="pf-head"><h1 className="pf-h1">{title}</h1>{text && <p className="pf-lead">{text}</p>}</div>
      {right}
    </div>
  );
}

export function Sec({ title, children, onAll }: { title: string; children: ReactNode; onAll?: () => void }) {
  return (
    <section className="pf-sec">
      <div className="pf-sec-head"><h2 className="pf-h2">{title}</h2>{onAll && <button className="pf-link" onClick={onAll}>Все <Icon name="chevron" size={14} /></button>}</div>
      {children}
    </section>
  );
}

export function Back({ onClick, label = "Назад" }: { onClick: () => void; label?: string }) {
  return <button className="pf-back" onClick={onClick}><Icon name="back" size={18} />{label}</button>;
}

export function Tabs({ value, items, onChange }: { value: string; items: { id: string; label: string; count?: number }[]; onChange: (id: string) => void }) {
  return (
    <div className="pf-tabs" role="tablist">
      {items.map((t) => (
        <button key={t.id} role="tab" aria-selected={t.id === value} className={`pf-tab ${t.id === value ? "on" : ""}`} onClick={() => onChange(t.id)}>
          {t.label}{t.count !== undefined && <small>{t.count}</small>}
        </button>
      ))}
    </div>
  );
}

export function Empty2({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return <div className="empty-pf"><b>{title}</b>{text && <span>{text}</span>}{action}</div>;
}

export function Skeletons({ n = 8 }: { n?: number }) {
  return <div className="pf-grid">{Array.from({ length: n }, (_, i) => <Skeleton key={i} className="sk-card" />)}</div>;
}

export function Price({ credits }: { credits: number }) {
  return <span className="tile-price"><Icon name="coin" size={13} />{credits ? tokensText(credits) : "Бесплатно"}</span>;
}

/** Карточка элемента каталога (эффект, тренд, фотосессия, маркетинг). */
export function CatalogTile({ item, onOpen }: { item: CatalogItem; onOpen: () => void }) {
  return (
    <button className="tile" onClick={onOpen}>
      <Media url={item.preview_url} kind={item.preview_kind} icon={item.kind === "video" ? "film" : "image"} />
      <span className="tile-flags">{item.kind === "video" && <span className="pf-badge">Видео</span>}{item.is_popular && <span className="pf-badge w">Популярно</span>}</span>
      <span className="tile-body"><b>{item.title}</b>{item.description && <span>{item.description}</span>}<Price credits={item.price_credits} /></span>
    </button>
  );
}

export function ModelTile({ m, selected, onPick }: { m: AiModel; selected?: boolean; onPick: () => void }) {
  return (
    <button className="tile" style={selected ? { borderColor: "#fff" } : undefined} onClick={onPick}>
      <Media url={m.image_url} icon={m.kind === "video" ? "film" : m.kind === "audio" ? "audio" : "image"} ratio="wd" />
      <span className="tile-flags">{m.is_new && <span className="pf-badge w">Новое</span>}</span>
      <span className="tile-body"><b>{m.name}</b><span>{m.description}</span><Price credits={m.price_credits} /></span>
    </button>
  );
}

/** Этапы генерации. Проценты не выдумываем: показываем только то, что сообщил провайдер. */
export const STAGES: [string, string][] = [["queued", "В очереди"], ["creating", "Создаётся"], ["processing", "Обрабатывается"], ["almost", "Почти готово"], ["done", "Готово"]];

export function Stages({ order }: { order: Pick<Order, "status" | "stage"> }) {
  const cur = order.status === "done" ? 4 : order.status === "created" && !order.stage ? 0 : Math.max(1, STAGES.findIndex(([k]) => k === order.stage));
  return (
    <div className="stage-steps" aria-live="polite">
      {STAGES.map(([k, label], i) => <div key={k} className={`stage-step ${i < cur ? "done" : i === cur ? "now" : ""}`}><i />{label}</div>)}
    </div>
  );
}

/** Следите за заказом: опрашиваем сервер, пока он не завершится. */
export function useOrderPoll(id: number | null) {
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!id) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = () => {
      api.order(id).then((o) => {
        if (!alive) return;
        setOrder(o);
        if (o.status === "created" || o.status === "processing") timer = setTimeout(tick, 1500);
      }).catch((e: Error) => alive && setError(e.message));
    };
    tick();
    return () => { alive = false; clearTimeout(timer); };
  }, [id]);
  return { order, error };
}

export const KIND_LABEL: Record<string, string> = { photo: "Изображение", video: "Видео", audio: "Аудио" };
export const STATUS_LABEL: Record<string, string> = { created: "В очереди", processing: "Создаётся", done: "Готово", failed: "Ошибка" };

export function nextRoute(to: string, extra: Partial<Route> = {}): Route {
  return { name: to, ...extra } as Route;
}

export function uuid(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}
