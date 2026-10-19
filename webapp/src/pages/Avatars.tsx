import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import { useApp, showToast } from "../ctx";
import { Icon } from "../icons";
import { CatalogTile, Empty2, Hdr, Sec } from "../pf";
import type { AvatarRow } from "../types";
import { Loading, Modal, useLoad } from "../ui";

const STEPS = ["Фото", "Согласие", "Создание"];

function Cover({ a }: { a: AvatarRow }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!a.has_cover) return;
    let alive = true; let u: string | null = null;
    api.avatarCoverBlob(a.id).then((b) => { if (alive) { u = URL.createObjectURL(b); setUrl(u); } }).catch(() => undefined);
    return () => { alive = false; if (u) URL.revokeObjectURL(u); };
  }, [a.id, a.has_cover]);
  return <span className="hthumb">{url ? <img src={url} alt="" /> : <Icon name="user" size={24} />}</span>;
}

export function Avatars() {
  const { nav, ensureRegistered } = useApp();
  const list = useLoad(() => api.avatars(), []);
  const scenes = useLoad(() => api.catalog("avatar"), []);
  const [wizard, setWizard] = useState(false);
  const [step, setStep] = useState(0);
  const [files, setFiles] = useState<File[]>([]);
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [del, setDel] = useState<AvatarRow | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => { const u = files.map((f) => URL.createObjectURL(f)); setUrls(u); return () => u.forEach(URL.revokeObjectURL); }, [files]);

  const rows = list.data ?? [];
  const working = rows.some((a) => a.status === "queued" || a.status === "analyzing" || a.status === "creating");
  useEffect(() => { if (!working) return; const t = setTimeout(list.reload, 1500); return () => clearTimeout(t); }, [working, list.data]); // eslint-disable-line react-hooks/exhaustive-deps

  function add(fl: FileList | null) {
    if (!fl) return;
    setFiles((cur) => [...cur, ...Array.from(fl)].slice(0, 25));
  }
  function reset() { setWizard(false); setStep(0); setFiles([]); setName(""); setConsent(false); setError(null); }
  async function create() {
    if (!(await ensureRegistered())) return;
    setBusy(true); setError(null);
    try { await api.createAvatar(name, files, consent); showToast("Аватар создаётся"); reset(); list.reload(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Не удалось создать аватар"); } finally { setBusy(false); }
  }
  async function remove() {
    if (!del) return;
    try { await api.deleteAvatar(del.id); showToast("Аватар и его фото удалены"); setDel(null); list.reload(); } catch { showToast("Не удалось удалить"); }
  }

  if (wizard) {
    return (
      <>
        <button className="pf-back" onClick={reset}><Icon name="back" size={18} />Отмена</button>
        <Hdr title="Создать аватар" text="Цифровая версия вас для фотосессий и сцен. Лучше всего подходят 10–25 фото с разных ракурсов." />
        <div className="wiz">{STEPS.map((s, i) => <i key={s} className={i <= step ? "on" : ""} />)}</div>
        <div className="panel">
          {step === 0 && (
            <>
              <b>1. Загрузите фото</b>
              <span className="hint">Минимум 3, максимум 25. Лицо хорошо видно, без очков и фильтров. Не загружайте фото других людей без их согласия.</span>
              <input ref={fileRef} type="file" hidden multiple accept="image/jpeg,image/png,image/webp" onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
              <button className="upl" onClick={() => fileRef.current?.click()}><span className="upl-ic"><Icon name="upload" size={20} /></span><span className="grow"><b>Выбрать фото</b><span>Загружено: {files.length} из 25</span></span></button>
              {files.length > 0 && <div className="thumbs">{urls.map((u, i) => <div key={u}><img src={u} alt="" /><button aria-label="Убрать" onClick={() => setFiles(files.filter((_, j) => j !== i))}><Icon name="close" size={12} /></button></div>)}</div>}
              <button className="btn orange block" disabled={files.length < 3} onClick={() => setStep(1)}>Далее</button>
              {files.length < 3 && <span className="hint">Нужно ещё фото: {3 - files.length}</span>}
            </>
          )}
          {step === 1 && (
            <>
              <b>2. Название и согласие</b>
              <div className="fld"><label htmlFor="an">Название аватара</label><input id="an" maxLength={40} value={name} onChange={(e) => setName(e.target.value)} placeholder="Например: Я" /></div>
              <label className="consent"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <span>Подтверждаю, что на фото — я или человек, давший согласие, и что имею право использовать эти фотографии для создания аватара.</span></label>
              <div className="comp-row"><button className="btn outline" onClick={() => setStep(0)}>Назад</button><button className="btn orange grow" disabled={!consent} onClick={() => setStep(2)}>Далее</button></div>
            </>
          )}
          {step === 2 && (
            <>
              <b>3. Создание</b>
              <p className="hint">Мы проанализируем внешность и создадим аватар. Это займёт немного времени, можно закрыть приложение. Ваши фото можно удалить в любой момент.</p>
              <div className="meta-table"><div><span>Фото</span><b>{files.length}</b></div><div><span>Название</span><b>{name || "Мой аватар"}</b></div></div>
              {error && <div className="notice bad"><p>{error}</p></div>}
              <div className="comp-row"><button className="btn outline" onClick={() => setStep(1)}>Назад</button><button className="btn orange grow" disabled={busy} onClick={create}>{busy ? "Загружаем фото…" : "Создать аватар"}</button></div>
            </>
          )}
        </div>
      </>
    );
  }

  return (
    <>
      <Hdr title="Аватары" text="Создайте цифровую версию себя и размещайте её в любых сценах: портреты, мода, путешествия, реклама."
        right={<button className="btn orange" onClick={() => setWizard(true)}><Icon name="plus" size={18} />Создать аватар</button>} />
      {list.loading && !list.data && <Loading />}
      {list.data && rows.length === 0 && <Empty2 title="Аватаров пока нет" text="Загрузите несколько фото — получите аватар для сцен." action={<button className="btn orange" onClick={() => setWizard(true)}>Создать первый аватар</button>} />}
      <div className="pf-grid wide">
        {rows.map((a) => (
          <div key={a.id} className="row-card">
            <Cover a={a} />
            <span className="grow"><b>{a.name}</b><span>{a.status_label} · {a.photo_count} фото{a.is_stub && a.status === "ready" ? " · демо" : ""}</span>{a.error && <span>{a.error}</span>}</span>
            <button className="btn outline sm" aria-label="Удалить" onClick={() => setDel(a)}><Icon name="trash" size={16} /></button>
          </div>
        ))}
      </div>
      <Sec title="Сцены для аватара">
        {scenes.data && scenes.data.length === 0 && <Empty2 title="Сцен пока нет" />}
        <div className="pf-grid">{(scenes.data ?? []).map((it) => <CatalogTile key={it.id} item={it} onOpen={() => nav.go({ name: "tool", slug: it.slug })} />)}</div>
      </Sec>
      {del && (
        <Modal onClose={() => setDel(null)}>
          <h2>Удалить аватар?</h2>
          <p className="muted">Аватар «{del.name}» и загруженные для него фото будут удалены без возможности восстановления.</p>
          <button className="btn orange block" onClick={remove}>Удалить</button>
          <button className="btn outline block" onClick={() => setDel(null)}>Отмена</button>
        </Modal>
      )}
    </>
  );
}
