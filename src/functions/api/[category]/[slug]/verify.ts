import { type Env, localize, pathParam, readPuzzle, resolveLocale } from "../../../_lib/http";

interface SolutionRow {
  correct_option_id?: unknown;
  explanation?: unknown;
  distance_tolerance_km?: unknown;
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const category = pathParam(context.params.category);
  const slug = pathParam(context.params.slug);
  const locale = resolveLocale(context.request);
  if (category === null || slug === null) return Response.json({ error: "not_found" }, { status: 404 });
  if (locale instanceof Response) return locale;

  let body: unknown;
  try {
    body = await context.request.json();
  } catch (error) {
    console.error("corps verify illisible", error);
    return Response.json({ error: "invalid_json" }, { status: 400 });
  }
  const optionId =
    body !== null && typeof body === "object" && "option_id" in body ? body.option_id : null;
  if (typeof optionId !== "string" || optionId.length === 0) {
    return Response.json({ error: "invalid_option" }, { status: 400 });
  }

  let row: Record<string, string> | null;
  try {
    row = await readPuzzle(context.env.DB, category, slug, "verify");
  } catch (error) {
    console.error("lecture D1 échouée", { category, slug, error });
    return Response.json({ error: "unavailable" }, { status: 503 });
  }
  if (row === null) return Response.json({ error: "not_found" }, { status: 404 });

  let solution: SolutionRow;
  try {
    solution = JSON.parse(row.solution ?? "") as SolutionRow;
  } catch (error) {
    console.error("solution illisible", { category, slug, error });
    return Response.json({ error: "invalid_puzzle" }, { status: 500 });
  }
  if (typeof solution.correct_option_id !== "string") {
    console.error("solution sans correct_option_id", { category, slug });
    return Response.json({ error: "invalid_puzzle" }, { status: 500 });
  }

  return Response.json({
    correct: optionId === solution.correct_option_id,
    solution: localize(solution, locale),
  });
};
