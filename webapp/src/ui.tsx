import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { useApp } from "./ctx";
import { tokensText } from "./format";
import type { Template } from "./types";

export function useLoad<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    setLoading(true);
    fn()
      .then((d) => { setData(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(reload, [reload]);
  return { data, error, loading, reload };
}

export function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Фирменный знак Nolla AI: оранжевая искра и чёрная точка. */
export function Mark({ size = 28, mono = false }: { size?: number; mono?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" aria-hidden>
      <path d="M58 16 C61.5 44 75 57.5 104 61 C75 64.5 61.5 78 58 106 C54.5 78 41 64.5 12 61 C41 57.5 54.5 44 58 16Z" fill={mono ? "currentColor" : "#FF6A00"} />
      <circle cx="96" cy="24" r="6" fill={mono ? "currentColor" : "#111111"} />
    </svg>
  );
}

export function Logo({ subtitle }: { subtitle?: string }) {
  return (
    <span className="logo">
      <Mark size={34} />
      <span className="logo-text"><b>Nolla AI</b>{subtitle && <span>{subtitle}</span>}</span>
    </span>
  );
}

export function ProBadge() {
  return <span className="pro-badge">PRO</span>;
}

/** Баланс в верхней полосе: нажатие открывает «Мои токены». */
export function BalanceChip({ balance, onClick }: { balance: number; onClick: () => void }) {
  return <button className="balance-chip" onClick={onClick} aria-label="Мои токены"><Coin size={14} />{tokensText(balance)}</button>;
}

export function Coin({ size = 16 }: { size?: number }) {
  return <span className="coin" style={{ width: size, height: size }} aria-hidden />;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`skeleton ${className}`} aria-hidden />;
}

export function Loading({ text = "Загружаем…" }: { text?: string }) {
  return (
    <div className="loading" role="status" aria-label={text}>
      <Skeleton className="sk-line" /><Skeleton className="sk-block" /><Skeleton className="sk-line short" />
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice bad" role="alert">
      <p>{message}</p>
      {onRetry && <button className="btn ghost sm" onClick={onRetry}>Повторить</button>}
    </div>
  );
}

export function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|mov)$/i.test(url.split("?")[0]);
}

/** Фото или видео. Если файла нет — графитовый градиент с искрой. */
export function Cover({ url, seed = 0, className = "" }: { url?: string | null; seed?: number; className?: string }) {
  const tone = `tone-${Math.abs(seed) % 5}`;
  if (!url) return <span className={`cover ${tone} ${className}`}><span className="cover-mark"><Mark size={46} /></span></span>;
  if (isVideoUrl(url)) return <span className={`cover ${tone} ${className}`}><video src={url} autoPlay muted loop playsInline preload="metadata" /></span>;
  return <span className={`cover ${tone} ${className}`}><img src={url} alt="" loading="lazy" /></span>;
}

/** Картинка/видео результата с авторизацией (запрашивается blob-ссылкой). */
export function AuthMedia({ orderId, mime, className = "", fallback, controls = true }: { orderId: number; mime: string | null; className?: string; fallback?: string; controls?: boolean }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    let objectUrl: string | null = null;
    api.resultBlob(orderId)
      .then((b) => { if (alive) { objectUrl = URL.createObjectURL(b); setUrl(objectUrl); } })
      .catch(() => alive && setFailed(true));
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [orderId]);
  if (failed) return <Cover url={fallback} seed={orderId} className={className} />;
  if (!url) return <Skeleton className={`sk-fill ${className}`} />;
  if (mime?.startsWith("video/")) return <video className={className} src={url} controls={controls} playsInline autoPlay loop muted />;
  return <img className={className} src={url} alt="Результат" />;
}

export function Heart({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button className={`heart ${on ? "on" : ""}`} aria-label={on ? "Убрать из избранного" : "В избранное"} aria-pressed={on}
      onClick={(e) => { e.stopPropagation(); onClick(); }}>
      <Icon name="heart" size={16} fill={on} />
    </button>
  );
}

