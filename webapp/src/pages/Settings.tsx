import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { Icon } from "../icons";
import { Modal, PageHeader, Toggle } from "../ui";

export function Settings() {
  const { me, nav, refreshMe } = useApp();
  const [notify, setNotify] = useState(me.notify_chat);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  async function change(v: boolean) {
    setNotify(v);
    try { await api.setNotify(v); refreshMe(); }
    catch { setNotify(!v); showToast("Не удалось сохранить настройку"); }
  }
  async function wipe() {
    setBusy(true);
    try {
      const r = await api.deleteMyMedia();
      showToast(r.deleted_files ? "Ваши работы и фото удалены" : "Удалять нечего");
      setConfirm(false); refreshMe();
    } catch (e) { showToast(e instanceof ApiError ? e.message : "Не удалось удалить"); }
    finally { setBusy(false); }
  }

  return (
    <>
      <PageHeader title="Настройки" onBack={nav.back} />
      <div className="setting-row">
        <span className="row-main"><b>Присылать результат в чат</b><span className="muted small">Готовые фото и видео приходят в чат с ботом, чтобы их можно было сохранить в галерею.</span></span>
        <Toggle checked={notify} onChange={change} label="Присылать результат в чат" />
      </div>
      <div className="menu-list">
        <button onClick={() => nav.go({ name: "tokens" })}><Icon name="coin" size={20} /><span>Мои токены и пополнение</span><Icon name="chevron" size={16} /></button>
        <button onClick={() => nav.go({ name: "payments" })}><Icon name="card" size={20} /><span>История платежей</span><Icon name="chevron" size={16} /></button>
        <button className="danger" onClick={() => setConfirm(true)}><Icon name="trash" size={20} /><span>Удалить мои работы и фото</span></button>
      </div>
      {confirm && (
        <Modal onClose={() => setConfirm(false)}>
          <span className="modal-icon danger"><Icon name="trash" size={26} /></span>
          <h2>Удалить работы и фото?</h2>
          <p className="muted">Все ваши готовые работы и загруженные фото будут удалены без возможности восстановления. Баланс и история операций сохранятся.</p>
          <button className="btn danger block" disabled={busy} onClick={wipe}>{busy ? "Удаляем…" : "Удалить"}</button>
          <button className="btn outline block" onClick={() => setConfirm(false)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
