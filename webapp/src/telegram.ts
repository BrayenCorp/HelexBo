interface TgUser { id: number; first_name?: string; photo_url?: string }
interface TgWebApp {
  initData: string;
  initDataUnsafe?: { user?: TgUser };
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  openInvoice(url: string, cb?: (status: "paid" | "cancelled" | "failed" | "pending") => void): void;
  openTelegramLink?(url: string): void;
  openLink?(url: string): void;
  BackButton: { show(): void; hide(): void; onClick(cb: () => void): void; offClick(cb: () => void): void };
  HapticFeedback?: { notificationOccurred(type: "success" | "error" | "warning"): void; impactOccurred?(style: "light" | "medium"): void };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TgWebApp };
  }
}

export const tg: TgWebApp | undefined = window.Telegram?.WebApp;

export function initTelegram(): void {
  if (!tg) return;
  tg.ready();
  tg.expand();
  tg.setHeaderColor?.("#000000");
  tg.setBackgroundColor?.("#000000");
}

export function haptic(type: "success" | "error" | "warning"): void {
  tg?.HapticFeedback?.notificationOccurred(type);
}

export const tgPhoto: string | undefined = tg?.initDataUnsafe?.user?.photo_url;

export function openExternal(url: string): void {
  if (tg?.openTelegramLink && /^https:\/\/t\.me\//.test(url)) tg.openTelegramLink(url);
  else if (tg?.openLink) tg.openLink(url);
  else window.open(url, "_blank", "noopener");
}
