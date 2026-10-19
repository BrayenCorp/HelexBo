import { useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api";
import { showToast, useApp } from "../ctx";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { openExternal, tgPhoto } from "../telegram";
import { tokensText } from "../format";
import { Avatar, Coin, Modal, ProBadge, useLoad } from "../ui";

function Tile({ icon, label, onClick }: { icon: IconName; label: string; onClick: () => void }) {
  return (
    <button className="menu-tile" onClick={onClick}><Icon name={icon} size={20} /><span>{label}</span><Icon name="chevron" size={16} /></button>
  );
}

export function Profile() {
  const { me, nav } = useApp();
  const p = useLoad(() => api.profile(), [me.balance, me.favorites.orders.length]);
  const [modal, setModal] = useState<ReactNode | null>(null);
  const prof = p.data;
  const closeBtn = <button className="btn orange block" onClick={() => setModal(null)}>Понятно</button>;

  function help() {
    if (prof?.support_url) return openExternal(prof.support_url);
    setModal(<><span className="modal-icon"><Icon name="help" size={26} /></span><h2>Помощь</h2>
      <p className="muted">Контакт поддержки пока не указан. Напишите администратору бота в Telegram.</p>{closeBtn}</>);
  }
  function pro() {
    setModal(<><span className="modal-icon"><Icon name="crown" size={26} /></span><h2>{me.is_pro ? "Тариф PRO" : "Тариф PRO"}</h2>
      <p className="muted">{me.is_pro ? "Тариф PRO назначен вам администратором. Управление подпиской появится позже." : "Подписка PRO скоро появится. Мы сообщим, когда она станет доступна."}</p>{closeBtn}</>);
  }

  return (
    <>
      <div className="home-top">
        <span />
        <button className="round-icon" onClick={() => nav.go({ name: "settings" })} aria-label="Настройки"><Icon name="settings" size={20} /></button>
      </div>

      <div className="profile-head">
        <span className="avatar-ring"><Avatar name={me.first_name} photo={tgPhoto} size={76} /></span>
        <span className="row-main">
          <span className="profile-name"><b>{me.username ? `@${me.username}` : me.first_name ?? "Гость"}</b>{me.is_pro ? <ProBadge /> : <span className="free-badge">Free</span>}</span>
          <span className="muted small">ID: {me.id}</span>
        </span>
      </div>

      <div className="stats3">
        <div><b>{prof?.generations ?? "—"}</b><span>Генераций</span></div>
        <div><b>{prof?.images ?? "—"}</b><span>Изображений</span></div>
        <div><b>{prof?.videos ?? "—"}</b><span>Видео</span></div>
      </div>

      <div className="tariff">
        <span className="tariff-icon"><Icon name="crown" size={24} /></span>
        <span className="row-main">
          <b>Ваш тариф: {me.is_pro ? "PRO" : "Free"}</b>
          <span className="muted small">{me.is_pro ? "Больше возможностей для ваших идей" : "Откройте больше возможностей с PRO"}</span>
        </span>
        <button className="btn orange sm" onClick={pro}>{me.is_pro ? "Управление" : "Перейти на PRO"}</button>
      </div>

      <button className="balance-row" onClick={() => nav.go({ name: "tokens" })}>
        <Coin size={22} /><span className="row-main"><b>{tokensText(me.balance)}</b><span className="muted small">Мои токены · история · пополнение</span></span><Icon name="chevron" size={18} />
      </button>

      <div className="menu-grid">
        <Tile icon="clock" label="История генераций" onClick={() => nav.reset({ name: "history" })} />
        <Tile icon="heart" label="Избранное" onClick={() => nav.reset({ name: "history", filter: "fav" })} />
        <Tile icon="settings" label="Настройки" onClick={() => nav.go({ name: "settings" })} />
        <Tile icon="help" label="Помощь" onClick={help} />
        <Tile icon="info" label="О нас" onClick={() => nav.go({ name: "about" })} />
        {me.ref_link && <Tile icon="share" label="Пригласить друзей" onClick={() => { navigator.clipboard?.writeText(me.ref_link).then(() => showToast("Ссылка скопирована"), () => showToast(me.ref_link)); }} />}
        {me.roles.length > 0 && <Tile icon="shield" label="Админ-панель" onClick={() => nav.go({ name: "admin" })} />}
      </div>

      {modal && <Modal onClose={() => setModal(null)}>{modal}</Modal>}
    </>
  );
}
