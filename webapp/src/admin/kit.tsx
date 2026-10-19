import { useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError } from "../api";
import { Icon } from "../icons";
import { Cover, ErrorBox, Modal } from "../ui";

export const errText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

export function Card({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="acard">
      <div className="acard-head"><h2>{title}</h2>{hint && <span className="muted small">{hint}</span>}</div>
      {children}
    </section>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}{hint && <span className="field-hint">{hint}</span>}</label>;
}

export function TextInput({ value, onChange, placeholder, type = "text" }: { value: string | number; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return <input className="input" type={type} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />;
}

export function TextArea({ value, onChange, rows = 3, placeholder }: { value: string; onChange: (v: string) => void; rows?: number; placeholder?: string }) {
  return <textarea className="input" rows={rows} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />;
}

export function SelectInput({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <span className="select">
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </span>
  );
}

export function Stepper({ value, onChange, min = 0, step = 1 }: { value: number; onChange: (v: number) => void; min?: number; step?: number }) {
  return (
    <span className="stepper">
      <button type="button" onClick={() => onChange(Math.max(min, value - step))} aria-label="Меньше">−</button>
      <input type="number" value={value} onChange={(e) => onChange(Math.max(min, Number(e.target.value) || 0))} />
      <button type="button" onClick={() => onChange(value + step)} aria-label="Больше">+</button>
    </span>
  );
}

export function SwitchRow({ label, hint, checked, onChange }: { label: string; hint?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="switch-row" onClick={() => onChange(!checked)}>
      <span className="row-main"><b>{label}</b>{hint && <span className="muted small">{hint}</span>}</span>
      <button type="button" role="switch" aria-checked={checked} className={`switch ${checked ? "on" : ""}`} onClick={(e) => { e.stopPropagation(); onChange(!checked); }}><span /></button>
    </div>
  );
}

/** Загрузка своего фото или видео: файл уходит на сервер, поле получает готовый адрес. */
export function useUpload(onDone: (url: string) => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function pick(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(null);
    try { onDone((await api.admin.upload(file)).url); }
    catch (e) { setError(errText(e, "Не удалось загрузить файл")); }
    finally { setBusy(false); }
  }
  return { busy, error, pick };
}

export function MediaPicker({ label, hint, value, onChange, ratio = "4 / 5" }: { label: string; hint?: string; value: string; onChange: (url: string) => void; ratio?: string }) {
  const up = useUpload(onChange);
  return (
    <div className="picker">
      <span className="picker-label">{label}</span>
      <div className="picker-box" style={{ aspectRatio: ratio }}>
        <Cover url={value} />
        <div className="picker-actions">
          <label className="pill-btn">
            <Icon name="upload" size={16} /> {up.busy ? "Загружаем…" : value ? "Заменить" : "Загрузить фото или видео"}
            <input type="file" accept="image/*,video/mp4,video/webm" hidden onChange={(e) => up.pick(e.target.files?.[0])} />
          </label>
          {value && <button type="button" className="pill-btn" onClick={() => onChange("")}><Icon name="trash" size={16} /></button>}
        </div>
      </div>
      {hint && <span className="field-hint">{hint}</span>}
      {up.error && <ErrorBox message={up.error} />}
    </div>
  );
}

export function MediaGallery({ label, hint, value, onChange, max = 8 }: { label: string; hint?: string; value: string[]; onChange: (v: string[]) => void; max?: number }) {
  const up = useUpload((url) => onChange([...value, url]));
  return (
    <div className="picker">
      <span className="picker-label">{label}</span>
      <div className="gallery">
        {value.map((u, i) => (
          <span key={u + i} className="gallery-item">
            <Cover url={u} seed={i} />
            <button type="button" className="gallery-x" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label="Убрать"><Icon name="close" size={14} /></button>
          </span>
        ))}
        {value.length < max && (
          <label className="gallery-add">
            <Icon name="plus" size={22} />
            <span>{up.busy ? "…" : "Добавить"}</span>
            <input type="file" accept="image/*,video/mp4,video/webm" hidden onChange={(e) => up.pick(e.target.files?.[0])} />
          </label>
        )}
      </div>
      {hint && <span className="field-hint">{hint}</span>}
      {up.error && <ErrorBox message={up.error} />}
    </div>
  );
}

export function SaveBar({ dirty, saving, onSave, error, label = "Сохранить" }: { dirty: boolean; saving: boolean; onSave: () => void; error?: string | null; label?: string }) {
  return (
    <div className="savebar">
      {error && <span className="savebar-error">{error}</span>}
      <span className={`dirty ${dirty ? "on" : ""}`}>{dirty ? "Есть несохранённые изменения" : "Изменений нет"}</span>
      <button className="btn gold" disabled={!dirty || saving} onClick={onSave}>{saving ? "Сохраняем…" : label}</button>
    </div>
  );
}

export function ConfirmModal({ title, text, confirm, onConfirm, onClose }: { title: string; text: string; confirm: string; onConfirm: () => void; onClose: () => void }) {
  return (
    <Modal onClose={onClose}>
      <span className="modal-icon danger"><Icon name="trash" size={26} /></span>
      <h2>{title}</h2>
      <p className="muted">{text}</p>
      <button className="btn danger block" onClick={onConfirm}>{confirm}</button>
      <button className="btn ghost block" onClick={onClose}>Отмена</button>
    </Modal>
  );
}

export function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return <div className="stat-tile"><span className="muted small">{label}</span><b>{value}</b>{sub && <span className="muted small">{sub}</span>}</div>;
}

export function ListRow({ thumb, title, sub, right, onClick }: { thumb?: string | null; title: string; sub?: string; right?: ReactNode; onClick?: () => void }) {
  return (
    <li>
      <div className="row-card" role="button" tabIndex={0} onClick={onClick} onKeyDown={(e) => e.key === "Enter" && onClick?.()}>
        {thumb !== null && <span className="row-thumb"><Cover url={thumb} /></span>}
        <span className="row-main"><b>{title}</b>{sub && <span className="muted small">{sub}</span>}</span>
        {right}
      </div>
    </li>
  );
}

export function useDraft<T>(initial: T) {
  const [base, setBase] = useState<T>(initial);
  const [draft, setDraft] = useState<T>(initial);
  const dirty = JSON.stringify(base) !== JSON.stringify(draft);
  return {
    draft, dirty,
    set: <K extends keyof T>(k: K, v: T[K]) => setDraft((d) => ({ ...d, [k]: v })),
    reset: (v: T) => { setBase(v); setDraft(v); },
  };
}
