interface IconProps { name: IconName; size?: number; fill?: boolean; className?: string }

export type IconName =
  | "home" | "grid" | "plus" | "heart" | "user" | "search" | "back" | "chevron" | "coin" | "play" | "sparkle"
  | "image" | "trash" | "check" | "close" | "settings" | "help" | "card" | "info" | "lock" | "bell" | "film"
  | "flame" | "man" | "woman" | "child" | "family" | "clock" | "download" | "share" | "crown" | "bolt" | "palette"
  | "refresh" | "sliders" | "video" | "menu" | "logout" | "copy" | "chevron-down" | "diamond"
  | "camera" | "edit" | "upload" | "users" | "chart" | "layers" | "tag" | "bug" | "list" | "shield" | "wand" | "send";

/** Набор линейных иконок в одном стиле (24×24, штрих 1.8). */
export function Icon({ name, size = 22, fill = false, className }: IconProps) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, className, "aria-hidden": true };
  switch (name) {
    case "home": return <svg {...common}><path d="M4 11.5 12 5l8 6.5V19a1 1 0 0 1-1 1h-4v-5H9v5H5a1 1 0 0 1-1-1z" /></svg>;
    case "grid": return <svg {...common}><rect x="4" y="4" width="6.5" height="6.5" rx="1.6" /><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.6" /><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.6" /><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.6" /></svg>;
    case "plus": return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;
    case "heart": return <svg {...common} fill={fill ? "currentColor" : "none"}><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" /></svg>;
    case "user": return <svg {...common}><circle cx="12" cy="8.5" r="3.6" /><path d="M5 20c.6-3.6 3.5-5.5 7-5.5s6.4 1.9 7 5.5" /></svg>;
    case "search": return <svg {...common}><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></svg>;
    case "back": return <svg {...common}><path d="m14.5 5-7 7 7 7" /></svg>;
    case "chevron": return <svg {...common}><path d="m9.5 5 7 7-7 7" /></svg>;
    case "coin": return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5v9M9.5 10c.4-1 1.4-1.5 2.5-1.5s2.3.6 2.3 1.7c0 2.3-4.8 1.4-4.8 3.7 0 1.1 1.2 1.8 2.5 1.8s2.2-.5 2.5-1.5" /></svg>;
    case "play": return <svg {...common} fill="currentColor"><path d="M8 5.5v13l11-6.5z" /></svg>;
    case "sparkle": return <svg {...common} fill={fill ? "currentColor" : "none"}><path d="M12 3c.6 4.8 3.2 7.4 8 8-4.8.6-7.4 3.2-8 8-.6-4.8-3.2-7.4-8-8 4.8-.6 7.4-3.2 8-8z" /></svg>;
    case "image": return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="2.5" /><circle cx="9" cy="10" r="1.6" /><path d="m5 17 4.5-4.5L13 16l2.5-2.5L20 18" /></svg>;
    case "trash": return <svg {...common}><path d="M5 7h14M10 7V5h4v2M7 7l.8 12h8.4L17 7M10.5 11v5M13.5 11v5" /></svg>;
    case "check": return <svg {...common}><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>;
    case "close": return <svg {...common}><path d="m6 6 12 12M18 6 6 18" /></svg>;
    case "settings": return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M18.4 5.6l-1.8 1.8M7.4 16.6l-1.8 1.8" /></svg>;
    case "help": return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M9.6 9.7a2.5 2.5 0 0 1 4.8.8c0 1.7-2.4 2-2.4 3.5M12 17h.01" /></svg>;
    case "card": return <svg {...common}><rect x="3.5" y="6" width="17" height="12" rx="2.5" /><path d="M3.5 10h17M7 14.5h3" /></svg>;
    case "info": return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5M12 8h.01" /></svg>;
    case "lock": return <svg {...common}><rect x="5.5" y="10.5" width="13" height="9" rx="2" /><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" /></svg>;
    case "bell": return <svg {...common}><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5h4" /></svg>;
    case "film": return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="2.5" /><path d="M4 9.5h16M4 14.5h16M9 5v14M15 5v14" /></svg>;
    case "camera": return <svg {...common}><path d="M4 8.5h3l1.5-2h7l1.5 2h3V18a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z" /><circle cx="12" cy="13" r="3.5" /></svg>;
    case "edit": return <svg {...common}><path d="M5 19h4L19 9l-4-4L5 15z" /></svg>;
    case "upload": return <svg {...common}><path d="M12 16V5M7.5 9.5 12 5l4.5 4.5M5 19h14" /></svg>;
    case "users": return <svg {...common}><circle cx="9" cy="9" r="3" /><path d="M3.5 19c.5-3 2.7-4.5 5.5-4.5s5 1.5 5.5 4.5M16 6.5a3 3 0 0 1 0 5.5M17.5 14.8c1.7.5 2.8 1.8 3 4.2" /></svg>;
    case "chart": return <svg {...common}><path d="M5 19V5M5 19h14M9 16v-4M13 16V8M17 16v-6" /></svg>;
    case "layers": return <svg {...common}><path d="m12 4 8.5 4.5L12 13 3.5 8.5zM3.5 12.5 12 17l8.5-4.5M3.5 16.5 12 21l8.5-4.5" /></svg>;
    case "tag": return <svg {...common}><path d="M4 12.5V5a1 1 0 0 1 1-1h7.5l7.5 7.5-8.5 8.5z" /><circle cx="8.5" cy="8.5" r="1.3" /></svg>;
    case "bug": return <svg {...common}><rect x="8" y="8" width="8" height="11" rx="4" /><path d="M9 8a3 3 0 0 1 6 0M4 12h4M16 12h4M5 18l3-2M19 18l-3-2M5 7l3 2M19 7l-3 2" /></svg>;
    case "list": return <svg {...common}><path d="M9 7h11M9 12h11M9 17h11M4.5 7h.01M4.5 12h.01M4.5 17h.01" /></svg>;
    case "shield": return <svg {...common}><path d="M12 3.5 5 6v5.5c0 4.2 2.8 7.3 7 9 4.2-1.7 7-4.8 7-9V6z" /><path d="m9 12 2.2 2.2L15.5 10" /></svg>;
    case "wand": return <svg {...common}><path d="m5 19 9-9M13 6l1-2 1 2 2 1-2 1-1 2-1-2-2-1zM18 13l.6-1.2.6 1.2 1.2.6-1.2.6-.6 1.2-.6-1.2-1.2-.6z" /></svg>;
    case "flame": return <svg {...common}><path d="M12 3c.5 3-2.5 4.5-2.5 7.3 0 1 .5 1.7 1.2 2.2C9 12 7 13.3 7 15.7 7 18.4 9.2 21 12 21s5-2.1 5-5c0-3.3-3-4.6-3-8-1.2.7-2 .8-2-2.5z" /></svg>;
    case "man": return <svg {...common}><circle cx="12" cy="8" r="3.4" /><path d="M5.5 20c.4-3.6 3-5.5 6.5-5.5s6.1 1.9 6.5 5.5M12 14.5v3" /></svg>;
    case "woman": return <svg {...common}><circle cx="12" cy="8.2" r="3.4" /><path d="M8.6 8.4C8.4 5 10 3.5 12 3.5s3.6 1.5 3.4 4.9M5.5 20.5c.5-3.4 3-5.4 6.5-5.4s6 2 6.5 5.4" /></svg>;
    case "child": return <svg {...common}><circle cx="12" cy="12" r="8" /><path d="M9 10.5h.01M15 10.5h.01M9 14c.8 1.1 1.8 1.7 3 1.7s2.2-.6 3-1.7" /></svg>;
    case "family": return <svg {...common}><circle cx="8.5" cy="8" r="2.6" /><circle cx="16.5" cy="9" r="2.2" /><path d="M3.5 19c.4-3 2.4-4.6 5-4.6s4.6 1.6 5 4.6M14.5 14.8c2.4-.3 4.5.9 5 4" /></svg>;
    case "clock": return <svg {...common}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></svg>;
    case "download": return <svg {...common}><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19h14" /></svg>;
    case "share": return <svg {...common}><circle cx="6.5" cy="12" r="2.2" /><circle cx="17" cy="6.5" r="2.2" /><circle cx="17" cy="17.5" r="2.2" /><path d="m8.4 10.9 6.7-3.2M8.4 13.1l6.7 3.2" /></svg>;
    case "crown": return <svg {...common}><path d="m4 8 4 4 4-6 4 6 4-4-1.5 10h-13z" /></svg>;
    case "bolt": return <svg {...common}><path d="M13 3 5.5 13H11l-1 8 7.5-10H12z" /></svg>;
    case "palette": return <svg {...common}><path d="M12 3.5a8.5 8.5 0 0 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.2-1-1.4-1-2.5 0-.9.7-1.4 1.6-1.4H17a3.5 3.5 0 0 0 3.5-3.4C20.5 7 16.7 3.5 12 3.5z" /><path d="M7.5 11h.01M10 7.5h.01M14.5 7.5h.01" /></svg>;
    case "refresh": return <svg {...common}><path d="M19.5 12a7.5 7.5 0 0 1-13 5M4.5 12a7.5 7.5 0 0 1 13-5M17.5 3.5V7H14M6.5 20.5V17H10" /></svg>;
    case "sliders": return <svg {...common}><path d="M5 7h9M18 7h1M5 17h1M10 17h9M14 7v0M10 17v0" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="17" r="2" /></svg>;
    case "chevron-down": return <svg {...common}><path d="m5.5 9.5 6.5 6.5 6.5-6.5" /></svg>;
    case "video": return <svg {...common}><rect x="3.5" y="6" width="17" height="12" rx="3.2" /><path d="m10.5 9.5 4 2.5-4 2.5z" /></svg>;
    case "menu": return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
    case "logout": return <svg {...common}><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4M10 8l-4 4 4 4M6 12h10" /></svg>;
    case "copy": return <svg {...common}><rect x="8.5" y="8.5" width="11" height="11" rx="2" /><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5" /></svg>;
    case "diamond": return <svg {...common}><path d="M12 3.5 20.5 12 12 20.5 3.5 12z" /></svg>;
    case "send": return <svg {...common}><path d="M20 4 10 14M20 4l-6.5 16-3.5-6-6-3.5z" /></svg>;
  }
}
