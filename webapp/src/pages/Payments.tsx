import { api } from "../api";
import { useApp } from "../ctx";
import { fmtDate, tokensText } from "../format";
import { Empty, ErrorBox, Loading, PageHeader, useLoad } from "../ui";

export function Payments() {
  const { nav } = useApp();
  const q = useLoad(() => api.paymentsHistory(), []);
  return (
    <>
      <PageHeader title="История платежей" onBack={nav.back} />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && q.data.length === 0 && <Empty icon="sparkle" title="Платежей пока нет" text="Здесь появятся ваши пополнения." />}
      <ul className="list tight">
        {(q.data ?? []).map((p) => (
          <li key={p.id} className="hist">
            <span className="row-main"><b>{p.package}: {tokensText(p.credits + p.bonus)}</b>
              <span className="muted small">{fmtDate(p.paid_at ?? p.created_at)}{p.provider === "test" ? " · тестовая оплата" : ""}</span></span>
            <b>{p.provider === "test" ? "Тест" : p.currency === "RUB" ? `${p.amount} ₽` : `${p.amount_stars} ⭐`}</b>
          </li>
        ))}
      </ul>
    </>
  );
}
