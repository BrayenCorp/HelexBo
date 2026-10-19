import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtTime } from "../format";
import { Icon } from "../icons";
import { Hdr, Sec } from "../pf";
import { ErrorBox, Loading, Modal, useLoad } from "../ui";

export function Integrations() {
  const { nav } = useApp();
  const q = useLoad(() => api.integrations(), []);
  const [label, setLabel] = useState("");
  const [fresh, setFresh] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const d = q.data;
  const copy = (t: string) => navigator.clipboard?.writeText(t).then(() => showToast("Скопировано"), () => showToast("Не удалось скопировать"));
  async function create() {
    setError(null);
    try { const r = await api.createToken(label.trim()); setFresh(r.token); setLabel(""); q.reload(); } catch (e) { setError(e instanceof ApiError ? e.message : "Не удалось создать токен"); }
  }
  async function revoke(id: number) { try { await api.revokeToken(id); showToast("Токен отозван"); q.reload(); } catch { showToast("Не удалось отозвать"); } }
  return (
    <>
      <button className="pf-back" onClick={nav.back}><Icon name="back" size={18} />Назад</button>
      <Hdr title="Интеграции" text="Подключите ChatGPT, Claude, Cursor или Codex к Nolla AI через MCP — и создавайте прямо из любимого инструмента." />
      {q.loading && !d && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {d && (
        <>
          <Sec title="Адрес MCP-сервера">
            <div className="codebox">{d.endpoint.startsWith("http") ? d.endpoint : `${window.location.origin}${d.endpoint}`}</div>
            <button className="btn outline" style={{ alignSelf: "flex-start" }} onClick={() => copy(d.endpoint.startsWith("http") ? d.endpoint : `${window.location.origin}${d.endpoint}`)}><Icon name="copy" size={16} />Скопировать адрес</button>
            <p className="hint">Передавайте токен в заголовке <code>Authorization: Bearer &lt;токен&gt;</code>. Токены хранятся только в виде хеша.</p>
          </Sec>
          <Sec title="Как подключить">
            <div className="pf-grid wide">{d.clients.map((c) => <div key={c.name} className="panel"><b>{c.name}</b><p className="hint" style={{ fontSize: 13.5 }}>{c.how}</p></div>)}</div>
          </Sec>
          <Sec title="Доступные инструменты">
            <div className="pf-grid wide">{d.tools.map((t) => <div key={t.name} className="row-card"><span className="rc-ic"><Icon name="wand" size={18} /></span><span className="grow"><b>{t.title}</b><span>{t.description}</span><code style={{ color: "var(--muted)" }}>{t.name}</code></span></div>)}</div>
          </Sec>
          <Sec title="Мои токены доступа">
            <div className="panel">
              <div className="fld"><label htmlFor="tl">Название (например, Cursor)</label><input id="tl" maxLength={40} value={label} onChange={(e) => setLabel(e.target.value)} /></div>
              {error && <div className="notice bad"><p>{error}</p></div>}
              <button className="btn orange" style={{ alignSelf: "flex-start" }} onClick={create}><Icon name="key" size={17} />Создать токен</button>
              {d.tokens.length === 0 && <p className="hint">Токенов пока нет. Максимум — 5 активных.</p>}
              <div className="meta-table">{d.tokens.map((t) => (
                <div key={t.id}><span>{t.label || "Без названия"} · {fmtTime(t.created_at)}{t.last_used_at ? ` · использован ${fmtTime(t.last_used_at)}` : ""}</span><button className="btn outline sm" onClick={() => revoke(t.id)}>Отозвать</button></div>
              ))}</div>
            </div>
          </Sec>
        </>
      )}
      {fresh && (
        <Modal onClose={() => setFresh(null)}>
          <h2>Ваш токен</h2>
          <p className="muted">Сохраните его сейчас — повторно мы его не покажем.</p>
          <div className="codebox">{fresh}</div>
          <button className="btn orange block" onClick={() => copy(fresh)}>Скопировать</button>
          <button className="btn outline block" onClick={() => setFresh(null)}>Готово</button>
        </Modal>
      )}
    </>
  );
}
