/** Spanish (es-CO) formatting helpers for the UI. */
const seconds = new Intl.NumberFormat("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("es-CO");
const usd = new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", minimumFractionDigits: 4, maximumFractionDigits: 4 });
const date = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short" });

export const fmtSeconds = (ms: number): string => `${seconds.format(ms / 1000)} s`;
export const fmtInt = (n: number): string => integer.format(n);
export const fmtUsd = (n: number): string => usd.format(n);

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  return d.toDateString() === today.toDateString() ? "hoy" : date.format(d);
}

/** Short form of a thread id for the header chip: `3f9c…a21`. */
export const shortId = (id: string): string => (id.length > 10 ? `${id.slice(0, 4)}…${id.slice(-3)}` : id);

/** URL without the scheme and with the middle of the path elided: `odoo.com/…/orm.html#computed`. */
export function shortUrl(url: string): string {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    const host = u.hostname.replace(/^www\./, "");
    const tail = parts.at(-1) ?? "";
    const path = parts.length > 1 ? `/…/${tail}` : `/${tail}`;
    return `${host}${path}${u.hash}`;
  } catch {
    return url;
  }
}
