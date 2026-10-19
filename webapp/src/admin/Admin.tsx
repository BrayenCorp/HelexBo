import { Analytics } from "./Analytics";
import { CategoriesList, CategoryEditor, PackageEditor } from "./Catalogue";
import { ContentAdmin } from "./Content";
import { Dashboard } from "./Dashboard";
import { Errors, Providers, SystemPage } from "./Dev";
import { Activity, Generations, Payments } from "./Lists";
import { Marketing, Referrals, Revenue, Subscriptions, TokensAdmin } from "./Money";
import { SettingsAdmin } from "./SettingsAdmin";
import { TemplateEditor, TemplatesList } from "./Templates";
import { UserProfile, UsersList } from "./Users";
import { AdminShell, ITEMS } from "./shell";
import { useApp } from "../ctx";
import { ErrorBox } from "../ui";

/** Маршрутизация внутри админ-центра. Доступ дополнительно проверяет сервер на каждом запросе. */
export function Admin({ page, id }: { page?: string; id?: string }) {
  const { me } = useApp();
  if (me.roles.length === 0) return <main className="page"><ErrorBox message="Нет доступа" /></main>;
  const first = ITEMS.find((i) => i.roles.some((r) => me.roles.includes(r)))?.page ?? "home";
  const p = page ?? first;
  let body;
  switch (p) {
    case "home": body = <Dashboard />; break;
    case "analytics": body = <Analytics />; break;
    case "users": body = <UsersList />; break;
    case "user": body = <UserProfile id={id ?? ""} />; break;
    case "activity": body = <Activity />; break;
    case "generations": body = <Generations />; break;
    case "content": body = <ContentAdmin />; break;
    case "categories": body = <CategoriesList />; break;
    case "category": body = <CategoryEditor id={id ?? "new"} />; break;
    case "templates": body = <TemplatesList />; break;
    case "template": body = <TemplateEditor id={id ?? "new"} />; break;
    case "trends": body = <TemplatesList trend />; break;
    case "payments": body = <Payments />; break;
    case "revenue": body = <Revenue />; break;
    case "tokens": body = <TokensAdmin />; break;
    case "package": body = <PackageEditor id={id ?? "new"} />; break;
    case "subscriptions": body = <Subscriptions />; break;
    case "referrals": body = <Referrals />; break;
    case "marketing": body = <Marketing />; break;
    case "errors": body = <Errors />; break;
    case "providers": body = <Providers />; break;
    case "system": body = <SystemPage />; break;
    case "settings": body = <SettingsAdmin />; break;
    default: body = <Dashboard />;
  }
  return <AdminShell page={p}>{body}</AdminShell>;
}
