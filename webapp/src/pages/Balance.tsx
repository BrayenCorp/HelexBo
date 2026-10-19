import { useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { fmtDate, nf, tokensText } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { Back, Empty2, Hdr, Sec } from "../pf";
import { haptic } from "../telegram";
import type { Pack } from "../types";
import { ErrorBox, Loading, Modal, useLoad } from "../ui";

const METHODS: [string, string, string, IconName][] = [["card", "Карта", "Банковская карта", "card"], ["sbp", "СБП", "Система быстрых платежей", "bolt"], ["crypto", "Криптовалюта", "USDT и другие", "key"]];
const REASON: Record<string, string> = { purchase: "Покупка токенов", purchase_bonus: "Бонус к пакету", welcome_bonus: "Приветственный бонус", order_refund: "Возврат за ошибку", admin_adjust: "Корректировка", test_grant: "Начисление" };
const METHOD_NAME: Record<string, string> = { card: "Карта", sbp: "СБП", crypto: "Криптовалюта" };

export function Balance() {
  const { me, nav, refreshMe } = useApp();
  const packs = useLoad(() => api.packages(), []);
  const sum = useLoad(() => api.tokens(), [me.balance]);
  const ledger = useLoad(() => api.ledger(), [me.balance]);
  const [pick, setPick] = useState<Pack | null>(null);
  const [done, setDone] = useState<{ tokens: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const demo = me.modes.payments === "test";
  const list = (packs.data ?? []).filter((p) => ["start", "pro", "creator", "studio"].includes(p.id)).concat((packs.data ?? []).filter((p) => !["start", "pro", "creator", "studio"].includes(p.id)));

  async function pay(method: string) {
    if (!pick) return;
    setBusy(true); setError(null);
    try {
      const r = await api.demoPay(pick.id, method);
      setDone({ tokens: r.tokens }); setPick(null); haptic("success"); refreshMe();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Не удалось выполнить демо-платёж"); } finally { setBusy(false); }
  }
  const s = sum.data;
  const label = (r: { reason: string; kind: string | null }) => r.reason === "order_charge" ? (r.kind === "video" ? "Создание видео" : r.kind === "audio" ? "Создание аудио" : "Создание изображения") : REASON[r.reason] ?? r.reason;

  return (
    <>
      <Hdr title="Баланс" />
      <div className="bal-hero"><span className="pf-lead" style={{ fontSize: 13, letterSpacing: "0.08em", textTransform: "uppercase" }}>Ваш баланс</span><div className="big">{nf(me.balance)}</div><span className="muted">{tokensText(me.balance).split(" ").slice(1).join(" ")}</span></div>
      {s && <div className="kv"><div><b>{nf(s.bought)}</b><span>Куплено</span></div><div><b>{nf(s.spent)}</b><span>Потрачено</span></div><div><b>{nf(s.refunded)}</b><span>Возвращено</span></div><div><b>{nf(s.bonus)}</b><span>Бонусные</span></div></div>}

      <Sec title="Пополнить баланс">
        {demo && <div className="demo-note"><Icon name="info" size={18} /><span>Платежи работают в демо-режиме: деньги не списываются, токены начисляются для проверки. Реальные способы оплаты подключаются позже.</span></div>}
        {packs.loading && !packs.data && <Loading />}
        <div className="pk-grid">
          {list.map((p) => (
            <button key={p.id} className={`pk ${p.badge ? "hot" : ""}`} onClick={() => setPick(p)} disabled={!demo}>
              {p.badge && <span className="pf-badge w">{p.badge}</span>}
              <h3>{p.title}</h3><div className="n">{nf(p.credits)}</div>
              <span className="muted">токенов{p.bonus ? "" : ""}</span>
              {p.bonus > 0 && <span className="bonus">+ {nf(p.bonus)} в подарок</span>}
              <span className="pr">{p.price_rub ? `${nf(p.price_rub)} ₽` : `${nf(p.price_stars)} ⭐`} <span className="pf-badge" style={{ marginLeft: 4 }}>Демо</span></span>
            </button>
          ))}
        </div>
        {!demo && <Empty2 title="Оплата пока недоступна" text="Способы оплаты подключаются. Загляните позже." />}
      </Sec>

      <Sec title="История операций">
        {ledger.data && ledger.data.length === 0 && <Empty2 title="Операций пока нет" />}
        <div className="meta-table">
          {(ledger.data ?? []).slice(0, 20).map((r) => <div key={r.id}><span>{label(r)} · {fmtDate(r.created_at)}</span><b>{r.delta > 0 ? "+" : ""}{nf(r.delta)}</b></div>)}
        </div>
        <button className="btn outline" style={{ alignSelf: "flex-start" }} onClick={() => nav.go({ name: "payments" })}>История платежей</button>
      </Sec>

      {pick && (
        <Modal onClose={() => !busy && setPick(null)}>
          <h2>Выберите способ оплаты</h2>
          <p className="muted">{pick.title}: {tokensText(pick.credits + pick.bonus)}</p>
          {error && <ErrorBox message={error} />}
          {METHODS.map(([code, title, text, icon]) => (
            <button key={code} className="pay-opt" disabled={busy || code === "crypto"} onClick={() => pay(code)}>
              <Icon name={icon} size={22} /><span className="grow"><b>{title}</b><span>{text}</span></span>
              <span className="pf-badge">{code === "crypto" ? "Скоро" : "Демо"}</span>
            </button>
          ))}
          <button className="btn outline block" disabled={busy} onClick={() => setPick(null)}>Отмена</button>
        </Modal>
      )}
      {done && (
        <Modal onClose={() => setDone(null)}>
          <span className="modal-icon"><Icon name="check" size={26} /></span>
          <h2>Демо-платёж успешно выполнен</h2>
          <p className="muted">Токены зачислены: {tokensText(done.tokens)}. Реальные деньги не списывались.</p>
          <button className="btn orange block" onClick={() => setDone(null)}>Отлично</button>
        </Modal>
      )}
    </>
  );
}

export function Payments() {
  const { nav } = useApp();
  const q = useLoad(() => api.paymentsHistory(), []);
  return (
    <>
      <Back onClick={nav.back} />
      <Hdr title="История платежей" />
      {q.loading && !q.data && <Loading />}
      {q.error && <ErrorBox message={q.error} onRetry={q.reload} />}
      {q.data && q.data.length === 0 && <Empty2 title="Платежей пока нет" text="Здесь появятся ваши пополнения." />}
      <div className="meta-table">
        {(q.data ?? []).map((p) => (
          <div key={p.id}><span>{p.package}: {tokensText(p.credits + p.bonus)} · {fmtDate(p.paid_at ?? p.created_at)}</span>
            <b>{p.provider === "test" ? `Демо${p.demo_method ? ` · ${METHOD_NAME[p.demo_method] ?? p.demo_method}` : ""}` : p.currency === "RUB" ? `${p.amount} ₽` : `${p.amount_stars} ⭐`}</b></div>
        ))}
      </div>
    </>
  );
}

export function showBalanceToast() { showToast("Баланс обновлён"); }
