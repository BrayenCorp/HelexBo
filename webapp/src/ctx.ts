import { createContext, useContext } from "react";
import type { Me, Nav } from "./types";

export interface AppState {
  me: Me;
  nav: Nav;
  refreshMe: () => void;
  toggleFavorite: (kind: "template" | "order", id: number) => void;
  /** Вход через Telegram. Возвращает true, если пользователь зарегистрирован (был или стал). */
  ensureRegistered: () => Promise<boolean>;
}

export const AppCtx = createContext<AppState | null>(null);

export function useApp(): AppState {
  const v = useContext(AppCtx);
  if (!v) throw new Error("AppCtx отсутствует");
  return v;
}

/** Короткое уведомление внизу экрана. */
export function showToast(message: string): void {
  window.dispatchEvent(new CustomEvent("nolla-toast", { detail: message }));
}
