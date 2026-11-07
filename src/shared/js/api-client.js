export async function fetchPuzzle(category, slug, lang) {
  const response = await fetch(`/api/${category}/${slug}?lang=${lang}`);
  if (!response.ok) throw new Error(`puzzle_http_${response.status}`);
  return response.json();
}

export async function verifyAnswer(category, slug, lang, optionId) {
  const response = await fetch(`/api/${category}/${slug}/verify?lang=${lang}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ option_id: optionId }),
  });
  if (!response.ok) throw new Error(`verify_http_${response.status}`);
  return response.json();
}
