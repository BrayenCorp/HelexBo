import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { fmtDate, nf, plural, tokensText } from "../format";
import { Icon } from "../icons";
import type { IconName } from "../icons";
import { tgPhoto } from "../telegram";
import type { Landing } from "../types";
import { Avatar, Coin, Cover, ErrorBox, Loading, Mark, Section, Sheet, useLoad } from "../ui";

const CAP_ICONS: IconName[] = ["image", "video", "user", "palette", "camera", "flame", "edit", "wand"];

export function Home() {
  const { me, nav, ensureRegistered } = useApp();
  const q = useLoad(() => api.home(), []);
  const [workTab, setWorkTab] = useState("all");
  const [preview, setPreview] = useState<Landing["works"][number] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Не удалось загрузить главную"} onRetry={q.reload} />;
  const d = q.data;
  const c = d.content;
  const heroImage = d.banner.banner_image_url || d.works[0]?.media_url || "";
  const works = d.works.filter((w) => workTab === "all" || w.category === workTab);

  async function start(kind: "photo" | "video" = "photo", modelId?: number) {
    if (await ensureRegistered()) nav.go({ name: "generate", kind, modelId });
  }
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  const chooseAction = (a: Landing["chooser"][number]["action"]) => {
    if (a.type === "category" && a.id) nav.go({ name: "category", id: a.id });
    else void start(a.kind ?? "photo", a.model_id);
  };

  return (
    <>
      <section className="hero">
        <Cover url={heroImage} seed={2} className="hero-bg" />
        <div className="hero-body">
          <span className="eyebrow">Nolla AI</span>
          <h2>{c.hero.title}</h2>
          <p>{c.hero.text}</p>
          <div className="hero-actions">
            <button className="btn orange" onClick={() => start()}>{c.hero.primary} <Icon name="chevron" size={16} /></button>
            <button className="btn ghost" onClick={() => scrollTo("why")}>{c.hero.secondary}</button>
          </div>
        </div>
      </section>

      {!me.registered ? (
        <div className="login-card">
          <h3>Войдите в Nolla AI</h3>
          <p className="muted small">Вход через Telegram: без паролей, почты и телефона. Аккаунт создаётся автоматически.</p>
          <button className="btn black block" onClick={() => ensureRegistered()}><Icon name="send" size={18} /> Продолжить через Telegram</button>
        </div>
      ) : (
        <div className="balance-card">
          <Avatar name={me.first_name} photo={tgPhoto} size={44} />
          <span className="row-main"><span>Привет, {me.username ? `@${me.username}` : me.first_name ?? "друг"} 👋</span><b>{tokensText(me.balance)}</b></span>
          <span className="bc-actions">
            <button className="btn orange sm" onClick={() => start()}>Создать</button>
            <button className="btn ghost sm" style={{ color: "#fff", borderColor: "#55554f" }} onClick={() => nav.go({ name: "shop" })}>Пополнить баланс</button>
          </span>
        </div>
      )}

      <Section title="Что умеет Nolla AI?">
        <div className="cap-grid">
          {c.capabilities.map((x, i) => (
            <div key={x.title} className="cap-card"><span className="cap-icon"><Icon name={CAP_ICONS[i % CAP_ICONS.length]} size={20} /></span><b>{x.title}</b><span>{x.text}</span></div>
          ))}
        </div>
      </Section>

      {d.models.length > 0 && (
        <Section title="Какие AI-модели мы используем?">
          {d.models.map((m) => (
            <div key={m.id} className="model-card">
              <div className="model-img"><Cover url={m.image_url} seed={m.id} /></div>
              <div className="model-body">
                <h3>{m.name}</h3>
                <p className="muted">{m.description}</p>
                {m.purpose && <div className="tag-list"><span className="tag dark">{m.purpose}</span></div>}
                {m.audience.length > 0 && (<><span className="small muted">Кому подходит:</span><div className="tag-list">{m.audience.map((a) => <span key={a} className="tag">{a}</span>)}</div></>)}
                <div className="price-row"><Coin size={14} /><b>от {tokensText(m.price_credits)}</b></div>
                <button className="btn black sm" onClick={() => start(m.kind, m.id)}>Попробовать</button>
              </div>
            </div>
          ))}
        </Section>
      )}

      {d.chooser.length > 0 && (
        <div className="choose">
          <h3>Не знаете, какую модель выбрать?</h3>
          <p className="muted small">Nolla AI поможет: выберите, что хотите получить.</p>
          {d.chooser.map((x) => (
            <button key={x.title} className="choose-item" onClick={() => chooseAction(x.action)}><span>{x.title}</span><Icon name="chevron" size={16} /></button>
          ))}
        </div>
      )}

      {d.trends.length > 0 && (
        <Section title="Сейчас в тренде">
          <div className="rail">
            {d.trends.map((t) => (
              <div key={t.id} className="trend-card">
                <div className="trend-img"><Cover url={t.preview_url} seed={t.id} />{t.kind === "video" && <span className="play-dot"><Icon name="play" size={12} /></span>}</div>
                <b>{t.title}</b>
                <span className="muted">{t.uses > 0 ? `${nf(t.uses)} ${plural(t.uses, ["использование", "использования", "использований"])}` : "Новый тренд"}</span>
                <button className="btn orange sm" onClick={() => nav.go({ name: "template", id: t.id })}>Попробовать</button>
              </div>
            ))}
          </div>
        </Section>
      )}

      {d.works.length > 0 && (
        <Section title="Что уже создают в Nolla AI">
          <div className="work-tabs">
            <button className={`chip ${workTab === "all" ? "on" : ""}`} onClick={() => setWorkTab("all")}>Все</button>
            {d.work_categories.map((x) => <button key={x.id} className={`chip ${workTab === x.id ? "on" : ""}`} onClick={() => setWorkTab(x.id)}>{x.title}</button>)}
          </div>
          <div className="work-grid">
            {works.map((w) => (
              <button key={w.id} className="work" onClick={() => setPreview(w)}>
                <Cover url={w.media_url} seed={w.id.length} />{w.kind === "video" && <span className="play-dot"><Icon name="play" size={12} /></span>}
              </button>
            ))}
          </div>
        </Section>
      )}

      <Section title="Как это работает">
        <div className="steps">
          {c.steps.map((x, i) => (<div key={x.title} className="step-card"><span className="step-num">{String(i + 1).padStart(2, "0")}</span><b>{x.title}</b>{x.text && <span className="muted small">{x.text}</span>}</div>))}
        </div>
      </Section>

      <Section title={c.tokens.title}>
        <div className="token-box">
          <p>{c.tokens.text}</p>
          <div>
            {d.price_from.photo !== undefined && <div className="cost-row"><span>Фото</span><b>от {tokensText(d.price_from.photo)}</b></div>}
            {d.price_from.video !== undefined && <div className="cost-row"><span>Видео</span><b>от {tokensText(d.price_from.video)}</b></div>}
          </div>
          <span className="small" style={{ color: "#bdbcb6" }}>Точная стоимость показывается перед созданием. Первое фото и первое видео бесплатны.</span>
        </div>
        {d.packages.length > 0 && (
          <div className="pack-row">
            {d.packages.map((p) => (
              <div key={p.id} className={`pack ${p.badge ? "has-badge" : ""}`}>
                {p.badge && <span className="pack-badge">{p.badge}</span>}
                <b className="pack-num">{nf(p.credits)}</b><span className="muted small">{plural(p.credits, ["токен", "токена", "токенов"])}</span>
                {p.bonus > 0 && <span className="pack-bonus">+{nf(p.bonus)} в подарок</span>}
                <span className="pack-price">{p.old_price_stars && <s>{p.old_price_stars}</s>}{p.price_stars} ⭐</span>
              </div>
            ))}
          </div>
        )}
        <button className="btn black block" onClick={() => nav.go({ name: "shop" })}>Купить токены</button>
      </Section>

      {(d.methods.available.length > 0 || d.methods.soon.length > 0) && (
        <Section title={c.payment.title}>
          <p className="muted small">{c.payment.text}</p>
          <div className="pay-methods">
            {d.methods.available.map((m) => (<div key={m.code} className="pay-method"><span className="cap-icon"><Icon name="card" size={18} /></span><span className="row-main"><b>{m.title}</b><span className="muted small">{m.description}</span></span></div>))}
            {d.methods.soon.map((m) => (<div key={m.code} className="pay-method"><span className="cap-icon"><Icon name="card" size={18} /></span><span className="row-main"><b>{m.title}</b></span><span className="soon">Скоро</span></div>))}
          </div>
        </Section>
      )}

      <section id="why" className="section">
        <div className="section-head"><h2>Почему Nolla AI</h2></div>
        <div className="why-list">
          {c.why.map((x, i) => (<div key={x.title} className="why-item"><span className="cap-icon"><Icon name={(["layers", "bolt", "refresh", "coin", "send"] as IconName[])[i % 5]} size={20} /></span><span><b>{x.title}</b><span className="muted">{x.text}</span></span></div>))}
        </div>
      </section>

      <div className="about-block"><h2>{c.about.title}</h2><p>{c.about.text}</p></div>

      {d.faq.length > 0 && (
        <Section title="Частые вопросы">
          {d.faq.map((f) => (
            <div key={f.id} className={`faq-item ${open === f.id ? "open" : ""}`}>
              <button className="faq-q" aria-expanded={open === f.id} onClick={() => setOpen(open === f.id ? null : f.id)}><span>{f.question}</span><Icon name="chevron-down" size={18} /></button>
              {open === f.id && <div className="faq-a">{f.answer}</div>}
            </div>
          ))}
        </Section>
      )}

      <div className="cta-final">
        <Mark size={36} /><h2>{c.cta.title}</h2><p>{c.cta.text}</p>
        <button className="btn" onClick={() => start()}>{c.cta.button} <Icon name="chevron" size={16} /></button>
      </div>
      <p className="muted small center">Nolla AI · {fmtDate(new Date().toISOString())}</p>

      {preview && (
        <Sheet title={preview.title || "Работа"} onClose={() => setPreview(null)}>
          <div className="preview-media"><Cover url={preview.media_url} seed={3} />{preview.kind === "video" && <span className="play-dot big"><Icon name="play" size={18} /></span>}</div>
          {preview.prompt && <p className="muted small">{preview.prompt}</p>}
          <button className="btn orange block" onClick={async () => {
            const w = preview;
            setPreview(null);
            if (await ensureRegistered()) nav.go({ name: "generate", kind: w.kind, templateId: w.template_id ?? undefined, prompt: w.prompt || undefined });
          }}><Mark size={18} mono /> Создать похожее</button>
        </Sheet>
      )}
    </>
  );
}

