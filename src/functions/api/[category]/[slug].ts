import { type Env, localize, pathParam, readPuzzle, resolveLocale } from "../../_lib/http";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const category = pathParam(context.params.category);
  const slug = pathParam(context.params.slug);
  const locale = resolveLocale(context.request);
  if (category === null || slug === null) return Response.json({ error: "not_found" }, { status: 404 });
  if (locale instanceof Response) return locale;

  let row: Record<string, string> | null;
  try {
    row = await readPuzzle(context.env.DB, category, slug, "public");
  } catch (error) {
    console.error("lecture D1 échouée", { category, slug, error });
    return Response.json({ error: "unavailable" }, { status: 503 });
  }
  if (row === null) return Response.json({ error: "not_found" }, { status: 404 });

  try {
    return Response.json({
      payload: localize(JSON.parse(row.payload ?? ""), locale),
      metadata: localize(JSON.parse(row.metadata ?? ""), locale),
    });
  } catch (error) {
    console.error("JSON puzzle illisible", { category, slug, error });
    return Response.json({ error: "invalid_puzzle" }, { status: 500 });
  }
};
