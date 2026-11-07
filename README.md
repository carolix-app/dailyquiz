# DailyQuiz

Hub de jeux quotidiens. La logique est dans `engine/` (Python, sans réseau). La CI écrit D1. Cloudflare Pages sert le site et l'API.

```
engine/     puzzles, validation, générateurs
scripts/    lot quotidien, validation, SQL
schema/     migrations et seed local
src/        pages /fr /en, assets, Pages Functions
tests/      pytest, dont « le puzzle est résolvable »
```

La frontière du jour est UTC. `published = 1` et `play_date <= date('now')` exposent un puzzle. GET `/api/{category}/{slug}?lang=fr|en` renvoie `payload` et `metadata` localisés, jamais `solution`. POST `/api/{category}/{slug}/verify` compare `option_id` et renvoie `{ correct, solution }`.

`/` redirige vers `/fr/` ou `/en/` selon le cookie `lang`, puis `Accept-Language`.

```bash
pip install pytest
pytest
python -m scripts.generate_daily_batch --date 2026-11-07 --output dist/batch.json --seed-output schema/seed/dev_seed.sql
```

Secrets Actions : `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_D1_DATABASE_ID`. Le déploiement copie `src/` vers `dist/` sans les Functions, et expose `src/functions` comme `functions/` à la racine, là où Wrangler les compile.

Validation manuelle dans `engine/core/validators.py` (pas de Pydantic). `generated_at` est figé à minuit UTC de `play_date` pour qu'un même jour redonne le même document. Le schéma SQL de `0001_init.sql` est une proposition : remplace-le si tu as le SQL définitif.
