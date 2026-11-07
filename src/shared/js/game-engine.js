import { fetchPuzzle, verifyAnswer } from "./api-client.js";
import { readGame, rememberGame } from "./storage.js";

const root = document.body;
const category = root.dataset.category ?? "";
const slug = root.dataset.slug ?? "";
const lang = root.dataset.lang === "en" ? "en" : "fr";
const gameKey = `${category}/${slug}`;
const ui = await fetch(`/shared/i18n/${lang}.json`).then((response) => response.json());

const status = document.querySelector("#status");
const prompt = document.querySelector("#prompt");
const options = document.querySelector("#options");
const streak = document.querySelector("#streak");
const saved = readGame(gameKey);
streak.textContent = `${ui.streak} : ${saved.streak}`;

try {
  const puzzle = await fetchPuzzle(category, slug, lang);
  const playDate = String(puzzle.metadata?.seed ?? "").slice(-10);
  prompt.textContent = puzzle.payload.prompt;
  status.textContent = `${ui.attempts} : ${puzzle.payload.max_attempts}`;
  let left = puzzle.payload.max_attempts;
  for (const option of puzzle.payload.options) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = option.label;
    button.addEventListener("click", async () => {
      if (left <= 0) return;
      left -= 1;
      const result = await verifyAnswer(category, slug, lang, option.id);
      button.disabled = true;
      button.classList.add(result.correct ? "correct" : "wrong");
      status.textContent = result.correct ? ui.correct : `${ui.incorrect} ${ui.attempts} : ${left}`;
      if (result.correct || left === 0) {
        prompt.textContent = result.solution.explanation;
        for (const node of options.querySelectorAll("button")) node.disabled = true;
        const game = rememberGame(gameKey, playDate, result.correct, result.solution.explanation);
        streak.textContent = `${ui.streak} : ${game.streak}`;
      }
    });
    options.append(button);
  }
} catch (error) {
  console.error("défi indisponible", error);
  status.textContent = ui.error;
}
