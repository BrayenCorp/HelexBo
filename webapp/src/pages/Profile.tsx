import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtShort, nf, tokensText } from "../format";
import { Icon } from "../icons";
import { Back, Dropdown, Hdr } from "../pf";
import { openExternal, tgPhoto } from "../telegram";
import type { Prefs } from "../types";
import { Avatar, Modal, Toggle, useLoad } from "../ui";

export const APP_VERSION = "1.0";

/** Профиль: кто вы, сколько создали и сколько токенов. Всё техническое — в настройках. */
export function Profile() {
  const { me, nav } = useApp();
  const q = useLoad(() => api.profile(), [me.balance]);
  const p = q.data;
  const sum = useLoad(() => api.tokens(), [me.balance]);
  return (
    <>
      <Hdr title="Профиль" />
      <div className="prof-card">
        <Avatar name={me.first_name} photo={tgPhoto} size={64} />
        <div className="prof-who">
          <b>{me.first_name ?? "Пользователь"}</b>
          <span>{me.username ? `@${me.username}` : "Telegram"}</span>
        </div>
        <button className="btn outline" onClick={() => nav.go({ name: "settings" })}><Icon name="settings" size={17} />Настройки</button>
      </div>

      <div className="kv">
        <div><b>{nf(me.balance)}</b><span>Токенов на балансе</span></div>
        <div><b>{nf(p?.generations ?? 0)}</b><span>Работ создано</span></div>
        <div><b>{nf(sum.data?.spent ?? 0)}</b><span>Токенов потрачено</span></div>
        <div><b>{fmtShort(me.created_at)}</b><span>С нами с</span></div>
      </div>

      <div className="pf-grid wide" style={{ gap: 10 }}>
        <button className="row-card" onClick={() => nav.go({ name: "balance" })}>
          <span className="rc-ic"><Icon name="coin" size={20} /></span><span className="grow"><b>Баланс и пополнение</b><span>Токены, пакеты, история</span></span><Icon name="chevron" size={18} />
        </button>
        <button className="row-card" onClick={() => nav.go({ name: "history" })}>
          <span className="rc-ic"><Icon name="clock" size={20} /></span><span className="grow"><b>Мои генерации</b><span>Все ваши работы</span></span><Icon name="chevron" size={18} />
        </button>
        {p?.support_url && (
          <button className="row-card" onClick={() => openExternal(p.support_url)}>
            <span className="rc-ic"><Icon name="help" size={20} /></span><span className="grow"><b>Поддержка</b><span>Написать нам</span></span><Icon name="chevron" size={18} />
          </button>
        )}
        {me.roles.length > 0 && (
          <button className="row-card" onClick={() => nav.go({ name: "admin" })}>
            <span className="rc-ic"><Icon name="chart" size={20} /></span><span className="grow"><b>Админ-центр</b><span>Управление проектом</span></span><Icon name="chevron" size={18} />
          </button>
        )}
      </div>
    </>
  );
}

/** Настройки: только то, что нужно обычному человеку. */
export function Settings() {
  const { me, nav, refreshMe } = useApp();
  const [prefs, setPrefs] = useState<Prefs>(me.prefs);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const sum = useLoad(() => api.tokens(), [me.balance]);
  const profile = useLoad(() => api.profile(), []);

  async function save(patch: Partial<Prefs>) {
    const prev = prefs;
    setPrefs({ ...prefs, ...patch } as Prefs);
    try { setPrefs(await api.savePrefs(patch)); refreshMe(); }
    catch (e) { setPrefs(prev); showToast(e instanceof ApiError ? e.message : "Не удалось сохранить"); }
  }
  async function wipe() {
    setBusy(true);
    try {
      const r = await api.deleteMyMedia();
      showToast(r.deleted_files ? "Работы, фото и аватары удалены" : "Удалять нечего");
      setConfirm(false); refreshMe();
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось удалить"); } finally { setBusy(false); }
  }

  const s = sum.data;
  return (
    <>
      <Back onClick={nav.back} />
      <Hdr title="Настройки" />

      <section className="set-group">
        <h2 className="set-title">Аккаунт</h2>
        <div className="set-rows">
          <div className="set-row"><span>Имя</span><b>{me.first_name ?? "—"}</b></div>
          <div className="set-row"><span>Username</span><b>{me.username ? `@${me.username}` : "—"}</b></div>
          <div className="set-row"><span>Вход</span><b>Telegram</b></div>
          <div className="set-row"><span>ID</span><b>{me.id}</b></div>
        </div>
      </section>

      <section className="set-group">
        <h2 className="set-title">Язык</h2>
        <Dropdown ariaLabel="Язык" value="ru" options={[{ id: "ru", label: "Русский" }]} onChange={() => undefined} disabled />
        <span className="hint">Другие языки появятся позже.</span>
      </section>

      <section className="set-group">
        <h2 className="set-title">Баланс</h2>
        <div className="set-rows">
          <div className="set-row"><span>Сейчас на счету</span><b>{tokensText(me.balance)}</b></div>
          <div className="set-row"><span>Куплено</span><b>{nf(s?.bought ?? 0)}</b></div>
          <div className="set-row"><span>Потрачено</span><b>{nf(s?.spent ?? 0)}</b></div>
          <div className="set-row"><span>Возвращено за ошибки</span><b>{nf(s?.refunded ?? 0)}</b></div>
        </div>
        <div className="comp-row">
          <button className="btn orange" onClick={() => nav.go({ name: "balance" })}>Пополнить</button>
          <button className="btn outline" onClick={() => nav.go({ name: "payments" })}>История пополнений</button>
        </div>
      </section>

      <section className="set-group">
        <h2 className="set-title">Уведомления</h2>
        <div className="sw-row">
          <div><b>Присылать готовые работы в чат</b><span className="hint">Результат придёт в чат с ботом — оттуда его удобно сохранить.</span></div>
          <Toggle checked={prefs.notify} onChange={(v) => save({ notify: v })} label="Уведомления о готовности" />
        </div>
      </section>

      <section className="set-group">
        <h2 className="set-title">Безопасность</h2>
        <p className="hint">Вход только через Telegram — пароль не нужен. Загруженные фото удаляются сразу после генерации; фото аватаров хранятся, пока вы их не удалите.</p>
        <button className="btn outline" style={{ alignSelf: "flex-start" }} onClick={() => setConfirm(true)}>
          <Icon name="trash" size={17} />Удалить мои работы и фото
        </button>
      </section>

      <section className="set-group">
        <h2 className="set-title">О приложении</h2>
        <div className="set-rows">
          <div className="set-row"><span>Версия</span><b>Nolla AI {APP_VERSION}</b></div>
          {profile.data?.support_url && <div className="set-row"><span>Поддержка</span><button className="link" onClick={() => openExternal(profile.data!.support_url)}>Написать</button></div>}
          <div className="set-row"><span>Условия использования</span><b className="muted">В разработке</b></div>
          <div className="set-row"><span>Политика конфиденциальности</span><b className="muted">В разработке</b></div>
        </div>
      </section>

      {confirm && (
        <Modal onClose={() => setConfirm(false)}>
          <h2>Удалить работы и фото?</h2>
          <p className="muted">Все готовые работы, загруженные фото и аватары будут удалены без возможности восстановления. Баланс и история пополнений сохранятся.</p>
          <button className="btn orange block" disabled={busy} onClick={wipe}>{busy ? "Удаляем…" : "Удалить"}</button>
          <button className="btn outline block" onClick={() => setConfirm(false)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
