import { tg } from "./telegram";
import type {
  AiModel, Category, CreateOrderResponse, Favorites, GenParams, Landing, PayMethods, TokensSummary, Kind, LedgerRow, Me, Order, Pack, PaymentRow, PaymentStart,
  Profile, Template, TemplateDetail, AvatarRow, CatalogItem, Integrations, PlatformHome, PlatformMeta, Prefs, Quote, SearchGroup,
} from "./types";

export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number) {
    super(message);
  }
}

// Только для локальной отладки в обычном браузере (сервер должен быть запущен с DEV_MODE=1).
const DEV_USER: string | undefined = import.meta.env.VITE_DEV_USER;

function authHeaders(): Record<string, string> {
  if (tg?.initData) return { Authorization: `tma ${tg.initData}` };
  if (DEV_USER) return { "X-Dev-User": DEV_USER };
  return {};
}

async function raw(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(path, { ...init, headers: { ...authHeaders(), ...(init.headers ?? {}) } });
  if (!res.ok) {
    let code = "error";
    let message = `Ошибка ${res.status}`;
    try {
      const body = await res.json();
      code = body.code ?? code;
      message = body.message ?? (typeof body.detail === "string" ? body.detail : message);
    } catch {
      /* тело не JSON */
    }
    throw new ApiError(message, code, res.status);
  }
  return res;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  return (await raw(path, init)).json() as Promise<T>;
}

