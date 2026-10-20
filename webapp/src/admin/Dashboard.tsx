import type { ReactNode } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { fmtTime, nf } from "../format";
import { ErrorBox, Loading, useLoad } from "../ui";
import { DataTable } from "./table";

interface Recent {
  id: number; user: string; user_id: number; action: string; model: string | null; where: string;
  status: string; cost: number; created_at: string; prompt: string; template: string | null;
}
interface Dash {
  users: { total: number; today: number; d7: number; d30: number; active_today: number; active_d7: number; from_bot: number; from_app: number };
  generations: { total: number; today: number; week: number; month: number; photo: number; video: number; audio: number; done: number; in_progress: number };
  tokens: { spent_total: number; spent_today: number; spent_month: number; bought_total: number; balance_total: number; refunded_total: number };
  errors: { generation_total: number; generation_today: number; api_total: number; api_today: number; last: { created_at: string; source: string; message: string; error_type: string | null }[] };
  recent: Recent[];
}

const STATUS: Record<string, string> = { done: "Готово", failed: "Ошибка", processing: "Создаётся", created: "В очереди" };

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <b className="metric-value">{value}</b>
      {sub && <span className="metric-sub">{sub}</span>}
    </div>
  );
}

function Block({ title, children, note }: { title: string; children: ReactNode; note?: string }) {
  return (
    <section className="adm-block">
      <div className="adm-block-head"><h2>{title}</h2>{note && <span className="muted small">{note}</span>}</div>
      <div className="metric-row">{children}</div>
    </section>
  );
}

/** Главная админки. Все числа берутся из базы; если данных нет — будет ноль, а не выдуманное значение. */
export function Dashboard() {
  const { nav } = useApp();
  const q = useLoad(() => api.admin.get<Dash>("dashboard"), []);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Не удалось загрузить данные"} onRetry={q.reload} />;
  const d = q.data;
  return (
    <>
      <Block title="Пользователи" note={`из бота: ${nf(d.users.from_bot)} · из приложения: ${nf(d.users.from_app)}`}>
        <Metric label="Всего" value={nf(d.users.total)} />
        <Metric label="Сегодня" value={nf(d.users.today)} sub="новых" />
        <Metric label="За 7 дней" value={nf(d.users.d7)} sub="новых" />
        <Metric label="За 30 дней" value={nf(d.users.d30)} sub="новых" />
        <Metric label="Активны сегодня" value={nf(d.users.active_today)} sub={`за неделю ${nf(d.users.active_d7)}`} />
      </Block>

      <Block title="Генерации" note={d.generations.in_progress ? `в работе: ${nf(d.generations.in_progress)}` : undefined}>
        <Metric label="Всего" value={nf(d.generations.total)} sub={`готово ${nf(d.generations.done)}`} />
        <Metric label="Сегодня" value={nf(d.generations.today)} />
        <Metric label="За неделю" value={nf(d.generations.week)} />
        <Metric label="За месяц" value={nf(d.generations.month)} />
        <Metric label="Изображения" value={nf(d.generations.photo)} />
        <Metric label="Видео" value={nf(d.generations.video)} />
        <Metric label="Аудио" value={nf(d.generations.audio)} />
      </Block>

      <Block title="Токены">
        <Metric label="Потрачено всего" value={nf(d.tokens.spent_total)} />
        <Metric label="Сегодня" value={nf(d.tokens.spent_today)} />
        <Metric label="За месяц" value={nf(d.tokens.spent_month)} />
        <Metric label="Куплено" value={nf(d.tokens.bought_total)} />
        <Metric label="Остаток у пользователей" value={nf(d.tokens.balance_total)} sub={`возвращено ${nf(d.tokens.refunded_total)}`} />
      </Block>

      <Block title="Ошибки">
        <Metric label="Ошибки генерации" value={nf(d.errors.generation_total)} sub={`сегодня ${nf(d.errors.generation_today)}`} />
        <Metric label="Ошибки сервера" value={nf(d.errors.api_total)} sub={`сегодня ${nf(d.errors.api_today)}`} />
      </Block>

      {d.errors.last.length > 0 && (
        <div className="card">
          <div className="card-head"><h2>Последние ошибки</h2><button className="link" onClick={() => nav.reset({ name: "admin", page: "errors" })}>Все ошибки</button></div>
          <ul className="list tight">
            {d.errors.last.map((e, i) => (
              <li key={i} className="err-row"><span className="row-main"><b>{e.message}</b><span className="muted small">{e.source}{e.error_type ? ` · ${e.error_type}` : ""} · {fmtTime(e.created_at)}</span></span></li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <div className="card-head"><h2>Последние действия</h2><button className="link" onClick={() => nav.reset({ name: "admin", page: "generations" })}>Все генерации</button></div>
        <DataTable rows={d.recent} empty="Пока никто ничего не создавал" onRow={(r) => nav.go({ name: "admin", page: "user", id: String(r.user_id) })} cols={[
          { key: "user", title: "Пользователь", render: (r) => <b>{r.user}</b> },
          { key: "action", title: "Действие", render: (r) => <>{r.action}{r.template ? ` · ${r.template}` : ""}</> },
          { key: "model", title: "Модель", render: (r) => r.model ?? "—" },
          { key: "where", title: "Откуда" },
          { key: "cost", title: "Токены", num: true, render: (r) => (r.cost ? nf(r.cost) : "бесплатно") },
          { key: "created_at", title: "Дата", render: (r) => fmtTime(r.created_at) },
          { key: "status", title: "Статус", render: (r) => <span className={`status ${r.status === "failed" ? "failed" : r.status === "done" ? "" : "processing"}`}>{STATUS[r.status] ?? r.status}</span> },
        ]} />
      </div>
    </>
  );
}
