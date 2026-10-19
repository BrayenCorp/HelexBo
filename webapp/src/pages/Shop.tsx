import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { nf, plural, tokensText } from "../format";
import { Icon } from "../icons";
import { haptic, tg } from "../telegram";
import type { Pack } from "../types";
import { Coin, ErrorBox, Loading, PageHeader, Sheet, useLoad } from "../ui";

/** Купить токены: пакеты → способ оплаты → оплата. Показываются только реально подключённые способы; остальные — «Скоро». */
export function Shop() {
  const { me, nav, refreshMe } = useApp();
  const packs = useLoad(() => api.packages(), []);
  const methods = useLoad(() => api.paymentMethods(), []);
  const [pick, setPick] = useState<Pack | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function waitForBalance(before: number) {
    for (let i = 0; i < 10; i++) { // зачисление Stars приходит от бота — ждём несколько секунд
      await new Promise((r) => setTimeout(r, 1500));
      if ((await api.me()).balance > before) break;
    }
    refreshMe();
  }

  async function pay(pack: Pack, method: string) {
    setBusy(true); setError(null);
    try {
      const p = await api.startPayment(pack.id, method);
      if (p.mode === "test") {
        const r = await api.testConfirm(p.payload);
        showToast(`Тестовая оплата прошла. Баланс: ${tokensText(r.balance)}`);
        haptic("success");
        setPick(null); refreshMe();
      } else if (p.invoice_link && tg) {
        const before = me.balance;
        setPick(null);
        tg.openInvoice(p.invoice_link, (status) => {
          if (status === "paid") { showToast("Оплата получена, начисляем токены…"); void waitForBalance(before); }
          else if (status === "failed") setError("Оплата не прошла. Попробуйте ещё раз.");
        });
      } else setError("Оплата Telegram Stars доступна только внутри Telegram.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось начать оплату.");
    } finally { setBusy(false); }
  }

  const m = methods.data;
  const none = m && m.available.length === 0;

  return (
    <>
      <PageHeader title="Купить токены" onBack={nav.back} />
      <div className="balance-card"><Coin size={26} /><span className="row-main"><span className="muted">Ваш баланс</span><b>{tokensText(me.balance)}</b></span>
        <button className="btn ghost sm" style={{ color: "#fff", borderColor: "#55554f" }} onClick={() => nav.go({ name: "tokens" })}>История</button></div>
      {me.modes.payments === "test" && <div className="notice warn"><p><b>Тестовая оплата.</b> Реальные деньги не списываются.</p></div>}
      {none && <div className="notice"><p>Оплата пока недоступна. Загляните позже.</p></div>}
      {error && <ErrorBox message={error} />}
      {(packs.loading || methods.loading) && !packs.data && <Loading />}
      {packs.error && <ErrorBox message={packs.error} onRetry={packs.reload} />}
      <div className="list">
        {(packs.data ?? []).map((p) => (
          <button key={p.id} className="row-card" style={p.badge ? { borderColor: "#ff6a00", borderWidth: 2 } : undefined} disabled={none ?? false} onClick={() => setPick(p)}>
            <span className="cap-icon"><Icon name="coin" size={20} /></span>
            <span className="row-main"><b>{p.title} · {nf(p.credits)} {plural(p.credits, ["токен", "токена", "токенов"])}</b>
              <span className="small muted">{p.bonus > 0 ? `+${nf(p.bonus)} в подарок` : "Без бонуса"}{p.badge ? ` · ${p.badge}` : ""}</span></span>
            <b>{p.old_price_stars ? <s className="muted" style={{ fontWeight: 400, marginRight: 4 }}>{p.old_price_stars}</s> : null}{p.price_stars} ⭐</b>
          </button>
        ))}
      </div>
      {m && m.available.length > 0 && <p className="muted small">Способы оплаты: {m.available.map((x) => x.title).join(", ")}{m.soon.length ? `. Скоро: ${m.soon.map((x) => x.title).join(", ")}` : ""}.</p>}

      {pick && m && (
        <Sheet title="Выберите способ оплаты" onClose={() => setPick(null)}>
          <p className="muted small">{pick.title}: {tokensText(pick.credits + pick.bonus)} за {pick.price_stars} ⭐</p>
          <div className="pay-methods">
            {m.available.map((x) => (
              <button key={x.code} className="pay-method pick" disabled={busy} onClick={() => pay(pick, x.code)}>
                <span className="cap-icon"><Icon name="card" size={18} /></span><span className="row-main"><b>{x.title}</b><span className="muted small">{x.description}</span></span><Icon name="chevron" size={16} />
              </button>
            ))}
            {m.soon.map((x) => (<div key={x.code} className="pay-method"><span className="cap-icon"><Icon name="card" size={18} /></span><span className="row-main"><b>{x.title}</b></span><span className="soon">Скоро</span></div>))}
          </div>
        </Sheet>
      )}
    </>
  );
}