function send<T>(method: string, path: string, body: unknown): Promise<T> {
  return json<T>(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const api = {
  me: () => json<Me>("/api/me"),
  profile: () => json<Profile>("/api/profile"),
  home: () => json<Landing>("/api/home"),
  register: () => send<{ registered: boolean; new: boolean; balance: number }>("POST", "/api/register", {}),
  welcomed: () => send<{ ok: boolean }>("POST", "/api/welcomed", {}),
  eventOpen: () => send<{ ok: boolean }>("POST", "/api/event/open", {}),
  models: (kind?: Kind) => json<AiModel[]>(`/api/models${kind ? `?kind=${kind}` : ""}`),
  paymentMethods: () => json<PayMethods>("/api/payment-methods"),
  tokens: () => json<TokensSummary>("/api/tokens"),
  categories: () => json<Category[]>("/api/categories"),
  category: (id: string) => json<Category>(`/api/categories/${encodeURIComponent(id)}`),
  templates: (p: { kind?: Kind; category?: string; q?: string; collection?: string } = {}) => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(p)) if (v) q.set(k, v);
    return json<Template[]>(`/api/templates?${q}`);
  },
  template: (id: number) => json<TemplateDetail>(`/api/templates/${id}`),
  createOrder: (o: { requestId: string; templateId?: number; kind?: Kind; prompt?: string; params?: GenParams; style?: string; photo?: File | null; modelId?: number; count?: number; photo2?: File | null; avatarId?: number; refOrderId?: number }) => {
    const form = new FormData();
    form.set("request_id", o.requestId);
    if (o.templateId) form.set("template_id", String(o.templateId));
    if (o.kind) form.set("kind", o.kind);
    if (o.prompt) form.set("prompt", o.prompt);
    if (o.params && Object.keys(o.params).length) form.set("params", JSON.stringify(o.params));
    if (o.style) form.set("style", o.style);
    if (o.modelId) form.set("model_id", String(o.modelId));
    if (o.count && o.count > 1) form.set("count", String(o.count));
    if (o.photo) form.set("photo", o.photo);
    if (o.photo2) form.set("photo2", o.photo2);
    if (o.avatarId) form.set("avatar_id", String(o.avatarId));
    if (o.refOrderId) form.set("ref_order_id", String(o.refOrderId));
    return json<CreateOrderResponse>("/api/orders", { method: "POST", body: form });
  },
  orders: () => json<Order[]>("/api/orders"),
  order: (id: number) => json<Order>(`/api/orders/${id}`),
  resultBlob: async (id: number) => (await raw(`/api/orders/${id}/result`)).blob(),
  deleteOrder: (id: number) => json<{ deleted: boolean }>(`/api/orders/${id}`, { method: "DELETE" }),
  sendToChat: (id: number) => json<{ sent: boolean }>(`/api/orders/${id}/send-to-chat`, { method: "POST" }),
  favorites: () => json<{ templates: TemplateDetail[]; results: Order[] }>("/api/favorites"),
  setFavorite: (kind: "template" | "order", refId: number, on: boolean) =>
    send<Favorites>("POST", "/api/favorites", { kind, ref_id: refId, on }),
  packages: () => json<Pack[]>("/api/packages"),
  ledger: () => json<LedgerRow[]>("/api/ledger"),
  paymentsHistory: () => json<PaymentRow[]>("/api/payments/history"),
  startPayment: (packageId: string, method: string) => send<PaymentStart>("POST", "/api/payments/start", { package_id: packageId, method }),
  testConfirm: (payload: string) =>
    send<{ status: string; credited: boolean; balance: number }>("POST", "/api/payments/test-confirm", { payload }),
  setNotify: (on: boolean) => send<{ notify_chat: boolean }>("PUT", "/api/me/settings", { notify_chat: on }),
  deleteMyMedia: () => json<{ deleted_files: number }>("/api/me/media", { method: "DELETE" }),
  meta: () => json<PlatformMeta>("/api/platform/meta"),
  version: () => json<{ version: string; build: string; webapp_build: string | null }>("/api/version"),
  previews: () => json<string[]>("/api/previews"),
  ideas: (tag?: string, q?: string) => {
    const p = new URLSearchParams();
    if (tag) p.set("tag", tag);
    if (q) p.set("q", q);
    return json<CatalogItem[]>(`/api/ideas?${p}`);
  },
  platformHome: () => json<PlatformHome>("/api/platform/home"),
  catalog: (section: string, p: { tag?: string; q?: string; popular?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (p.tag) q.set("tag", p.tag);
    if (p.q) q.set("q", p.q);
    if (p.popular) q.set("popular", "true");
    return json<CatalogItem[]>(`/api/catalog/${section}?${q}`);
  },
  catalogItem: (id: number) => json<CatalogItem>(`/api/catalog/item/${id}`),
  catalogSlug: (slug: string) => json<CatalogItem>(`/api/catalog/slug/${encodeURIComponent(slug)}`),
  search: (q: string) => json<SearchGroup[]>(`/api/search?q=${encodeURIComponent(q)}`),
  quote: (p: { kind?: Kind; templateId?: number; modelId?: number; count?: number }) => {
    const q = new URLSearchParams();
    if (p.kind) q.set("kind", p.kind);
    if (p.templateId) q.set("template_id", String(p.templateId));
    if (p.modelId) q.set("model_id", String(p.modelId));
    if (p.count) q.set("count", String(p.count));
    return json<Quote>(`/api/quote?${q}`);
  },
  avatars: () => json<AvatarRow[]>("/api/avatars"),
  avatar: (id: number) => json<AvatarRow>(`/api/avatars/${id}`),
  createAvatar: (name: string, photos: File[], consent: boolean) => {
    const form = new FormData();
    form.set("name", name);
    form.set("consent", consent ? "true" : "false");
    photos.forEach((f) => form.append("photos", f));
    return json<AvatarRow>("/api/avatars", { method: "POST", body: form });
  },
  deleteAvatar: (id: number) => json<{ deleted: boolean }>(`/api/avatars/${id}`, { method: "DELETE" }),
  avatarCoverBlob: async (id: number) => (await raw(`/api/avatars/${id}/cover`)).blob(),
  frameBlob: async (id: number, i: number) => (await raw(`/api/orders/${id}/frames/${i}`)).blob(),
  regenFrame: (id: number, index: number, requestId: string) =>
    send<{ order: Order; balance: number; price: number }>("POST", `/api/orders/${id}/regen-frame`, { index, request_id: requestId }),
  prefs: () => json<Prefs>("/api/me/prefs"),
  savePrefs: (p: Partial<Prefs> & { clear_model?: boolean }) => send<Prefs>("PUT", "/api/me/prefs", p),
  integrations: () => json<Integrations>("/api/integrations"),
  createToken: (label: string) => send<{ id: number; token: string; label: string }>("POST", "/api/integrations/tokens", { label }),
  revokeToken: (id: number) => json<{ revoked: boolean }>(`/api/integrations/tokens/${id}`, { method: "DELETE" }),
  demoPay: (packageId: string, method: string) =>
    send<{ status: string; credited: boolean; tokens: number; balance: number }>("POST", "/api/payments/demo", { package_id: packageId, method }),
  admin: {
    get: <T>(path: string) => json<T>(`/api/admin/${path}`),
    send: <T>(method: "POST" | "PUT", path: string, body: unknown) => send<T>(method, `/api/admin/${path}`, body),
    del: <T>(path: string) => json<T>(`/api/admin/${path}`, { method: "DELETE" }),
    download: async (kind: string) => (await raw(`/api/admin/export/${kind}`)).blob(),
    sendExport: (kind: string) => json<{ sent: boolean }>(`/api/admin/export/${kind}/send`, { method: "POST" }),
    previews: () => json<{ name: string; url: string; size: number }[]>("/api/admin/previews"),
    addPreview: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return json<{ name: string; url: string }>("/api/admin/previews", { method: "POST", body: form });
    },
    delPreview: (name: string) => json<{ deleted: boolean }>(`/api/admin/previews/${encodeURIComponent(name)}`, { method: "DELETE" }),
    upload: (file: File) => {
      const form = new FormData();
      form.set("file", file);
      return json<{ url: string; kind: "image" | "video" }>("/api/admin/media", { method: "POST", body: form });
    },
  },
};
