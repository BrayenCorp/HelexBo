import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { Logo } from "../ui";

export type PeriodKey = "today" | "yesterday" | "7d" | "30d" | "90d" | "year" | "custom";
export interface Period { key: PeriodKey; start: string; end: string }

const PERIODS: [PeriodKey, string][] = [["today", "Сегодня"], ["yesterday", "Вчера"], ["7d", "7 дней"], ["30d", "30 дней"], ["90d", "90 дней"], ["year", "Этот год"], ["custom", "Произвольный"]];
const today = () => new Date().toISOString().slice(0, 10);

interface PeriodState { period: Period; setPeriod: (p: Period) => void }
const PeriodCtx = createContext<PeriodState>({ period: { key: "30d", start: "", end: "" }, setPeriod: () => undefined });
export const usePeriod = () => useContext(PeriodCtx);
/** Параметры периода для запросов к серверу. */
export const pq = (p: Period): string => `period=${p.key}${p.key === "custom" ? `&start=${p.start}&end=${p.end}` : ""}`;

interface Item { page: string; title: string; icon: IconName; roles: ("owner" | "developer")[]; period?: boolean }
export const ITEMS: Item[] = [
  { page: "home", title: "Главная", icon: "home", roles: ["owner"], period: true },
  { page: "analytics", title: "Аналитика", icon: "chart", roles: ["owner"], period: true },
  { page: "users", title: "Пользователи", icon: "users", roles: ["owner"] },
  { page: "activity", title: "Активность пользователей", icon: "clock", roles: ["owner"], period: true },
  { page: "generations", title: "Генерации", icon: "sparkle", roles: ["owner", "developer"] },
  { page: "content", title: "Контент", icon: "layers", roles: ["owner"] },
  { page: "categories", title: "Категории", icon: "grid", roles: ["owner"] },
  { page: "templates", title: "Шаблоны", icon: "image", roles: ["owner"] },
  { page: "trends", title: "Тренды", icon: "flame", roles: ["owner"] },
  { page: "payments", title: "Платежи", icon: "card", roles: ["owner"] },
  { page: "revenue", title: "Выручка", icon: "coin", roles: ["owner"], period: true },
  { page: "tokens", title: "Токены", icon: "diamond", roles: ["owner"], period: true },
  { page: "subscriptions", title: "Подписки", icon: "crown", roles: ["owner"], period: true },
  { page: "referrals", title: "Реферальная система", icon: "share", roles: ["owner"] },
  { page: "marketing", title: "Маркетинг", icon: "tag", roles: ["owner"] },
  { page: "errors", title: "Ошибки и журналы", icon: "bug", roles: ["owner", "developer"] },
  { page: "providers", title: "AI-провайдеры", icon: "bolt", roles: ["owner", "developer"], period: true },
  { page: "system", title: "Система", icon: "shield", roles: ["owner", "developer"] },
  { page: "settings", title: "Настройки", icon: "settings", roles: ["owner"] },
];
const PARENT: Record<string, string> = { user: "users", template: "templates", category: "categories", package: "tokens" };

export function PeriodBar() {
  const { period, setPeriod } = usePeriod();
  return (
    <div className="period">
      {PERIODS.map(([k, label]) => (
        <button key={k} className={`chip ${period.key === k ? "on" : ""}`} onClick={() => setPeriod({ key: k, start: period.start || today(), end: period.end || today() })}>{label}</button>
      ))}
      {period.key === "custom" && (
        <>
          <input type="date" value={period.start} max={period.end} onChange={(e) => setPeriod({ ...period, start: e.target.value })} aria-label="Начало периода" />
          <span className="muted">—</span>
          <input type="date" value={period.end} min={period.start} max={today()} onChange={(e) => setPeriod({ ...period, end: e.target.value })} aria-label="Конец периода" />
        </>
      )}
    </div>
  );
}

/** Каркас админ-центра: боковое меню (на телефоне — выезжающее), заголовок, период. */
export function AdminShell({ page, children }: { page: string; children: ReactNode }) {
  const { me, nav } = useApp();
  const [open, setOpen] = useState(false);
  const [period, setPeriod] = useState<Period>({ key: "30d", start: "", end: "" });
  const roles = me.roles;
  const items = ITEMS.filter((i) => i.roles.some((r) => roles.includes(r)));
  const current = ITEMS.find((i) => i.page === (PARENT[page] ?? page)) ?? ITEMS[0];
  const go = (p: string) => { setOpen(false); nav.reset({ name: "admin", page: p }); };
  return (
    <PeriodCtx.Provider value={{ period, setPeriod }}>
      <div className="adm">
        <div className={`adm-scrim ${open ? "open" : ""}`} onClick={() => setOpen(false)} />
        <aside className={`adm-side ${open ? "open" : ""}`}>
          <div className="adm-brand"><Logo /><small>Центр аналитики и управления</small></div>
          <nav className="adm-nav" aria-label="Разделы админки">
            {items.map((i) => (
              <button key={i.page} className={`adm-link ${current.page === i.page ? "on" : ""}`} onClick={() => go(i.page)}><Icon name={i.icon} size={18} />{i.title}</button>
            ))}
          </nav>
          <div className="adm-foot">
            <div className="adm-user"><span className="avatar" style={{ width: 34, height: 34 }}>{(me.first_name ?? "A")[0]}</span>
              <span><b>{me.username ? `@${me.username}` : me.first_name}</b><span>{roles.includes("owner") ? "Владелец" : "Разработчик"} · ID {me.id}</span></span></div>
            <button className="btn sm" onClick={() => nav.reset({ name: "home" })}><Icon name="logout" size={16} /> Выйти из админки</button>
          </div>
        </aside>
        <div className="adm-main">
          <header className="adm-top">
            <button className="adm-burger" onClick={() => setOpen(true)} aria-label="Меню"><Icon name="menu" size={20} /></button>
            <h1>{current.title}</h1>
            {current.period && PARENT[page] === undefined && <PeriodBar />}
          </header>
          <main className="adm-content">{children}</main>
        </div>
      </div>
    </PeriodCtx.Provider>
  );
}
