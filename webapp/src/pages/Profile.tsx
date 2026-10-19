import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { tokensText } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { Back, Hdr, Sec } from "../pf";
import { openExternal, tgPhoto } from "../telegram";
import type { Prefs, Route } from "../types";
import { Avatar, Modal, Toggle, useLoad } from "../ui";

const INTERESTS: [string, string][] = [["photo", "Фото"], ["video", "Видео"], ["avatars", "Аватары"], ["social", "Контент для соцсетей"], ["ads", "Реклама"], ["other", "Другое"]];

export function Profile() {
  const { me, nav } = useApp();
  const q = useLoad(() => api.profile(), [me.balance]);
  const p = q.data;
  const row = (icon: IconName, title: string, text: string, to: Route) => (
    <button className="row-card" onClick={() => nav.go(to)}><span className="rc-ic"><Icon name={icon} size={20} /></span><span className="grow"><b>{title}</b><span>{text}</span></span><Icon name="chevron" size={18} /></button>
  );
  return (
    <>
      <Hdr title="Профиль" />
      <div className="row-card" style={{ cursor: "default" }}>
        <Avatar name={me.first_name} photo={tgPhoto} size={56} />
        <span className="grow"><b style={{ fontSize: 18 }}>{me.first_name ?? "Пользователь"}</b><span>{me.username ? `@${me.username}` : "Telegram"}</span></span>
      </div>
      <div className="kv">
        <div><b>{p?.generations ?? "—"}</b><span>Работ создано</span></div>
        <div><b>{tokensText(me.balance).split(" ")[0]}</b><span>Токенов на балансе</span></div>
      </div>
      <div className="pf-grid wide" style={{ gap: 10 }}>
        {row("settings", "Настройки", "Язык, модель по умолчанию, уведомления", { name: "settings" })}
        {row("shield", "Безопасность", "Ваши данные и удаление файлов", { name: "security" })}
        {row("coin", "Баланс", "Токены и пополнение", { name: "balance" })}
        {row("card", "История платежей", "Все пополнения", { name: "payments" })}
        {row("plug", "Интеграции", "ChatGPT, Claude, Cursor и другие через MCP", { name: "integrations" })}
        {p?.support_url && <button className="row-card" onClick={() => openExternal(p.support_url)}><span className="rc-ic"><Icon name="help" size={20} /></span><span className="grow"><b>Поддержка</b><span>Написать нам</span></span><Icon name="chevron" size={18} /></button>}
        {me.roles.length > 0 && row("chart", "Админ-центр", "Управление платформой", { name: "admin" })}
      </div>
    </>
  );
}

export function Settings() {
  const { me, nav, refreshMe } = useApp();
  const models = useLoad(() => api.models("photo"), []);
  const [prefs, setPrefs] = useState<Prefs>(me.prefs);
  async function save(patch: Partial<Prefs> & { clear_model?: boolean }) {
    const prev = prefs;
    setPrefs({ ...prefs, ...patch } as Prefs);
    try { setPrefs(await api.savePrefs(patch)); refreshMe(); } catch (e) { setPrefs(prev); showToast(e instanceof ApiError ? e.message : "Не удалось сохранить"); }
  }
  return (
    <>
      <Back onClick={nav.back} />
      <Hdr title="Настройки" />
      <div className="panel">
        <div className="fld"><label htmlFor="lg">Язык</label><select id="lg" value="ru" disabled><option value="ru">Русский</option></select><span className="hint">Другие языки появятся позже.</span></div>
        <div className="fld"><label htmlFor="dm">Модель по умолчанию</label>
          <select id="dm" value={prefs.default_model_id ?? ""} onChange={(e) => save(e.target.value ? { default_model_id: Number(e.target.value) } : { clear_model: true, default_model_id: null })}>
            <option value="">Выбирать автоматически</option>
            {(models.data ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select></div>
        <div className="fld-row">
          <div className="fld"><label htmlFor="rt">Соотношение сторон</label>
            <select id="rt" value={prefs.ratio} onChange={(e) => save({ ratio: e.target.value })}>{["1:1", "3:4", "4:3", "9:16", "16:9", "21:9"].map((r) => <option key={r}>{r}</option>)}</select></div>
          <div className="fld"><label htmlFor="ql">Качество</label>
            <select id="ql" value={prefs.quality} onChange={(e) => save({ quality: e.target.value })}><option value="standard">Стандарт</option><option value="high">Высокое</option></select></div>
        </div>
        <div className="fld"><span className="lbl">Мои интересы</span>
          <div className="pill-row">{INTERESTS.map(([k, l]) => <button key={k} className={`pill ${prefs.interests.includes(k) ? "on" : ""}`} onClick={() => save({ interests: prefs.interests.includes(k) ? prefs.interests.filter((x) => x !== k) : [...prefs.interests, k] })}>{l}</button>)}</div></div>
        <div className="sw-row"><div><b>Присылать результат в чат</b><span className="hint">Готовые работы приходят в чат с ботом.</span></div><Toggle checked={prefs.notify} onChange={(v) => save({ notify: v })} label="Уведомления в чат" /></div>
        <div className="sw-row"><div><b>Скачивать автоматически</b><span className="hint">Готовый результат сразу сохраняется на устройство.</span></div><Toggle checked={prefs.autodownload} onChange={(v) => save({ autodownload: v })} label="Автоскачивание" /></div>
      </div>
    </>
  );
}

export function Security() {
  const { nav, refreshMe } = useApp();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  async function wipe() {
    setBusy(true);
    try {
      const r = await api.deleteMyMedia();
      showToast(r.deleted_files ? "Ваши работы, фото и аватары удалены" : "Удалять нечего");
      setConfirm(false); refreshMe();
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось удалить"); } finally { setBusy(false); }
  }
  return (
    <>
      <Back onClick={nav.back} />
      <Hdr title="Безопасность" text="Вход выполняется через Telegram — пароли не нужны." />
      <Sec title="Ваши данные">
        <div className="panel">
          <p className="hint" style={{ fontSize: 14 }}>Загруженные фото используются только для вашей генерации и удаляются после её завершения. Фото аватаров хранятся, пока вы сами не удалите аватар.</p>
          <p className="hint" style={{ fontSize: 14 }}>Доступ к платформе из внешних приложений (MCP) защищён личными токенами — их можно отозвать в разделе «Интеграции».</p>
          <button className="btn outline" onClick={() => nav.go({ name: "integrations" })}><Icon name="key" size={17} />Мои токены доступа</button>
          <button className="btn outline" onClick={() => setConfirm(true)}><Icon name="trash" size={17} />Удалить мои работы, фото и аватары</button>
        </div>
      </Sec>
      {confirm && (
        <Modal onClose={() => setConfirm(false)}>
          <h2>Удалить работы и фото?</h2>
          <p className="muted">Все готовые работы, загруженные фото и аватары будут удалены без возможности восстановления. Баланс и история платежей сохранятся.</p>
          <button className="btn orange block" disabled={busy} onClick={wipe}>{busy ? "Удаляем…" : "Удалить"}</button>
          <button className="btn outline block" onClick={() => setConfirm(false)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
