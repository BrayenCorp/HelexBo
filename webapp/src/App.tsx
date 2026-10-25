import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AppCtx, showToast } from "./ctx";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { Admin } from "./admin/Admin";
import { Avatars } from "./pages/Avatars";
import { Balance, Payments } from "./pages/Balance";
import { Catalog, EFFECTS_CFG, Marketing, Prompts, SHOOTS_CFG, TRENDS_CFG } from "./pages/Catalog";
import { History } from "./pages/History";
import { Home } from "./pages/Home";
import { Ideas } from "./pages/Ideas";
import { Integrations } from "./pages/Integrations";
import { Models } from "./pages/Models";
import { OrderView } from "./pages/OrderView";
import { Onboarding, SearchOverlay } from "./pages/Overlays";
import { Profile, Settings } from "./pages/Profile";
import { Studio } from "./pages/Studio";
import { tg } from "./telegram";
import { BUILD } from "./version";
import type { Me, Nav, Route } from "./types";
import { BalanceChip, ErrorBox, Loading, Logo, Sheet } from "./ui";
import { CreateMenu } from "./pages/Overlays";

type NavItem = { id: string; label: string; icon: IconName; to: Route; match: Route["name"][] };
const MAIN: NavItem[] = [
  { id: "home", label: "Главная", icon: "home", to: { name: "home" }, match: ["home"] },
  { id: "create", label: "Создать", icon: "sparkle", to: { name: "create" }, match: ["create"] },
  { id: "ideas", label: "Идеи", icon: "bolt", to: { name: "ideas" }, match: ["ideas"] },
  { id: "models", label: "Модели", icon: "layers", to: { name: "models" }, match: ["models"] },
  { id: "effects", label: "Эффекты", icon: "wand", to: { name: "effects" }, match: ["effects", "tool"] },
  { id: "trends", label: "Тренды", icon: "flame", to: { name: "trends" }, match: ["trends"] },
  { id: "shoots", label: "Фотосессии", icon: "camera", to: { name: "photoshoots" }, match: ["photoshoots"] },
  { id: "avatars", label: "Аватары", icon: "user", to: { name: "avatars" }, match: ["avatars"] },
  { id: "prompts", label: "Промпты", icon: "edit", to: { name: "prompts" }, match: ["prompts"] },
  { id: "marketing", label: "Маркетинг", icon: "megaphone", to: { name: "marketing" }, match: ["marketing"] },
  { id: "history", label: "Мои генерации", icon: "clock", to: { name: "history" }, match: ["history", "order"] },
];
const MORE: NavItem[] = [
  { id: "balance", label: "Баланс", icon: "coin", to: { name: "balance" }, match: ["balance", "payments"] },
  { id: "profile", label: "Профиль", icon: "settings", to: { name: "profile" }, match: ["profile", "settings"] },
];

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Бот открывает приложение сразу на нужной карточке: ?slug=... или startapp
  const [stack, setStack] = useState<Route[]>(() => {
    const slug = new URLSearchParams(window.location.search).get("slug") || tg?.initDataUnsafe?.start_param || "";
    return /^[a-z0-9-]{2,60}$/.test(slug) ? [{ name: "home" }, { name: "tool", slug }] : [{ name: "home" }];
  });
  const [menu, setMenu] = useState(false);
  const [quick, setQuick] = useState(false);
  const [search, setSearch] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [stale, setStale] = useState(false);  // на сервере новая сборка, а у человека открыта старая из кеша
  const route = stack[stack.length - 1];

  const refreshMe = useCallback(() => { api.me().then((m) => { setMe(m); setError(null); }).catch((e: Error) => setError(e.message)); }, []);
  useEffect(refreshMe, [refreshMe]);
  useEffect(() => { if (me && !sessionStorage.getItem("nolla-open")) { sessionStorage.setItem("nolla-open", "1"); api.eventOpen().catch(() => undefined); } }, [me]);
  // Старое приложение из кеша: на сервере лежит сборка новее той, что открылась.
  useEffect(() => { api.version().then((v) => setStale((v.webapp_build ?? v.build) !== BUILD)).catch(() => undefined); }, []);
  useEffect(() => { document.documentElement.dataset.theme = route.name === "admin" ? "light" : "dark"; }, [route.name]);

  const nav: Nav = useMemo(() => ({
    go: (r) => { setMenu(false); setQuick(false); setStack((s) => [...s, r]); window.scrollTo(0, 0); },
    replace: (r) => { setStack((s) => [...s.slice(0, -1), r]); window.scrollTo(0, 0); },
    reset: (r) => { setMenu(false); setQuick(false); setStack([r]); window.scrollTo(0, 0); },
    back: () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
  }), []);

  useEffect(() => {
    const app = tg;
    if (!app) return;
    if (stack.length > 1) app.BackButton.show(); else app.BackButton.hide();
    app.BackButton.onClick(nav.back);
    return () => app.BackButton.offClick(nav.back);
  }, [stack.length, nav]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const onToast = (e: Event) => { setToast((e as CustomEvent<string>).detail); clearTimeout(timer); timer = setTimeout(() => setToast(null), 3200); };
    window.addEventListener("nolla-toast", onToast);
    return () => { window.removeEventListener("nolla-toast", onToast); clearTimeout(timer); };
  }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearch((v) => !v); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  const toggleFavorite = useCallback((kind: "template" | "order", id: number) => {
    setMe((cur) => {
      if (!cur) return cur;
      const list = kind === "template" ? cur.favorites.templates : cur.favorites.orders;
      const on = !list.includes(id);
      api.setFavorite(kind, id, on).then((fav) => setMe((m) => (m ? { ...m, favorites: fav } : m))).catch(() => showToast("Не удалось изменить избранное"));
      const next = on ? [id, ...list] : list.filter((x) => x !== id);
      return { ...cur, favorites: { ...cur.favorites, [kind === "template" ? "templates" : "orders"]: next } };
    });
  }, []);

  const ensureRegistered = useCallback(async (): Promise<boolean> => {
    if (me?.registered) return true;
    try { await api.register(); setMe(await api.me()); return true; }
    catch { showToast("Не удалось войти. Откройте приложение из Telegram."); return false; }
  }, [me?.registered]);

  if (error && !me) {
    return (
      <main className="pf-page"><Logo /><ErrorBox message={error} onRetry={refreshMe} /><p className="muted small">Откройте приложение кнопкой в Telegram-боте.</p></main>
    );
  }
  if (!me) return <main className="pf-page"><Loading /></main>;

  const ctxValue = { me, nav, refreshMe, toggleFavorite, ensureRegistered };
  if (route.name === "admin") {
    return (
      <AppCtx.Provider value={ctxValue}>
        <Admin page={route.page} id={route.id} />
        {toast && <div className="toast" role="status" style={{ bottom: 24 }}>{toast}</div>}
      </AppCtx.Provider>
    );
  }

  const active = (it: NavItem) => it.match.includes(route.name);
  const bottom = (id: string, label: string, icon: IconName, to: Route, match: Route["name"][]) => (
    <button className={match.includes(route.name) ? "on" : ""} onClick={() => nav.reset(to)}><Icon name={icon} size={22} /><span>{label}</span></button>
  );
  const pageKey = route.name + ("id" in route ? String(route.id) : "slug" in route ? String(route.slug) : "");

  return (
    <AppCtx.Provider value={ctxValue}>
      <div className="pf">
        <aside className="pf-side" aria-label="Разделы">
          <Logo />
          <button className="btn orange block side-create" onClick={() => setQuick(true)}><Icon name="plus" size={17} />Создать</button>
          {MAIN.map((it) => <button key={it.id} className={`pf-nav ${active(it) ? "on" : ""}`} onClick={() => nav.reset(it.to)}><Icon name={it.icon} size={19} />{it.label}</button>)}
          <div className="pf-nav-sep" />
          {MORE.map((it) => <button key={it.id} className={`pf-nav ${active(it) ? "on" : ""}`} onClick={() => nav.reset(it.to)}><Icon name={it.icon} size={19} />{it.label}</button>)}
        </aside>
        <div className="pf-main">
          <header className="pf-top">
            <span className="logo-wrap"><Logo /></span>
            <span className="pf-top-space" />
            <button className="pf-search-btn" onClick={() => setSearch(true)} aria-label="Поиск"><Icon name="search" size={18} /><span>Поиск</span><kbd>Ctrl K</kbd></button>
            <div className="plus-wrap">
              <button className="plus-btn" onClick={() => setQuick((v) => !v)} aria-label="Создать" aria-expanded={quick}><Icon name="plus" size={20} /></button>
              {quick && <CreateMenu onClose={() => setQuick(false)} onPick={(kind) => nav.go({ name: "create", kind })} onMore={() => nav.go({ name: "effects" })} />}
            </div>
            <BalanceChip balance={me.balance} onClick={() => nav.go({ name: "balance" })} />
          </header>
          <main className="pf-page" key={pageKey}>
            {stale && (
              <div className="notice bad update-note" role="alert">
                <p>Вышла новая версия приложения, а у вас открыта прежняя.</p>
                <button className="btn orange sm" onClick={() => window.location.reload()}>Обновить</button>
              </div>
            )}
            {me.status === "blocked" && <div className="notice bad"><p>Ваш аккаунт заблокирован: создание новых работ недоступно. Обратитесь в поддержку.</p></div>}
            {route.name === "home" && <Home />}
            {route.name === "ideas" && <Ideas />}
            {route.name === "create" && <Studio init={route} />}
            {route.name === "tool" && <Studio init={{ name: "create", slug: route.slug, refOrderId: route.refOrderId }} />}
            {route.name === "models" && <Models kind={route.kind} />}
            {route.name === "effects" && <Catalog cfg={EFFECTS_CFG} tag={route.tag} />}
            {route.name === "trends" && <Catalog cfg={TRENDS_CFG} />}
            {route.name === "photoshoots" && <Catalog cfg={SHOOTS_CFG} tag={route.tag} />}
            {route.name === "avatars" && <Avatars />}
            {route.name === "prompts" && <Prompts />}
            {route.name === "marketing" && <Marketing />}
            {route.name === "order" && <OrderView id={route.id} />}
            {route.name === "history" && <History initial={route.filter} />}
            {route.name === "profile" && <Profile />}
            {route.name === "settings" && <Settings />}
            {route.name === "balance" && <Balance />}
            {route.name === "payments" && <Payments />}
            {route.name === "integrations" && <Integrations />}
          </main>
        </div>

        <div className="pf-dock">
          <nav className="pf-bottom" aria-label="Разделы">
            {bottom("home", "Главная", "home", { name: "home" }, ["home"])}
            {bottom("ideas", "Идеи", "bolt", { name: "ideas" }, ["ideas", "trends", "photoshoots", "effects", "marketing", "prompts"])}
            {bottom("history", "Генерации", "clock", { name: "history" }, ["history", "order"])}
            {bottom("profile", "Профиль", "user", { name: "profile" }, ["profile", "settings", "balance", "payments", "integrations"])}
            <button className={["create", "tool", "models", "avatars"].includes(route.name) ? "on" : ""} onClick={() => setMenu(true)}><Icon name="menu" size={22} /><span>Ещё</span></button>
          </nav>
        </div>

        {menu && (
          <Sheet title="Разделы" onClose={() => setMenu(false)}>
            <div className="menu-sheet">
              {[...MAIN.filter((i) => !["home", "ideas", "history"].includes(i.id)), ...MORE].map((it) => (
                <button key={it.id} onClick={() => nav.reset(it.to)}><Icon name={it.icon} size={20} />{it.label}</button>
              ))}
              <button onClick={() => { setMenu(false); setSearch(true); }}><Icon name="search" size={20} />Поиск</button>
            </div>
          </Sheet>
        )}
        {search && <SearchOverlay onClose={() => setSearch(false)} />}
        {me.show_welcome && <Onboarding />}
        {toast && <div className="toast" role="status">{toast}</div>}
      </div>
    </AppCtx.Provider>
  );
}
