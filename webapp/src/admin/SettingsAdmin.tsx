import { useEffect, useState } from "react";
import { api } from "../api";
import { showToast } from "../ctx";
import { fmtTime } from "../format";
import { ErrorBox, Loading, useLoad } from "../ui";
import { Card, Field, TextInput, errText } from "./kit";
import { ExportButton } from "./parts";
import { DataTable, Pager } from "./table";

interface Audit { items: { id: number; ts: string; admin_name: string; action: string; target: string; before: Record<string, unknown>; after: Record<string, unknown>; note: string }[]; total: number }
interface Config { owners: number[]; developers: number[]; star_usd_rate: number; ai_mode: string; payments_mode: string; bot_username: string; webapp_url: string; event_dictionary: Record<string, string>; derived_events: Record<string, string> }

const EXPORTS: [string, string][] = [["users", "Пользователи"], ["generations", "Генерации"], ["payments", "Платежи"], ["revenue", "Выручка по дням"], ["tokens", "Операции с токенами"], ["referrals", "Рефералы"], ["analytics", "Аналитика по дням (90 дней)"]];
const diff = (a: Record<string, unknown>, b: Record<string, unknown>) => Object.keys(b).filter((k) => a[k] !== b[k]).map((k) => `${k}: ${String(a[k])} → ${String(b[k])}`).join("; ") || "—";

export function SettingsAdmin() {
  const [tab, setTab] = useState<"main" | "audit" | "export" | "access">("main");
  const st = useLoad(() => api.admin.get<{ support_url: string; ideas_channel_url: string; referral_bonus: string }>("settings"), []);
  const cfg = useLoad(() => api.admin.get<Config>("config"), []);
  const [page, setPage] = useState(1);
  const audit = useLoad(() => api.admin.get<Audit>(`audit?page=${page}`), [page]);
  const [support, setSupport] = useState("");
  const [channel, setChannel] = useState("");
  const [refBonus, setRefBonus] = useState("");
  useEffect(() => {
    setSupport(st.data?.support_url ?? "");
    setChannel(st.data?.ideas_channel_url ?? "");
    setRefBonus(st.data?.referral_bonus ?? "");
  }, [st.data]);
  async function save() {
    try { await api.admin.send("PUT", "settings", { support_url: support, ideas_channel_url: channel, referral_bonus: refBonus }); showToast("Сохранено"); st.reload(); }
    catch (e) { showToast(errText(e, "Не удалось сохранить")); }
  }
  return (
    <>
      <div className="tabs-line">
        {([["main", "Основное"], ["audit", "Журнал действий администраторов"], ["export", "Экспорт"], ["access", "Доступ и события"]] as const).map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}
      </div>
      {tab === "main" && (
        <Card title="Основные настройки">
          <Field label="Ссылка «Помощь и поддержка»" hint="Например, https://t.me/ваш_аккаунт"><TextInput value={support} onChange={setSupport} placeholder="https://t.me/…" /></Field>
          <Field label="Канал с идеями и промптами" hint="Кнопка «Посмотреть идеи» в боте ведёт сюда. Пусто — бот покажет идеи прямо в чате."><TextInput value={channel} onChange={setChannel} placeholder="https://t.me/ваш_канал" /></Field>
          <Field label="Токенов за приглашённого друга" hint="Начисляются пригласившему, когда друг впервые входит. 0 — программа выключена."><TextInput value={refBonus} onChange={setRefBonus} placeholder="20" /></Field>
          {cfg.data && <div className="kpi-rows">
            <div className="kpi-row"><span className="muted">Режим AI</span><b>{cfg.data.ai_mode === "mock" ? "Тестовый (заглушки)" : "Рабочий"}</b></div>
            <div className="kpi-row"><span className="muted">Режим оплаты</span><b>{{ test: "Тестовая", stars: "Telegram Stars", off: "Отключена" }[cfg.data.payments_mode] ?? cfg.data.payments_mode}</b></div>
            <div className="kpi-row"><span className="muted">Курс Stars → USD (оценка выручки)</span><b>{cfg.data.star_usd_rate}</b></div>
            <div className="kpi-row"><span className="muted">Бот</span><b>{cfg.data.bot_username ? `@${cfg.data.bot_username}` : "—"}</b></div>
          </div>}
          <p className="muted small">Режимы и курс задаются в файле .env на сервере. Стартовый бонус токенов и число вариантов — в разделе «Токены».</p>
          <button className="btn orange sm" onClick={save}>Сохранить</button>
        </Card>
      )}
      {tab === "audit" && (audit.data ? (
        <>
          <DataTable rows={audit.data.items} empty="Действий пока не было" cols={[
            { key: "ts", title: "Когда", render: (a) => fmtTime(a.ts) }, { key: "admin_name", title: "Кто" },
            { key: "action", title: "Что сделал", wrap: true, render: (a) => <b>{a.action}</b> }, { key: "target", title: "Над кем" },
            { key: "before", title: "Было → стало", wrap: true, render: (a) => diff(a.before, a.after) }, { key: "note", title: "Комментарий", wrap: true },
          ]} />
          <Pager page={page} size={30} total={audit.data.total} onPage={setPage} />
        </>
      ) : audit.error ? <ErrorBox message={audit.error} onRetry={audit.reload} /> : <Loading />)}
      {tab === "export" && (
        <Card title="Экспорт данных" hint="CSV в кодировке UTF-8: открывается в Excel с кириллицей">
          <div className="action-grid">{EXPORTS.map(([k, l]) => <ExportButton key={k} kind={k} label={l} />)}</div>
          <p className="muted small">В Telegram файл присылается в личный чат с ботом, в браузере скачивается сразу.</p>
        </Card>
      )}
      {tab === "access" && cfg.data && (
        <>
          <Card title="Кто имеет доступ к админ-центру" hint="Список задаётся в .env: OWNER_IDS и DEVELOPER_IDS">
            <div className="kpi-rows"><div className="kpi-row"><span className="muted">Владельцы (ID)</span><b>{cfg.data.owners.join(", ") || "—"}</b></div><div className="kpi-row"><span className="muted">Разработчики (ID)</span><b>{cfg.data.developers.join(", ") || "—"}</b></div></div>
          </Card>
          <Card title="Какие события собирает система" hint="События бота и Mini App пишутся в отдельную таблицу, остальные считаются из заказов, платежей и журнала токенов">
            <div className="kpi-rows">
              {Object.entries(cfg.data.event_dictionary).map(([k, v]) => <div key={k} className="kpi-row"><span className="muted">{k}</span><b>{v}</b></div>)}
              {Object.entries(cfg.data.derived_events).map(([k, v]) => <div key={k} className="kpi-row"><span className="muted">{k}</span><b>{v}</b></div>)}
            </div>
          </Card>
        </>
      )}
    </>
  );
}
