import { api } from "../api";
import { useApp } from "../ctx";
import { tokensText } from "../format";
import { Icon } from "../icons";
import { Mark } from "../ui";

/** Показывается один раз после первого входа. */
export function Welcome() {
  const { me, nav, refreshMe } = useApp();
  async function go() {
    await api.welcomed().catch(() => undefined);
    refreshMe();
    nav.reset({ name: "generate", kind: "photo" });
  }
  return (
    <div className="welcome" role="dialog" aria-modal>
      <Mark size={64} />
      <h1>Добро пожаловать в Nolla AI</h1>
      <p className="muted">Твой аккаунт создан.</p>
      <div className="big-bonus"><small>Твой баланс</small>{tokensText(me.balance)}</div>
      {me.welcome_bonus > 0 && <p className="muted small">Включая стартовый бонус: {tokensText(me.welcome_bonus)}.</p>}
      <p className="muted small">Первое фото и первое видео — бесплатно.</p>
      <button className="btn orange big block" onClick={go}>Перейти к созданию <Icon name="chevron" size={18} /></button>
    </div>
  );
}
