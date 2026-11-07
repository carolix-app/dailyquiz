export interface Env {
  DB: D1Database;
}

export type Locale = "fr" | "en";

const PUBLIC_SQL = `SELECT play_date, payload, metadata FROM puzzles
  WHERE category = ?1 AND game_slug = ?2 AND published = 1 AND play_date <= DATE('now')
  ORDER BY play_date DESC LIMIT 1`;

const VERIFY_SQL = `SELECT play_date, solution FROM puzzles
  WHERE category = ?1 AND game_slug = ?2 AND published = 1 AND play_date <= DATE('now')
  ORDER BY play_date DESC LIMIT 1`;

export function resolveLocale(request: Request): Locale | Response {
  const query = new URL(request.url).searchParams.get("lang");
  if (query === "fr" || query === "en") return query;
  if (query !== null) return Response.json({ error: "invalid_lang" }, { status: 400 });
  const primary = (request.headers.get("Accept-Language") ?? "").toLowerCase().match(/[a-z]{2}/);
  return primary?.[0] === "en" ? "en" : "fr";
}

export function localize(value: unknown, locale: Locale): unknown {
  if (isTranslation(value)) return value[locale] ?? value.fr ?? value.en;
  if (Array.isArray(value)) return value.map((item) => localize(item, locale));
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, inner]) => [key, localize(inner, locale)]),
    );
  }
  return value;
}

export function pathParam(value: string | string[] | undefined): string | null {
  const raw = Array.isArray(value) ? value[0] : value;
  return typeof raw === "string" && /^[a-z0-9-]+$/.test(raw) ? raw : null;
}

export async function readPuzzle(
  db: D1Database,
  category: string,
  slug: string,
  mode: "public" | "verify",
): Promise<Record<string, string> | null> {
  const row = await db
    .prepare(mode === "public" ? PUBLIC_SQL : VERIFY_SQL)
    .bind(category, slug)
    .first<Record<string, string>>();
  return row ?? null;
}

function isTranslation(value: unknown): value is { fr?: string; en?: string } {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.length > 0 &&
    keys.every((key) => key === "fr" || key === "en") &&
    keys.every((key) => typeof (value as Record<string, unknown>)[key] === "string")
  );
}
