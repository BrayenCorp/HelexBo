import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import { tokensText } from "../format";
import { Coin, Cover, ErrorBox, Loading, Mark, PageHeader, useLoad } from "../ui";

/** Пример стиля: просмотр и кнопка «Создать похожее» → генератор с выбранным стилем. */
export function TemplatePage({ id }: { id: number }) {
  const { me, nav } = useApp();
  const q = useLoad(() => api.template(id), [id]);
  if (q.loading && !q.data) return <Loading />;
  if (q.error || !q.data) return <ErrorBox message={q.error ?? "Пример не найден"} onRetry={q.reload} />;
  const t = q.data;
  const free = me.free[t.kind];

  return (
    <>
      <PageHeader title="Пример" onBack={nav.back} />
      <div className="detail-media">
        <Cover url={t.preview_url} seed={t.id} />
        {t.kind === "video" && <span className="play-dot big"><Icon name="play" size={18} /></span>}
      </div>
      <div>
        <h1 className="h1">{t.title}</h1>
        {t.style_label && <span className="tag">{t.style_label}</span>}
      </div>
      {t.description && <p className="muted">{t.description}</p>}
      <div className="info-row">
        <span className="info-icon"><Icon name={t.kind === "photo" ? "image" : "film"} size={18} /></span>
        <b>{t.kind === "photo" ? "Фото" : "Видео"}</b>
        <span className="price-row"><Coin size={16} />{free ? <b className="gold-text">Бесплатно</b> : <b>{tokensText(t.price_credits)}</b>}</span>
      </div>
      {t.examples.length > 0 && (
        <section className="section">
          <h2 className="sub-title">Ещё примеры</h2>
          <div className="rail">
            {t.examples.map((e, i) => <span key={i} className="thumb static"><Cover url={e.url} seed={i} /></span>)}
          </div>
        </section>
      )}
      <div className="cta-bar">
        <button className="btn orange block" onClick={() => nav.go({ name: "generate", kind: t.kind, templateId: t.id })}><Mark size={18} mono /> Создать похожее</button>
      </div>
    </>
  );
}
