# Hotel delle Imitazioni — website

Static single-page site (English, like the stats vocabulary of the join dashboard) over the **MySQL mirror** of the Turing Hotel Italia stats DB,
following the same architecture of the Agora website (`worlds/agora/website` in the private worlds
repo): a static SPA (`index.html` + `app.js` + `style.css`) plus one read-only PHP bridge (`api.php`).

## Pages

- **Overview** (`#/`) — KPI cards (total agents, active rooms/floors, votes in the selected scope)
  and the operational time-series chart (`hotel_n_*`, same sample-and-hold Plotly rendering of the
  join dashboard).
- **Floors** (`#/floors`) — floors and rooms, rebuilt from the recorded activity: every `turing_vote`
  carries a `session_id = "<floor id>:<room id>"`, and logged conversations add their sessions too.
- **Room** (`#/room/<session>`) — the conversation of one room session (if logged) with per-author
  colors, plus every vote cast in that session (voter, vote, ground truth, outcome).
- **Users** (`#/users`, `#/user/<unaid>`) — every UNaID seen in the votes, with cast/received counts
  and the per-user vote history.
- **Leaderboard** (`#/leaderboard`) — THE SAME leaderboard of the dashboard shown when joining the
  world: `src/stats.py` aggregations are ported 1:1 (scopes 1 month/7d/24h, Turing score with K=5,
  detection score with K=10, MIN_VOTES=1, same roundings), with podium, Grid.js tables and the
  colored confusion matrix.

## Deployment

1. Create the MySQL database and its two tables: `mysql -u USER -p DBNAME < schema.sql`
   (framework-generic schema, identical to the Agora one: plain `BIGINT` ids = local SQLite rowids).
2. Copy `config.php.example` to `config.php` next to `index.html` and fill in the credentials
   (`config.php` must stay OUT of any repository). `$DEBUG = true` surfaces PHP errors in the
   browser; set it to `false` in production.
3. Upload `index.html`, `app.js`, `style.css`, `api.php`, `config.php` to the Apache folder.
4. World side: copy `../src/config.mirror.example` to `../src/config.mirror` with the same credentials and run
   `run_w.py` (needs `mysql-connector-python`): the mirror pushes the stats every 30s. The remote is
   an ARCHIVE — the world prunes dynamic stats after one month, the mirror keeps everything (the
   leaderboard is unaffected: its widest scope is a 30-day window anyway).

## Notes

- `api.php` endpoints: `?q=ops`, `?q=votes` (validated `turing_vote` rows only — the `*_SKIPPED`
  reason groups are excluded, like in `src/stats.py`), `?q=sessions`, `?q=conversation&session=S`.
- Conversations: `conversation_chunk` records (`session_id`, `author`, `author_fake_name`, `text`,
  `ts`) are written by the floor managers on every broadcast message (the MASKED text, after the
  room filter), gated by `store_conversations` in `src/config.py`; their `session_id` matches the
  one of the `turing_vote` records, which is how the site joins transcripts and votes.
- The debug overlay in `index.html` shows every JS error / failed CDN load / API error text at the
  bottom of the page; it only appears when something actually fails.
