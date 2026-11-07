-- DailyQuiz, schéma initial.
-- published = 1 expose le puzzle. L'API exige en plus play_date <= date UTC du jour.
-- Les textes JSON restent multilingues ; la locale est résolue dans la Pages Function.

PRAGMA foreign_keys = ON;

CREATE TABLE puzzles (
    id INTEGER PRIMARY KEY,
    play_date TEXT NOT NULL CHECK (play_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    category TEXT NOT NULL CHECK (category IN ('geo', 'foot', 'movies')),
    game_slug TEXT NOT NULL CHECK (length(game_slug) > 0),
    schema_version TEXT NOT NULL,
    payload TEXT NOT NULL CHECK (json_valid(payload)),
    solution TEXT NOT NULL CHECK (json_valid(solution)),
    metadata TEXT NOT NULL CHECK (json_valid(metadata)),
    published INTEGER NOT NULL DEFAULT 0 CHECK (published IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (play_date, category, game_slug)
);

CREATE INDEX idx_puzzles_public_lookup
    ON puzzles (category, game_slug, play_date DESC)
    WHERE published = 1;

CREATE INDEX idx_puzzles_play_date ON puzzles (play_date);

CREATE TABLE play_stats (
    puzzle_id INTEGER PRIMARY KEY,
    plays INTEGER NOT NULL DEFAULT 0 CHECK (plays >= 0),
    solves INTEGER NOT NULL DEFAULT 0 CHECK (solves >= 0),
    attempts_total INTEGER NOT NULL DEFAULT 0 CHECK (attempts_total >= 0),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (puzzle_id) REFERENCES puzzles (id) ON DELETE CASCADE
);

CREATE TABLE generation_runs (
    id INTEGER PRIMARY KEY,
    play_date TEXT NOT NULL CHECK (play_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    generator_version TEXT NOT NULL,
    puzzles_written INTEGER NOT NULL DEFAULT 0 CHECK (puzzles_written >= 0),
    detail TEXT
);

CREATE INDEX idx_generation_runs_play_date ON generation_runs (play_date);
