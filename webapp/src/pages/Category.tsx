import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Chips, ErrorBox, Loading, PageHeader, StyleCard, useLoad } from "../ui";

export function Category({ id }: { id: string }) {
  const { nav } = useApp();
  const [label, setLabel] = useState("all");
  const cat = useLoad(() => api.category(id), [id]);
  const list = useLoad(() => api.templates({ category: id }), [id]);
  if (cat.loading && !cat.data) return <Loading />;
  if (cat.error || !cat.data) return <ErrorBox message={cat.error ?? "Категория не найдена"} onRetry={cat.reload} />;
  const items = list.data ?? [];
  const labels = [...new Set(items.map((t) => t.style_label).filter(Boolean))];
  const shown = label === "all" ? items : items.filter((t) => t.style_label === label);

  return (
    <>
      <PageHeader title={cat.data.title} onBack={nav.back} />
      {cat.data.description && <p className="muted">{cat.data.description}</p>}
      {labels.length > 0 && (
        <Chips value={label} onChange={setLabel} options={[["all", "Все"], ...labels.map((l): [string, string] => [l, l])]} />
      )}
      {list.loading && !list.data && <Loading />}
      {list.error && <ErrorBox message={list.error} onRetry={list.reload} />}
      {list.data && shown.length === 0 && <p className="muted center pad">Здесь пока нет примеров. Загляните позже.</p>}
      <div className="grid2">
        {shown.map((t, i) => <StyleCard key={t.id} t={t} tall={i % 3 === 0} onOpen={() => nav.go({ name: "template", id: t.id })} />)}
      </div>
    </>
  );
}
