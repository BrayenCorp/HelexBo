import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { AppCtx, showToast } from "./ctx";
import { Icon } from "./icons";
import type { IconName } from "./icons";
import { Admin } from "./admin/Admin";
import { About } from "./pages/About";
import { Category } from "./pages/Category";
import { Explore } from "./pages/Explore";
import { Generate } from "./pages/Generate";
import { History } from "./pages/History";
import { Home } from "./pages/Home";
import { OrderView } from "./pages/OrderView";
import { Payments } from "./pages/Payments";
import { Profile } from "./pages/Profile";
import { Settings } from "./pages/Settings";
import { Shop } from "./pages/Shop";
import { TemplatePage } from "./pages/TemplatePage";
import { Tokens } from "./pages/Tokens";
import { Welcome } from "./pages/Welcome";
import { tg } from "./telegram";
import type { Me, Nav, Route } from "./types";
import { BalanceChip, ErrorBox, Loading, Logo, ProBadge, Sheet } from "./ui";

type Tab = "home" | "explore" | "history" | "profile";

function tabOf(r: Route): Tab {
  switch (r.name) {
    case "home": return "home";
    case "explore": case "category": case "template": return "explore";
    case "history": case "order": return "history";
    default: return "profile";
  }
}

// На этих экранах нижнее меню скрыто: у них своя основная кнопка внизу или нужен весь экран.
const NAV_HIDDEN: Route["name"][] = ["generate", "order", "admin", "template"];
const TOPBAR: Route["name"][] = ["home", "explore", "history", "profile"];

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stack, setStack] = useState<Route[]>([{ name: "home" }]);
  const [quick, setQuick] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const route = stack[stack.length - 1];

  const refreshMe = useCallback(() => {
    api.me().then((m) => { setMe(m); setError(null); }).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(refreshMe, [refreshMe]);
  useEffect(() => { if (me && !sessionStorage.getItem("nolla-open")) { sessionStorage.setItem("nolla-open", "1"); api.eventOpen().catch(() => undefined); } }, [me]);

  const nav: Nav = useMemo(() => ({
    go: (r) => { setQuick(false); setStack((s) => [...s, r]); window.scrollTo(0, 0); },
    replace: (r) => { setStack((s) => [...s.slice(0, -1), r]); window.scrollTo(0, 0); },
    reset: (r) => { setQuick(false); setStack([r]); window.scrollTo(0, 0); },
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
    const onToast = (e: Event) => {
      setToast((e as CustomEvent<string>).detail);
      clearTimeout(timer);
      timer = setTimeout(() => setToast(null), 3200);
    };
    window.addEventListener("nolla-toast", onToast);
    return () => { window.removeEventListener("nolla-toast", onToast); clearTimeout(timer); };
  }, []);

  const toggleFavorite = useCallback((kind: "template" | "order", id: number) => {
    setMe((cur) => {
      if (!cur) return cur;
      const list = kind === "template" ? cur.favorites.templates : cur.favorites.orders;
      const on = !list.includes(id);
      api.setFavorite(kind, id, on)
        .then((fav) => setMe((m) => (m ? { ...m, favorites: fav } : m)))
        .catch(() => showToast("Не удалось изменить избранное"));
      const next = on ? [id, ...list] : list.filter((x) => x !== id);
      return { ...cur, favorites: { ...cur.favorites, [kind === "template" ? "templates" : "orders"]: next } };
    });
  }, []);

  const ensureRegistered = useCallback(async (): Promise<boolean> => {
    if (me?.registered) return true;
    try {
      await api.register();
      const fresh = await api.me();
      setMe(fresh);
      return true;
    } catch {
      showToast("Не удалось войти. Откройте приложение из Telegram.");
      return false;
    }
  }, [me?.registered]);

  if (error && !me) {
    return (
      <main className="page">
        <Logo />
        <ErrorBox message={error} onRetry={refreshMe} />
        <p className="muted center small">Откройте приложение кнопкой в Telegram-боте.</p>
      </main>
    );
  }
  if (!me) return <main className="page"><Loading /></main>;

  const tab = tabOf(route);
  const hideNav = NAV_HIDDEN.includes(route.name);
  const tabBtn = (t: Tab, label: string, icon: IconName, to: Route) => (
    <button className={tab === t ? "on" : ""} onClick={() => nav.reset(to)}><Icon name={icon} size={22} /><span>{label}</span></button>
  );
  const ctxValue = { me, nav, refreshMe, toggleFavorite, ensureRegistered };

  if (route.name === "admin") {
    return (
      <AppCtx.Provider value={ctxValue}>
        <Admin page={route.page} id={route.id} />
        {toast && <div className="toast" role="status" style={{ bottom: 24 }}>{toast}</div>}
      </AppCtx.Provider>
    );
  }

  return (
    <AppCtx.Provider value={ctxValue}>
      <div className={`app ${hideNav ? "no-nav" : ""}`}>
        {TOPBAR.includes(route.name) && (
          <header className="topbar">
            <Logo subtitle="Больше, чем просто генерация" />
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {me.is_pro && <ProBadge />}
              <BalanceChip balance={me.balance} onClick={() => nav.go({ name: "tokens" })} />
            </span>
          </header>
        )}
        <main className="page" key={route.name + (route.name === "category" || route.name === "template" || route.name === "order" ? String(route.id) : "")}>
          {me.status === "blocked" && <div className="notice bad"><p>Ваш аккаунт заблокирован: создание новых работ недоступно. Обратитесь в поддержку.</p></div>}
          {route.name === "home" && <Home />}
          {route.name === "explore" && <Explore />}
          {route.name === "category" && <Category id={route.id} />}
          {route.name === "template" && <TemplatePage id={route.id} />}
          {route.name === "generate" && <Generate {...route} />}
          {route.name === "order" && <OrderView id={route.id} />}
          {route.name === "history" && <History initial={route.filter} />}
          {route.name === "profile" && <Profile />}
          {route.name === "shop" && <Shop />}
          {route.name === "tokens" && <Tokens />}
          {route.name === "payments" && <Payments />}
          {route.name === "settings" && <Settings />}
          {route.name === "about" && <About />}
        </main>

        {!hideNav && (
          <nav className="tabs" aria-label="Разделы">
            {tabBtn("home", "Главная", "home", { name: "home" })}
            {tabBtn("explore", "Создать", "diamond", { name: "explore" })}
            <span className="fab-slot"><button className="fab" onClick={() => setQuick(true)} aria-label="Быстро создать"><Icon name="plus" size={28} /></button></span>
            {tabBtn("history", "История", "clock", { name: "history" })}
            {tabBtn("profile", "Профиль", "user", { name: "profile" })}
          </nav>
        )}

        {quick && (
          <Sheet title="Что создаём?" onClose={() => setQuick(false)}>
            <div className="quick">
              <button onClick={() => nav.go({ name: "generate", kind: "photo" })}><span><Icon name="image" size={26} /></span><b>Фото</b><small>Изображение по описанию или фото</small></button>
              <button onClick={() => nav.go({ name: "generate", kind: "video" })}><span><Icon name="video" size={26} /></span><b>Видео</b><small>Короткое видео по описанию</small></button>
            </div>
          </Sheet>
        )}
        {me.show_welcome && <Welcome />}
        {toast && <div className="toast" role="status">{toast}</div>}
      </div>
    </AppCtx.Provider>
  );
}
