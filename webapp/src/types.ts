export type Kind = "photo" | "video" | "audio";

export interface Favorites { templates: number[]; orders: number[] }

export interface Me {
  id: number;
  created_at: string | null;
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
  prefs: Prefs;
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
  stage: string | null;
  section: string;
  tool: string;
  model_name: string | null;
  group: "images" | "video" | "audio" | "effects" | "avatars" | "marketing";
  frames: string[];
  avatar_id: number | null;
  emoji?: string | null;
}

export interface GenParams {
  format?: string;
  quality?: string;
  style?: string;
  lighting?: string;
  camera?: string;
  resolution?: string;
  duration?: string;
  seed?: number;
  negative?: string;
  voice?: string;
  emotion?: string;
  tone?: string;
  speed?: number;
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
  slug?: string;
  tags?: string[];
  needs_image?: boolean;
  text_only?: boolean;
  is_new?: boolean;
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
  demo_method?: string | null;
}

export interface PaymentStart {
  payment_id: number;
  payload: string;
  mode: "test" | "stars";
  invoice_link: string | null;
}

export interface Profile {
  id: number;
  created_at?: string | null;
  first_name: string | null;
  username: string | null;
  balance: number;
  is_pro: boolean;
  generations: number;
  images: number;
  videos: number;
  audios?: number;
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
  /** Результат прошлой работы как референс. */
  refOrderId?: number;
  avatarId?: number;
}

export type Section = "effect" | "trend" | "photoshoot" | "prompt" | "marketing" | "mtool" | "avatar";

export interface Tag { id: string; label: string; count: number }

export interface Prefs {
  language: string;
  default_model_id: number | null;
  ratio: string;
  quality: string;
  autodownload: boolean;
  interests: string[];
  notify: boolean;
}

export interface CatalogItem {
  id: number;
  title: string;
  description: string;
  section: Section;
  tag: string;
  tag_label: string;
  tool: string;
  kind: Kind;
  price_credits: number;
  required: { code: string; label: string }[];
  needs_avatar: boolean;
  preview_url: string;
  preview_kind: "image" | "video";
  is_popular: boolean;
  featured: boolean;
  uses: number;
  slug: string;
  prompt?: string;
  supported_models?: string[];
}

export interface PlatformMeta {
  sections: Record<string, { tags: Tag[]; total: number; popular: number }>;
  models: Record<string, { tags: Tag[] }>;
  materials: Record<string, string>;
  audio: { voices: { id: string; label: string }[]; emotions: { id: string; label: string }[]; tones: { id: string; label: string }[] };
  quick_actions: { title: string; text: string; action: Record<string, unknown> }[];
}

export interface PlatformHome {
  popular: CatalogItem[];
  ideas: CatalogItem[];
  trends: CatalogItem[];
  photoshoots: CatalogItem[];
  recent: Order[];
  demo: boolean;
}

export interface SearchGroup { type: string; label: string; items: { id: number; title: string; subtitle: string; slug?: string; kind?: Kind }[] }

export interface AvatarRow {
  id: number;
  name: string;
  status: "queued" | "analyzing" | "creating" | "ready" | "failed";
  status_label: string;
  photo_count: number;
  has_cover: boolean;
  created_at: string;
  is_stub: boolean;
  error: string | null;
}

export interface Quote { base: number; free: boolean; count: number; total: number; balance: number; enough: boolean }

export interface Integrations {
  endpoint: string;
  clients: { name: string; how: string }[];
  tools: { name: string; title: string; description: string }[];
  tokens: { id: number; label: string; created_at: string; last_used_at: string | null }[];
}

export type HistoryFilter = "all" | "images" | "video" | "audio" | "effects" | "avatars" | "marketing" | "fav";

export type Route =
  | { name: "home" }
  | { name: "create"; kind?: Kind; templateId?: number; modelId?: number; prompt?: string; params?: GenParams; refOrderId?: number; avatarId?: number; slug?: string }
  | { name: "models"; kind?: Kind }
  | { name: "effects"; tag?: string }
  | { name: "tool"; slug: string; refOrderId?: number }
  | { name: "ideas" }
  | { name: "trends" }
  | { name: "photoshoots"; tag?: string }
  | { name: "avatars" }
  | { name: "prompts" }
  | { name: "marketing" }
  | { name: "order"; id: number }
  | { name: "history"; filter?: HistoryFilter }
  | { name: "profile" }
  | { name: "settings" }
  | { name: "balance" }
  | { name: "payments" }
  | { name: "integrations" }
  | { name: "admin"; page?: string; id?: string };

export interface Nav {
  go: (r: Route) => void;
  replace: (r: Route) => void;
  reset: (r: Route) => void;
  back: () => void;
}
