/** Числа и даты по-русски: «1 240 токенов», «14 октября 2026». */
export const nf = (n: number): string => new Intl.NumberFormat("ru-RU").format(Math.round(n));

export function plural(n: number, forms: [string, string, string]): string {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return forms[2];
  if (b > 1 && b < 5) return forms[1];
  return b === 1 ? forms[0] : forms[2];
}

export const tokensText = (n: number): string => `${nf(n)} ${plural(n, ["токен", "токена", "токенов"])}`;
export const pct = (v: number | null | undefined): string => (v === null || v === undefined ? "—" : `${v.toLocaleString("ru-RU")}%`);

export function fmtDate(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" }) : "—";
}
export function fmtShort(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "2-digit" }) : "—";
}
export function fmtTime(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";
}
export function ago(iso: string | null | undefined): string {
  if (!iso) return "—";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "только что";
  if (s < 3600) return `${Math.floor(s / 60)} мин. назад`;
  if (s < 86400) return `${Math.floor(s / 3600)} ч. назад`;
  return `${Math.floor(s / 86400)} дн. назад`;
}
export const money = (n: number | null | undefined, unit = "Stars"): string => (n === null || n === undefined ? "Нет данных" : `${nf(n)} ${unit}`);
export const usd = (n: number): string => `$${n.toLocaleString("ru-RU", { maximumFractionDigits: 2 })}`;
