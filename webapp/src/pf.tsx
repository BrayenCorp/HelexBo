import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { tokensText } from "./format";
import type { AiModel, CatalogItem, Order, Route } from "./types";
import { Skeleton } from "./ui";

/* ------------------------------------------------------------------ ваши фото для обложек
   Фото лежат в data/media/previews (загружаются в админке: «Контент → Фото для обложек»).
   Карточка всегда получает одно и то же фото — по своему номеру, поэтому обложки не прыгают. */
let previewCache: string[] | null = null;
let previewPending: Promise<string[]> | null = null;

export function usePreviews(): string[] {
  const [list, setList] = useState<string[]>(previewCache ?? []);
  useEffect(() => {
    if (previewCache) return;
    let alive = true;
    previewPending = previewPending ?? api.previews().catch(() => [] as string[]);
    previewPending.then((l) => { previewCache = l; if (alive) setList(l); });
    return () => { alive = false; };
  }, []);
  return list;
}

/** Одно и то же фото для одной и той же карточки. */
export function pickPreview(list: string[], id: number): string | undefined {
  if (!list.length) return undefined;
  const h = Math.abs(Math.imul(id || 1, 2654435761)) % list.length;
  return list[h];
}

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
  const photos = usePreviews();
  const cover = item.preview_url || (item.kind === "video" ? undefined : pickPreview(photos, item.id));
  return (
    <button className="tile" onClick={onOpen}>
      <Media url={cover} kind={item.preview_url ? item.preview_kind : "image"} icon={item.kind === "video" ? "film" : "image"} ratio={item.kind === "video" ? "wd" : ""} />
      <span className="tile-flags">{item.kind === "video" && <span className="pf-badge">Видео</span>}{item.is_popular && <span className="pf-badge w">Популярно</span>}</span>
      <span className="tile-body"><b>{item.title}</b>{item.description && <span>{item.description}</span>}<Price credits={item.price_credits} /></span>
    </button>
  );
}

export function ModelTile({ m, selected, onPick }: { m: AiModel; selected?: boolean; onPick: () => void }) {
  const photos = usePreviews();
  const cover = m.image_url || (m.kind === "photo" ? pickPreview(photos, 1000 + m.id) : undefined);
  return (
    <button className={`tile ${selected ? "on" : ""}`} onClick={onPick}>
      <Media url={cover} icon={m.kind === "video" ? "film" : m.kind === "audio" ? "audio" : "image"} ratio={m.kind === "photo" ? "" : "wd"} />
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


/* ------------------------------------------------------------------ выпадающее меню
   Одно на всё приложение: плавное, с галочкой у выбранного, закрывается по клику мимо и по Esc. */
export interface Opt { id: string; label: string; note?: string; right?: string; disabled?: boolean }

export function Dropdown({ value, options, onChange, placeholder = "Выберите", disabled = false, ariaLabel }:
  { value: string; options: Opt[]; onChange: (id: string) => void; placeholder?: string; disabled?: boolean; ariaLabel?: string }) {
  const [open, setOpen] = useState(false);
  const [up, setUp] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const cur = options.find((o) => o.id === value);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  function toggle() {
    if (disabled) return;
    const r = box.current?.getBoundingClientRect();
    setUp(!!r && window.innerHeight - r.bottom < Math.min(320, options.length * 52 + 16));
    setOpen((v) => !v);
  }

  return (
    <div className={`dd ${open ? "open" : ""}`} ref={box}>
      <button type="button" className="dd-btn" onClick={toggle} disabled={disabled} aria-haspopup="listbox" aria-expanded={open} aria-label={ariaLabel}>
        <span className="dd-val">
          <b>{cur?.label ?? placeholder}</b>
          {cur?.note && <span>{cur.note}</span>}
        </span>
        {cur?.right && <span className="dd-right">{cur.right}</span>}
        <Icon name="chevron-down" size={18} />
      </button>
      {open && (
        <div className={`dd-menu ${up ? "up" : ""}`} role="listbox">
          {options.map((o) => (
            <button key={o.id} type="button" role="option" aria-selected={o.id === value} disabled={o.disabled}
              className={`dd-item ${o.id === value ? "on" : ""}`} onClick={() => { onChange(o.id); setOpen(false); }}>
              <span className="dd-val"><b>{o.label}</b>{o.note && <span>{o.note}</span>}</span>
              {o.right && <span className="dd-right">{o.right}</span>}
              {o.id === value && <Icon name="check" size={16} />}
            </button>
          ))}
          {options.length === 0 && <div className="dd-empty">Пока пусто</div>}
        </div>
      )}
    </div>
  );
}
