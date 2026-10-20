import type { ReactNode } from "react";
import { Icon } from "../icons";

export interface Col<T> { key: string; title: string; render?: (r: T) => ReactNode; num?: boolean; wrap?: boolean; sortable?: boolean }

export function DataTable<T extends object>({ cols, rows, onRow, empty = "Нет данных", sort, onSort }: { cols: Col<T>[]; rows: T[]; onRow?: (r: T) => void; empty?: string; sort?: { key: string; desc: boolean }; onSort?: (key: string) => void }) {
  return (
    <div className="table-wrap">
      <table className="tbl">
        <thead><tr>{cols.map((c) => (
          <th key={c.key} className={`${c.num ? "num" : ""} ${c.sortable && onSort ? "sortable" : ""}`}
            onClick={c.sortable && onSort ? () => onSort(c.key) : undefined}
            aria-sort={sort?.key === c.key ? (sort.desc ? "descending" : "ascending") : undefined}>
            {c.title}{sort?.key === c.key && <span className="sort-mark">{sort.desc ? "↓" : "↑"}</span>}
          </th>
        ))}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={onRow ? "click" : ""} onClick={() => onRow?.(r)}>
              {cols.map((c) => <td key={c.key} className={`${c.num ? "num" : ""} ${c.wrap ? "wrap" : ""}`}>{c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? "—")}</td>)}
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={cols.length} className="center muted" style={{ padding: 28 }}>{empty}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export function Pager({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="pager">
      <span>Всего: {total.toLocaleString("ru-RU")}</span>
      <div>
        <button className="btn ghost sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Назад"><Icon name="back" size={16} /></button>
        <span>Стр. {page} из {pages}</span>
        <button className="btn ghost sm" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Вперёд"><Icon name="chevron" size={16} /></button>
      </div>
    </div>
  );
}
