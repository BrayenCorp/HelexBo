export type Kind = "photo" | "video";

export interface Favorites { templates: number[]; orders: number[] }

export interface Me {
  id: number;
  first_name: string | null;
  username: string | null;
  balance: number;
  notify_chat: boolean;
  is_pro: boolean;
  registered: boolean;
  show_welcome: boolean;
  welcome_bonus: number;
  max_variants: number;
  status: string;
  ref_link: string;
  bot_link: string;
  freeform: Record<Kind, { price: number; enabled: boolean }>;
  free: { photo: boolean; video: boolean };
  roles: string[];
  modes: { ai: string; payments: string };
  favorites: Favorites;
}

export interface Template {
  id: number;
  title: string;
  description: string;
  category: string;
  kind: Kind;
  preview_url: string;
  preview_kind: "image" | "video";
  price_credits: number;
  is_popular: boolean;
  is_trend: boolean;
  style_label: string;
}

export interface TemplateDetail extends Template {
  examples: { url: string; kind: "image" | "video" }[];
  styles: { id: string; title: string }[];
}

export interface Category {
  id: string;
  title: string;
  description: string;
  cover_url: string;
  count: number;
}

export interface Banner {
  banner_title: string;
  banner_text: string;
  banner_button: string;
  banner_image_url: string;
  video_title: string;
  video_text: string;
  video_image_url: string;
  support_url: string;
}

export interface ShowcaseItem {
  id: number;
  title: string;
  media_url: string;
  media_kind: "image" | "video";
  template_id: number | null;
  prompt: string;
}

export interface HomeData {
  banner: Banner;
  categories: Category[];
  popular: Template[];
  trends: Template[];
  showcase: ShowcaseItem[];
}

export type OrderStatus = "created" | "processing" | "done" | "failed";

export interface Order {
  id: number;
  template_id: number;
  kind: Kind;
  status: OrderStatus;
  used_free: boolean;
  price_credits: number;
  has_result: boolean;
  result_mime: string | null;
  is_stub: boolean;
  error: string | null;
  created_at: string;
  title: string | null;
  preview_url: string;
  prompt: string;
  params: GenParams;
  style: string | null;
  duration_sec: number | null;
  is_system: boolean;
}

export interface GenParams {
  format?: string;
  quality?: string;
  style?: string;
  lighting?: string;
  camera?: string;
}

export interface CreateOrderResponse {
  order: Order;
  orders: Order[];
  created: boolean;
  balance: number;
  free: { photo: boolean; video: boolean };
}

export interface Pack {
  id: string;
  title: string;
  credits: number;
  bonus: number;
  price_stars: number;
  old_price_stars: number | null;
  price_rub: number | null;
  badge: string;
}

export interface LedgerRow {
  id: number;
  delta: number;
  reason: string;
  kind: Kind | null;
  note: string | null;
  created_at: string;
}

export interface TokensSummary {
  balance: number;
  bought: number;
  spent: number;
  refunded: number;
  bonus: number;
}

export interface AiModel {
  id: number;
  name: string;
  kind: Kind;
  description: string;
  purpose: string;
  audience: string[];
  image_url: string;
  price_credits: number;
}

export interface PayMethod {
  code: string;
  title: string;
  description: string;
}

export interface PayMethods {
  available: PayMethod[];
  soon: PayMethod[];
}

export interface ContentItem {
  title: string;
  text: string;
}

export interface Landing {
  content: {
    hero: { title: string; text: string; primary: string; secondary: string };
    capabilities: ContentItem[];
    steps: ContentItem[];
    why: ContentItem[];
    about: { title: string; text: string };
    tokens: { title: string; text: string };
    payment: { title: string; text: string };
    cta: { title: string; text: string; button: string };
  };
  categories: Category[];
  models: AiModel[];
  trends: { id: number; title: string; description: string; preview_url: string; kind: Kind; uses: number }[];
  works: { id: string; title: string; media_url: string; kind: Kind; template_id: number | null; prompt: string; category: string | null }[];
  work_categories: { id: string; title: string }[];
  chooser: { title: string; action: { type: "model" | "category" | "generate"; model_id?: number; kind?: Kind; id?: string } }[];
  price_from: Partial<Record<Kind, number>>;
  packages: Pack[];
  methods: PayMethods;
  faq: { id: number; question: string; answer: string }[];
  banner: { banner_image_url: string };
}

export interface PaymentRow {
  id: number;
  credits: number;
  bonus: number;
  amount: number;
  currency: string;
  amount_stars: number;
  provider: string;
  package: string;
  paid_at: string | null;
  created_at: string;
}

export interface PaymentStart {
  payment_id: number;
  payload: string;
  mode: "test" | "stars";
  invoice_link: string | null;
}

export interface Profile {
  id: number;
  first_name: string | null;
  username: string | null;
  balance: number;
  is_pro: boolean;
  generations: number;
  images: number;
  videos: number;
  favorites_count: number;
  support_url: string;
  roles: string[];
}

export interface GenerateOpts {
  kind: Kind;
  templateId?: number;
  modelId?: number;
  prompt?: string;
  params?: GenParams;
  edit?: boolean;
}

export type Route =
  | { name: "home"; anchor?: string }
  | { name: "explore" }
  | { name: "category"; id: string }
  | { name: "template"; id: number }
  | ({ name: "generate" } & GenerateOpts)
  | { name: "order"; id: number }
  | { name: "history"; filter?: "all" | "photo" | "video" | "fav" }
  | { name: "profile" }
  | { name: "shop" }
  | { name: "tokens" }
  | { name: "payments" }
  | { name: "settings" }
  | { name: "about" }
  | { name: "admin"; page?: string; id?: string };

export interface Nav {
  go: (r: Route) => void;
  replace: (r: Route) => void;
  reset: (r: Route) => void;
  back: () => void;
}
