const dec2 = new Intl.NumberFormat("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const dec1 = new Intl.NumberFormat("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const int = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const usd = new Intl.NumberFormat("es-CO", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 4 });

const missing = (v: number | null | undefined): v is null | undefined => v === null || v === undefined || Number.isNaN(v);

export const score = (v: number | null | undefined): string => (missing(v) ? "—" : dec2.format(v));
export const pct = (v: number | null | undefined): string => (missing(v) ? "—" : `${dec1.format(v * 100)} %`);
export const secs = (ms: number | null | undefined): string => (missing(ms) ? "—" : `${dec1.format(ms / 1000)} s`);
export const ms = (v: number | null | undefined): string => (missing(v) ? "—" : `${dec2.format(v)} ms`);
export const tokens = (v: number | null | undefined): string => (missing(v) ? "—" : int.format(v));
export const money = (v: number | null | undefined): string => (missing(v) ? "—" : usd.format(v));

export const MODE_LABEL = { agentic: "Agéntico", linear: "Lineal" } as const;
export const SERIES_COLOR = { agentic: "var(--chart-agentic)", linear: "var(--chart-linear)" } as const;
export const AGENT_LABEL = { docs: "Documentación", research: "Investigación", direct: "Directa" } as const;
export const CATEGORY_LABEL = {
  covered: "Cubierta",
  not_covered: "No cubierta",
  out_of_scope: "Fuera de alcance",
  follow_up: "Seguimiento",
} as const;
