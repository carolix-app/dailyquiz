import { type Locale, resolveLocale } from "./_lib/http";

export const onRequest: PagesFunction = async (context) => {
  const url = new URL(context.request.url);
  const pathLocale = localeFromPath(url.pathname);

  if (url.pathname === "/") {
    const preferred = readCookie(context.request) ?? languageHeader(context.request);
    return Response.redirect(new URL(`/${preferred}/`, url), 302);
  }

  const response = await context.next();
  if (pathLocale === null || readCookie(context.request) === pathLocale) return response;
  const headers = new Headers(response.headers);
  headers.append("Set-Cookie", `lang=${pathLocale}; Path=/; Max-Age=31536000; SameSite=Lax`);
  return new Response(response.body, { status: response.status, headers });
};

function localeFromPath(pathname: string): Locale | null {
  if (pathname === "/fr" || pathname.startsWith("/fr/")) return "fr";
  if (pathname === "/en" || pathname.startsWith("/en/")) return "en";
  return null;
}

function readCookie(request: Request): Locale | null {
  const match = (request.headers.get("Cookie") ?? "").match(/(?:^|;\s*)lang=(fr|en)(?:;|$)/);
  return match?.[1] === "fr" || match?.[1] === "en" ? match[1] : null;
}

function languageHeader(request: Request): Locale {
  const resolved = resolveLocale(request);
  return resolved instanceof Response ? "fr" : resolved;
}
