import { api } from "../api";
import { useApp } from "../ctx";
import { fmtDate, nf, tokensText } from "../format";
import { Icon } from "../icons";
import { Coin, ErrorBox, Loading, PageHeader, Section, useLoad } from "../ui";

const REASON: Record<string, string> = {
  purchase: "Покупка", purchase_bonus: "Бонус к пакету", welcome_bonus: "Стартовый бонус", order_refund: "Возврат за ошибку",
  admin_adjust: "Корректировка администратором", test_grant: "Начисление",
};

/** «Мои токены»: баланс, куплено, потрачено, возвращено, бонусные, история операций. */
export function Tokens() {
  const { me, nav } = useApp();
  const sum = useLoad(() => api.tokens(), [me.balance]);
  const ledger = useLoad(() => api.ledger(), [me.balance]);
  const s = sum.data;
  const label = (r: { reason: string; kind: "photo" | "video" | null }) =>
    r.reason === "order_charge" ? (r.kind === "video" ? "Создание видео" : "Генерация изображения") : REASON[r.reason] ?? r.reason;
  return (
    <>
      <PageHeader title="Мои токены" onBack={nav.back} />
      <div className="balance-card"><Coin size={30} /><span className="row-main"><span className="muted">Текущий баланс</span><b>{tokensText(me.balance)}</b></span>
        <button className="btn orange sm" onClick={() => nav.go({ name: "shop" })}>Пополнить</button></div>
      {sum.error && <ErrorBox message={sum.error} onRetry={sum.reload} />}
      {s && (
        <div className="token-stats">
          <div className="stat-tile"><span className="muted small">Куплено</span><b>{nf(s.bought)}</b></div>
          <div className="stat-tile"><span className="muted small">Потрачено</span><b>{nf(s.spent)}</b></div>
          <div className="stat-tile"><span className="muted small">Возвращено</span><b>{nf(s.refunded)}</b></div>
          <div className="stat-tile"><span className="muted small">Бонусные</span><b>{nf(s.bonus)}</b></div>
        </div>
      )}
      <Section title="История операций">
        {ledger.loading && !ledger.data && <Loading />}
        {ledger.data && ledger.data.length === 0 && <p className="muted small">Операций пока нет.</p>}
        <ul className="list tight">
          {(ledger.data ?? []).map((r) => (
            <li key={r.id} className="hist boxed">
              <span className="hist-icon"><Icon name={r.delta > 0 ? "plus" : "sparkle"} size={16} /></span>
              <span className="row-main"><b>{label(r)}</b><span className="muted small">{fmtDate(r.created_at)}{r.note ? ` · ${r.note}` : ""}</span></span>
              <span className={r.delta > 0 ? "plus" : "minus"}>{r.delta > 0 ? "+" : ""}{nf(r.delta)}</span>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}
