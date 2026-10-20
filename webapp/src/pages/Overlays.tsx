import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useApp } from "../ctx";
import { Icon } from "../icons";
import type { Kind, Route, SearchGroup } from "../types";
import { useDebounced } from "../ui";

const GO: Record<string, (id: number, slug?: string) => Route> = {
  model: () => ({ name: "models" }),
  prompt: () => ({ name: "prompts" }),
  effect: (_, s) => ({ name: "tool", slug: s ?? "" }),
  trend: (_, s) => ({ name: "tool", slug: s ?? "" }),
  photoshoot: (_, s) => ({ name: "tool", slug: s ?? "" }),
  marketing: (_, s) => ({ name: "tool", slug: s ?? "" }),
  history: (id) => ({ name: "order", id }),
};

/** Глобальный поиск «Поиск» (Ctrl/Cmd+K). */
export function SearchOverlay({ onClose }: { onClose: () => void }) {
  const { nav } = useApp();
  const [q, setQ] = useState("");
  const dq = useDebounced(q, 250);
  const [groups, setGroups] = useState<SearchGroup[] | null>(null);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  useEffect(() => { const k = (e: KeyboardEvent) => e.key === "Escape" && onClose(); window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k); }, [onClose]);
  useEffect(() => {
    if (dq.trim().length < 2) { setGroups(null); return; }
    let alive = true;
    api.search(dq.trim()).then((g) => alive && setGroups(g)).catch(() => alive && setGroups([]));
    return () => { alive = false; };
  }, [dq]);
  return (
    <div className="s-overlay" onClick={onClose} role="dialog" aria-modal aria-label="Поиск">
      <div className="s-box" onClick={(e) => e.stopPropagation()}>
        <div className="s-input"><Icon name="search" size={20} /><input ref={ref} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по моделям, эффектам, промптам и истории" aria-label="Поиск" /></div>
        <div className="s-res">
          {dq.trim().length < 2 && <div className="s-group">Введите хотя бы 2 символа</div>}
          {groups && groups.length === 0 && <div className="s-group">Ничего не найдено</div>}
          {(groups ?? []).map((g) => (
            <div key={g.type}>
              <div className="s-group">{g.label}</div>
              {g.items.map((it) => (
                <button key={`${g.type}-${it.id}`} className="s-item" onClick={() => { onClose(); nav.go((GO[g.type] ?? (() => ({ name: "home" } as Route)))(it.id, it.slug)); }}>
                  <b style={{ fontWeight: 600 }}>{it.title}</b><span>{it.subtitle}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const OPTS: [string, string, "image" | "video" | "user" | "send" | "megaphone" | "sparkle"][] = [
  ["photo", "Фото", "image"], ["video", "Видео", "video"], ["avatars", "Аватары", "user"], ["social", "Контент для соцсетей", "send"], ["ads", "Реклама", "megaphone"], ["other", "Другое", "sparkle"],
];

/** Первый вход: «Добро пожаловать.» → «Что вы хотите создавать?». */
export function Onboarding() {
  const { me, refreshMe } = useApp();
  const [step, setStep] = useState(0);
  const [sel, setSel] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  async function finish() {
    setBusy(true);
    try { if (sel.length) await api.savePrefs({ interests: sel }); await api.welcomed(); } catch { /* не мешаем входу */ }
    refreshMe();
  }
  return (
    <div className="onb" role="dialog" aria-modal>
      <div className="onb-in">
        {step === 0 ? (
          <>
            <h1 className="pf-h1" style={{ fontSize: 44 }}>Добро пожаловать.</h1>
            <p className="pf-lead">Nolla AI — платформа для создания изображений, видео и озвучки с лучшими AI-моделями.{me.welcome_bonus > 0 ? ` Мы начислили вам ${me.welcome_bonus} токенов для старта.` : ""}</p>
            <button className="btn orange big" onClick={() => setStep(1)}>Продолжить</button>
          </>
        ) : (
          <>
            <h1 className="pf-h1" style={{ fontSize: 34 }}>Что вы хотите создавать?</h1>
            <p className="pf-lead">Можно выбрать несколько вариантов — мы подскажем, с чего начать.</p>
            <div className="onb-opts">
              {OPTS.map(([k, l, ic]) => <button key={k} className={sel.includes(k) ? "on" : ""} onClick={() => setSel(sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k])}><Icon name={ic} size={22} />{l}</button>)}
            </div>
            <button className="btn orange big" disabled={busy} onClick={finish}>{busy ? "Подождите…" : "Начать"}</button>
            <button className="pf-link" style={{ alignSelf: "center" }} onClick={finish}>Пропустить</button>
          </>
        )}
      </div>
    </div>
  );
}


const CREATE_OPTIONS: [string, string, string, "image" | "video" | "audio"][] = [
  ["photo", "Фото", "Изображение по описанию или из вашего снимка", "image"],
  ["video", "Видео", "Короткий ролик по описанию или из фото", "video"],
  ["audio", "Аудио", "Озвучка текста выбранным голосом", "audio"],
];

/** Меню создания: на компьютере раскрывается под кнопкой «+», на телефоне — нижней панелью. */
export function CreateMenu({ onClose, onPick, onMore }: { onClose: () => void; onPick: (kind: Kind) => void; onMore: () => void }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onDoc = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) onClose(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [onClose]);
  return (
    <>
      <div className="create-scrim" onClick={onClose} />
      <div className="create-pop" ref={box} role="dialog" aria-label="Создать">
        <div className="create-head">Что создаём?</div>
        {CREATE_OPTIONS.map(([kind, title, text, icon]) => (
          <button key={kind} className="create-item" onClick={() => { onClose(); onPick(kind as Kind); }}>
            <span className="create-ic"><Icon name={icon} size={19} /></span>
            <span className="create-txt"><b>{title}</b><span>{text}</span></span>
          </button>
        ))}
        <button className="create-more" onClick={() => { onClose(); onMore(); }}>Готовые эффекты и инструменты</button>
      </div>
    </>
  );
}