export function formatDuration(sec: number | null | undefined): string {
  const s = Math.max(0, sec ?? 0);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

/** Карточка стиля/примера: крупное фото, название внизу. */
export function StyleCard({ t, onOpen, tall = false }: { t: Template; onOpen: () => void; tall?: boolean }) {
  return (
    <button className={`scard ${tall ? "tall" : ""}`} onClick={onOpen}>
      <Cover url={t.preview_url} seed={t.id} />
      {t.kind === "video" && <span className="play-dot"><Icon name="play" size={12} /></span>}
      <span className="scard-info">
        <b>{t.title}</b>
        {t.description && <span>{t.description}</span>}
      </span>
    </button>
  );
}

export function Thumb({ url, seed, label, onOpen, video = false }: { url: string; seed: number; label?: string; onOpen: () => void; video?: boolean }) {
  return (
    <button className="thumb" onClick={onOpen}>
      <Cover url={url} seed={seed} />
      {video && <span className="play-dot"><Icon name="play" size={12} /></span>}
      {label && <span className="thumb-title">{label}</span>}
    </button>
  );
}

export function PageHeader({ title, onBack, right, backLabel }: { title: string; onBack?: () => void; right?: ReactNode; backLabel?: string }) {
  return (
    <div className="page-head">
      {onBack && <button className="back-btn" onClick={onBack} aria-label="Назад"><Icon name="back" size={20} />{backLabel && <span>{backLabel}</span>}</button>}
      <h1 className={`page-title ${onBack ? "" : "left"}`}>{title}</h1>
      <span className="page-head-right">{right}</span>
    </div>
  );
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: [T, string, IconName?][]; onChange: (v: T) => void }) {
  return (
    <div className="segmented" role="tablist">
      {options.map(([v, label, icon]) => (
        <button key={v} role="tab" aria-selected={v === value} className={v === value ? "on" : ""} onClick={() => onChange(v)}>
          {icon && <Icon name={icon} size={16} />}{label}
        </button>
      ))}
    </div>
  );
}

export function Chips<T extends string>({ value, options, onChange, compact = false }: { value: T; options: [T, string, IconName?][]; onChange: (v: T) => void; compact?: boolean }) {
  return (
    <div className={`chips ${compact ? "compact" : ""}`}>
      {options.map(([v, label, icon]) => (
        <button key={v} className={`chip ${v === value ? "on" : ""}`} onClick={() => onChange(v)}>
          {icon && <Icon name={icon} size={15} />}{label}
        </button>
      ))}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} className={`switch ${checked ? "on" : ""}`}
      onClick={(e) => { e.stopPropagation(); onChange(!checked); }}><span /></button>
  );
}

export function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div className="overlay center-o" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  );
}

export function Sheet({ title, children, onClose }: { title?: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal onClick={(e) => e.stopPropagation()}>
        <div className="sheet-grab" />
        <div className="sheet-head"><b>{title}</b><button className="icon-plain" onClick={onClose} aria-label="Закрыть"><Icon name="close" size={20} /></button></div>
        {children}
      </div>
    </div>
  );
}

export function Section({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="section">
      <div className="section-head"><h2>{title}</h2>{action}</div>
      {children}
    </section>
  );
}

export function SeeAll({ onClick }: { onClick: () => void }) {
  return <button className="link" onClick={onClick}>Все <Icon name="chevron" size={14} /></button>;
}

export function Empty({ icon, title, text, action }: { icon: IconName; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <span className="empty-icon"><Icon name={icon} size={28} /></span>
      <b>{title}</b>
      {text && <span className="muted">{text}</span>}
      {action}
    </div>
  );
}

export function Avatar({ name, photo, size = 40 }: { name?: string | null; photo?: string; size?: number }) {
  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.4 }}>
      {photo ? <img src={photo} alt="" /> : (name?.[0] ?? "N").toUpperCase()}
    </span>
  );
}

/** Иконка категории по её идентификатору; для своих категорий — искра. */
export function categoryIcon(id: string): IconName {
  const map: Record<string, IconName> = { trends: "flame", men: "man", women: "woman", kids: "child", family: "family", "ai-video": "film" };
  return map[id] ?? "sparkle";
}

export function useGoBackOr(): () => void {
  const { nav } = useApp();
  return nav.back;
}
