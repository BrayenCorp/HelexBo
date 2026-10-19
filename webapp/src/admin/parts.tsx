import type { ReactNode } from "react";
import { api } from "../api";
import { showToast } from "../ctx";
import { ago, nf } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { tg } from "../telegram";
import { errText } from "./kit";

export interface Overview {
  period: { start: string; end: string };
  users: { total: number; new: number; active: number; returned: number };
  generations: { total: number; photo: number; video: number; success: number; errors: number; processing: number };
  money: { revenue_stars: number; revenue_usd_estimate: number; purchases: number; today: number; d7: number; d30: number; avg_check: number; other_currencies: { currency: string; amount: number; n: number }[] };
  tokens: { sold: number; spent: number; refunded: number; bonus: number; balance_total: number };
  subscriptions: { free: number; pro: number; granted: number; cancelled: number };
}
export interface SeriesData {
  days: string[]; users_new: number[]; users_active: number[]; users_returned: number[]; revenue: number[]; purchases: number[]; avg_check: number[];
  photo: number[]; video: number[]; generations: number[]; tokens_bought: number[]; tokens_spent: number[]; tokens_refunded: number[];
}
export interface ActivityItem { ts: string; type: string; user_id: number | null; user: string; text: string; amount: number | null }

export const TYPE_ICON: Record<string, IconName> = { registration: "user", photo: "image", video: "video", error: "bug", started: "clock", purchase: "coin", pro: "crown", admin: "shield" };
export const TYPE_LABEL: Record<string, string> = { registration: "Регистрация", photo: "Фото", video: "Видео", error: "Ошибка", started: "Запуск", purchase: "Покупка", pro: "PRO", admin: "Админ" };

export function Kpi({ title, big, bigLabel, rows, orange = false }: { title: string; big: ReactNode; bigLabel?: string; rows: [string, ReactNode][]; orange?: boolean }) {
  return (
    <div className="kpi-group">
      <h3>{title}</h3>
      <div><div className={`kpi-big ${orange ? "orange" : ""}`}>{big}</div>{bigLabel && <span className="muted small">{bigLabel}</span>}</div>
      <div className="kpi-rows">{rows.map(([k, v]) => <div key={k} className="kpi-row"><span className="muted">{k}</span><b>{v}</b></div>)}</div>
    </div>
  );
}

export function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return <div className="chart-card"><h3>{title}</h3>{children}</div>;
}

export function ActivityFeed({ items, onUser }: { items: ActivityItem[]; onUser?: (id: number) => void }) {
  if (!items.length) return <p className="muted center pad">Активности пока нет.</p>;
  return (
    <div className="feed">
      {items.map((a, i) => (
        <div key={i} className="feed-item">
          <span className={`feed-dot ${a.type === "error" ? "error" : a.type === "purchase" ? "purchase" : ""}`}><Icon name={TYPE_ICON[a.type] ?? "sparkle"} size={16} /></span>
          <span className="row-main">
            <span style={{ color: "var(--ink)", fontSize: 14 }}>
              {a.user_id && onUser && a.type !== "admin" ? <button className="link" onClick={() => onUser(a.user_id!)}>{a.user}</button> : <b>{a.user}</b>} {a.text}
            </span>
            <span>{TYPE_LABEL[a.type] ?? a.type} · {ago(a.ts)}</span>
          </span>
          {a.amount !== null && <span className="feed-amount">{a.amount > 0 ? "+" : ""}{nf(a.amount)} ток.</span>}
        </div>
      ))}
    </div>
  );
}

/** Скачать CSV: в Telegram файлы из Mini App неудобны, поэтому там файл присылается в чат с ботом. */
export function ExportButton({ kind, label = "Экспорт CSV" }: { kind: string; label?: string }) {
  async function run() {
    try {
      if (tg) { await api.admin.sendExport(kind); showToast("Файл отправлен в чат с ботом"); return; }
      const blob = await api.admin.download(kind);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `nolla-${kind}.csv`;
      a.click();
    } catch (e) { showToast(errText(e, "Не удалось выгрузить")); }
  }
  return <button className="btn outline sm" onClick={run}><Icon name="download" size={16} /> {label}</button>;
}

export const stateLabel = (s: string) => (s === "ok" ? "Работает" : s === "warn" ? "Предупреждение" : "Ошибка");
