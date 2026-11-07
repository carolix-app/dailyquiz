const KEY = "dailyquiz:v1";

export function readGame(gameKey) {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "{}");
    const game = parsed.games?.[gameKey];
    return game && typeof game === "object" ? game : { streak: 0, lastPlayed: null, history: {} };
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof DOMException) {
      console.error("état joueur illisible", error);
      return { streak: 0, lastPlayed: null, history: {} };
    }
    throw error;
  }
}

export function rememberGame(gameKey, playDate, solved, explanation) {
  const state = readAll();
  const game = state.games[gameKey] ?? { streak: 0, lastPlayed: null, history: {} };
  if (game.history[playDate]) return game;
  const yesterday = shift(playDate, -1);
  game.streak = solved ? (game.lastPlayed === yesterday && game.streak > 0 ? game.streak + 1 : 1) : 0;
  game.lastPlayed = playDate;
  game.history[playDate] = { solved, explanation };
  state.games[gameKey] = game;
  localStorage.setItem(KEY, JSON.stringify(state));
  return game;
}

function readAll() {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || "{}");
    if (!parsed.games || typeof parsed.games !== "object") return { games: {} };
    return parsed;
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof DOMException) return { games: {} };
    throw error;
  }
}

function shift(iso, days) {
  const [year, month, day] = iso.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1, day));
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
