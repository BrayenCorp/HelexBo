import { useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import { Back, Empty2, Hdr, ModelTile, Skeletons, Tabs } from "../pf";
import type { AiModel, Kind } from "../types";
import { Modal, useLoad } from "../ui";

export function Models({ kind }: { kind?: Kind }) {
  const { nav } = useApp();
  const [k, setK] = useState<Kind>(kind ?? "photo");
  const [tag, setTag] = useState("all");
  const [open, setOpen] = useState<AiModel | null>(null);
  const meta = useLoad(() => api.meta(), []);
  const q = useLoad(() => api.models(k), [k]);
  const tags = (meta.data?.models[k]?.tags ?? []).filter((t) => t.count > 0);
  const list = (q.data ?? []).filter((m) => tag === "all" || m.tags?.includes(tag));
  return (
    <>
      <Hdr title="Модели" text="Лучшие AI-модели для изображений, видео и звука. Названия — оригинальные, описания ориентировочные." />
      <div className="pf-seg" style={{ alignSelf: "flex-start" }}>
        {([["photo", "Изображения"], ["video", "Видео"], ["audio", "Аудио"]] as const).map(([v, l]) => <button key={v} className={k === v ? "on" : ""} onClick={() => { setK(v); setTag("all"); }}>{l}</button>)}
      </div>
      <Tabs value={tag} onChange={setTag} items={[{ id: "all", label: "Все", count: q.data?.length }, ...tags.map((t) => ({ id: t.id, label: t.label, count: t.count }))]} />
      {q.loading && !q.data && <Skeletons n={6} />}
      {q.data && list.length === 0 && <Empty2 title="Моделей в этой категории нет" />}
      <div className="pf-grid wide">{list.map((m) => <ModelTile key={m.id} m={m} onPick={() => setOpen(m)} />)}</div>
      {open && (
        <Modal onClose={() => setOpen(null)}>
          <h2>{open.name}</h2>
          <p className="muted">{open.description}</p>
          {open.purpose && <div className="meta-table"><div><span>Назначение</span><b>{open.purpose}</b></div>{open.audience.length > 0 && <div><span>Для кого</span><b>{open.audience.join(", ")}</b></div>}<div><span>Стоимость</span><b>{open.price_credits} токенов</b></div></div>}
          {open.needs_image && <p className="hint"><Icon name="info" size={14} /> Нужно исходное изображение.</p>}
          {open.text_only && <p className="hint"><Icon name="info" size={14} /> Работает только по тексту.</p>}
          <button className="btn orange block" onClick={() => { setOpen(null); nav.go({ name: "create", kind: open.kind, modelId: open.id }); }}>Создать с этой моделью</button>
          <button className="btn outline block" onClick={() => setOpen(null)}>Закрыть</button>
        </Modal>
      )}
      {kind && <Back onClick={nav.back} />}
    </>
  );
}
