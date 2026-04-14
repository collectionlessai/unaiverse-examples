"""
Turing Hotel 2.0 - WStats
==========================
Stats schema and leaderboard UI for the Turing Hotel world.

Schema overview
---------------
OUTER dynamic (peer_id = group key):

  turing_vote       - one record per validated A-judges-B classification.
                      peer_id = votee real <unaid> (nodeOwner@email/nodeName)
                      Value shape:
                        {
                          "voter":            "<unaid>",
                          "vote":             "human" | "ai",  # this vote is parsed by the floor manager from the raw vote
                          "ground_truth":     "human" | "ai",
                          "session_id":       "<floor.peer_id>:<room.uuid>",
                          "floor_manager":    "<peer_id>",
                          "hotel_manager":    "<peer_id>",
                          "msgs_from_votee":  <int>,
                          "msgs_from_voter":  <int>,
                        }
                      Invalid votes are NEVER written: the Floor Manager sends valid votes
                      to the Hotel Manager that sent there that peer. Then the Hotel Manager
                      stores the valid vote and sends it to the world.

  conversation_chunk - per-message transcript chunk (debug only).
                       peer_id = "<room.uuid>:<activation_ts>" session id.
                       Gated by STORE_CONVERSATIONS; never read by plot() sent by the agent himself.
                       Value shape:
                         {
                           "session_id":       "<floor.peer_id>:<room.uuid>",
                           "author":           "<unaid>",
                           "author_fake_name": "<str>",
                           "text":             "<str>",
                           "ts":               <ts_ms>,
                         }

  hotel_n_*         - one scalar stat per hotel operational metric.
                      peer_id = hotel manager real peer id.
                      Written periodically by the hotel manager.

AGENT dynamic (peer_id = floor manager's own peer id, implicit):

  floor_n_*         - one scalar stat per floor operational metric.
                      Written by each floor manager about itself.

WORLD static (ungrouped, non-derivable world-population facts):

  n_total_agents, n_humans, n_ais.

Derived at plot time (not stored):
  n_total_votes, n_active_rooms, n_active_floors - computed inside the TTL
  cache from raw turing_vote and hotel_n_* records.

Grouping key note
-----------------
The framework's peer_id parameter is used as a generic group key here.
This matches the existing convention in agent.py where room.uuid is already
passed as peer_id for room_activation / room_message / etc.  A formal rename
to group_id is deferred to a separate framework PR.
"""

import html
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from unaiverse.stats import Stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_MONTHS = 1
_SCOPE_WINDOWS_MS: dict[str, int | None] = {
    "max": _MAX_MONTHS * 30 * 24 * 3600 * 1000,
    "7d": 7 * 24 * 3600 * 1000,
    "24h": 24 * 3600 * 1000,
}
_SCOPE_LABELS: dict[str, str] = {
    "max": f"{_MAX_MONTHS} month{'' if _MAX_MONTHS == 1 else 's'} (Max)",
    "7d": "7 days",
    "24h": "24 hours",
}
_MIN_VOTES = 3  # suppress leaderboard rows with fewer votes
_PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"]
_HOTEL_OPS_STATS = (
    "hotel_n_floors_active",
    "hotel_n_rooms_active",
    "hotel_n_rooms_overbooked",
    "hotel_n_agents_present",
    "hotel_n_agents_waiting",
)
_HOTEL_OPS_LABELS = {
    "hotel_n_floors_active":    "Floors active",
    "hotel_n_rooms_active":     "Rooms active",
    "hotel_n_rooms_overbooked": "Rooms overbooked",
    "hotel_n_agents_present":   "Agents in rooms",
    "hotel_n_agents_waiting":   "Agents waiting",
}


# ---------------------------------------------------------------------------
# WStats
# ---------------------------------------------------------------------------
class WStats(Stats):
    """Custom Stats class for the Turing Hotel 2.0 world."""

    # ------------------------------------------------------------------ schema

    STORE_CONVERSATIONS: bool = True
    LEADERBOARD_CACHE_TTL_SECONDS: int = 60

    # World population is tracked as static facts via CUSTOM_WORLD_STATS_STATIC_SCHEMA;
    # the base class dynamic counters (world_masters, world_agents, …) are not used here.
    CORE_WORLD_STATS_DYNAMIC_SCHEMA: dict = {}

    CUSTOM_OUTER_STATS_DYNAMIC_SCHEMA = {
        "turing_vote":              (dict, None),
        "conversation_chunk":       (dict, None),
        "hotel_n_floors_active":    (int, 0),
        "hotel_n_rooms_active":     (int, 0),
        "hotel_n_rooms_overbooked": (int, 0),
        "hotel_n_agents_present":   (int, 0),
        "hotel_n_agents_waiting":   (int, 0),
    }

    CUSTOM_AGENT_STATS_DYNAMIC_SCHEMA = {
        # Floor operational metrics (scalar → val_num in SQLite, indexed).
        "floor_n_rooms_active": (int, 0),
        "floor_n_guests":       (int, 0),
        "floor_churn_count":    (int, 0),
    }

    CUSTOM_WORLD_STATS_STATIC_SCHEMA = {
        # World-population stats written by the world.
        "n_total_agents":  (int, 0),
        "n_humans":        (int, 0),
        "n_ais":           (int, 0),
    }

    # ------------------------------------------------------------------- init

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # In-memory TTL cache for computed leaderboard aggregates.
        self._leaderboard_cache: dict | None = None
        self._leaderboard_cache_ts_ms: int = 0

    # ============================================================ cache layer

    def _leaderboard_is_fresh(self) -> bool:
        if self._leaderboard_cache is None:
            return False
        age_ms = int(time.time() * 1000) - self._leaderboard_cache_ts_ms
        return age_ms < self.LEADERBOARD_CACHE_TTL_SECONDS * 1000

    def _refresh_aggregates_if_stale(self) -> dict:
        if not self._leaderboard_is_fresh():
            self._refresh_aggregates()
        return self._leaderboard_cache  # type: ignore[return-value]

    def _refresh_aggregates(self) -> None:
        now_ms = int(time.time() * 1000)
        votes = self._fetch_vote_history()
        ops = self._fetch_hotel_ops_series()

        buckets = self._bucket_by_scope(votes, now_ms)

        scopes: dict[str, dict] = {}
        for scope_key, scope_votes in buckets.items():
            scopes[scope_key] = {
                "confusion": self._compute_confusion_matrix(scope_votes),
                "votee": self._compute_votee_leaderboard(scope_votes, _MIN_VOTES),
                "voter": self._compute_voter_leaderboard(scope_votes, _MIN_VOTES),
                "n_total_votes": len(scope_votes),
            }

        global_counters = self._derive_global_counters(ops, now_ms)

        self._leaderboard_cache = {
            "scopes":    scopes,
            "ops_series": ops,
            **global_counters,
        }
        self._leaderboard_cache_ts_ms = now_ms

    # =========================================================== data handling

    def _fetch_vote_history(self) -> list[dict]:
        """Return all turing_vote records from SQLite as parsed dicts."""
        if not self.is_world:
            return []
        rows = self._db_conn.execute(
            "SELECT timestamp, peer_id, val_json "
            "FROM dynamic_stats "
            "WHERE stat_name = 'turing_vote' "
            "ORDER BY timestamp ASC"
        ).fetchall()
        votes = []
        for ts, votee_peer_id, val_json in rows:
            try:
                record = json.loads(val_json)
                record["_ts"] = ts
                record["_votee_peer_id"] = votee_peer_id
                votes.append(record)
            except (json.JSONDecodeError, TypeError):
                pass
        return votes

    def _fetch_hotel_ops_series(self) -> dict[str, list[tuple[int, int]]]:
        """Return hotel operational time-series from SQLite.
        Returns {stat_name: [(ts_ms, val), ...]} sorted by ts ascending.
        """
        if not self.is_world:
            return {}
        placeholders = ",".join("?" * len(_HOTEL_OPS_STATS))
        rows = self._db_conn.execute(
            f"SELECT timestamp, stat_name, val_num "
            f"FROM dynamic_stats "
            f"WHERE stat_name IN ({placeholders}) "
            f"ORDER BY timestamp ASC",
            _HOTEL_OPS_STATS,
        ).fetchall()
        series: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for ts, stat_name, val_num in rows:
            if val_num is not None:
                series[stat_name].append((ts, int(val_num)))
        return dict(series)

    @staticmethod
    def _bucket_by_scope(
        votes: list[dict], now_ms: int
    ) -> dict[str, list[dict]]:
        """Split vote list into max / 7d / 24h buckets in one pass."""
        buckets: dict[str, list[dict]] = {k: [] for k in _SCOPE_WINDOWS_MS}
        for v in votes:
            ts = v.get("_ts", 0)
            for scope, window_ms in _SCOPE_WINDOWS_MS.items():
                if window_ms is None or (now_ms - ts) <= window_ms:
                    buckets[scope].append(v)
        return buckets
    
    def _prune_db(self):
        if not self.is_world or self._db_conn is None:
            return
        # Custom pruning: delete all dynamic records older than the max scope window.
        max_window_ms = _SCOPE_WINDOWS_MS['max']
        cutoff_ts = int(time.time() * 1000) - max_window_ms
        self._db_conn.execute(
            "DELETE FROM dynamic_stats WHERE timestamp < ?",
            (cutoff_ts,)
        )
        # commit is called from Stats.save_to_disk() which is where _prune_db is called from, so no need to commit here.

    # ======================================================== aggregation

    @staticmethod
    def _compute_confusion_matrix(votes: list[dict]) -> dict:
        """2x2 confusion matrix: ground_truth x vote, counts + row %."""
        truths = ("human", "ai")
        vote_cols = ("human", "ai")
        counts: dict[str, dict[str, int]] = {t: {v: 0 for v in vote_cols} for t in truths}
        for rec in votes:
            gt = rec.get("ground_truth")
            vt = rec.get("vote")
            if gt in counts and vt in vote_cols:
                counts[gt][vt] += 1

        pct: dict[str, dict[str, float]] = {t: {v: .0 for v in vote_cols} for t in truths}
        for gt in truths:
            row_total = sum(counts[gt].values())
            for vt in vote_cols:
                pct[gt][vt] = counts[gt][vt] / row_total * 100 if row_total else 0.0
        return {"counts": counts, "pct": pct}

    @staticmethod
    def _compute_votee_leaderboard(
        votes: list[dict], min_votes: int
    ) -> list[dict]:
        """Per-AI-votee stats. Primary metric: Turing score — fooling rate
        weighted by average conversation length. Fooling over more messages is
        harder (more exposure), so a longer conversation at the same fooling
        rate scores higher. Formula: fooling_rate * avg_msgs / (avg_msgs + K)
        with K=5. Sorted by Turing score descending."""
        _K = 5
        by_votee: dict[str, dict] = {}
        for rec in votes:
            vid = rec.get("_votee_peer_id") or ""
            gt = rec.get("ground_truth")
            if not vid or gt != "ai":   # AI-only leaderboard
                continue
            entry = by_votee.setdefault(vid, {
                "peer_id": vid,
                "votes": 0,
                "fooling": 0,
                "msgs_total": 0,
            })
            entry["votes"] += 1
            vt = rec.get("vote")
            if vt and vt != gt:
                entry["fooling"] += 1
            entry["msgs_total"] += rec.get("msgs_from_votee", 0)

        rows = []
        for vid, e in by_votee.items():
            if e["votes"] < min_votes:
                continue
            fooling_rate = e["fooling"] / e["votes"] * 100
            avg_msgs = e["msgs_total"] / e["votes"]
            turing_score = fooling_rate * avg_msgs / (avg_msgs + _K)
            rows.append({
                "peer_id":      vid,
                "votes":        e["votes"],
                "fooling_rate": round(fooling_rate, 1),
                "avg_msgs":     round(avg_msgs, 1),
                "turing_score": round(turing_score, 1),
            })
        rows.sort(key=lambda r: r["turing_score"], reverse=True)
        return rows

    @staticmethod
    def _compute_voter_leaderboard(
        votes: list[dict], min_votes: int
    ) -> list[dict]:
        """Per-voter stats using binary classification metrics.
        Positive class = "human". Sorted by detection_score descending.
        detection_score = f1 * votes / (votes + K) with K=10 — rewards
        sustained accuracy over many votes, mirroring the Turing score."""
        _K = 10
        # Build voter nature lookup: when a voter also appears as a votee,
        # their ground_truth reveals whether they are human or ai.
        nature_lookup: dict[str, str] = {}
        for rec in votes:
            votee_id = rec.get("_votee_peer_id") or ""
            gt = rec.get("ground_truth")
            if votee_id and gt in ("human", "ai"):
                nature_lookup[votee_id] = gt

        by_voter: dict[str, dict] = {}
        for rec in votes:
            vid = rec.get("voter") or ""
            if not vid:
                continue
            entry = by_voter.setdefault(vid, {
                "peer_id": vid,
                "total": 0,
                "tp": 0, "fp": 0, "tn": 0, "fn": 0,
            })
            entry["total"] += 1
            gt = rec.get("ground_truth")
            vt = rec.get("vote")
            if not vt or vt not in ("human", "ai"):
                continue
            if gt == "human" and vt == "human":
                entry["tp"] += 1
            elif gt == "ai" and vt == "human":
                entry["fp"] += 1
            elif gt == "ai" and vt == "ai":
                entry["tn"] += 1
            elif gt == "human" and vt == "ai":
                entry["fn"] += 1

        def _prf(tp: int, fp: int, tn: int, fn: int) -> tuple:
            prec = tp / (tp + fp) if (tp + fp) else None
            rec_ = tp / (tp + fn) if (tp + fn) else None
            f1 = (
                2 * prec * rec_ / (prec + rec_)
                if (prec is not None and rec_ is not None and (prec + rec_) > 0)
                else None
            )
            return prec, rec_, f1

        def _fmt(v: float | None) -> str:
            return f"{v * 100:.1f}" if v is not None else None  # type: ignore[return-value]

        rows = []
        for vid, e in by_voter.items():
            if e["total"] < min_votes:
                continue
            prec, rec_, f1 = _prf(e["tp"], e["fp"], e["tn"], e["fn"])
            raw_detection = (f1 * e["total"] / (e["total"] + _K)) if f1 is not None else None
            sort_detection = raw_detection if raw_detection is not None else -1.0
            rows.append({
                "peer_id":         vid,
                "nature":          nature_lookup.get(vid, "-"),
                "votes":           e["total"],
                "precision":       _fmt(prec),
                "recall":          _fmt(rec_),
                "f1":              _fmt(f1),
                "detection_score": round(raw_detection * 100, 1) if raw_detection is not None else None,
                "_sort_detection": sort_detection,
            })
        rows.sort(key=lambda r: r["_sort_detection"], reverse=True)
        return rows

    @staticmethod
    def _derive_global_counters(
        ops_series: dict[str, list[tuple[int, int]]], refreshed_ms: int
    ) -> dict:
        def _latest(stat: str) -> int:
            pts = ops_series.get(stat)
            return pts[-1][1] if pts else 0

        return {
            "n_active_rooms":   _latest("hotel_n_rooms_active"),
            "n_active_floors":  _latest("hotel_n_floors_active") if "hotel_n_floors_active" in ops_series else 0,
            "refreshed_ms":     refreshed_ms,
        }

    # ============================================================= rendering

    @staticmethod
    def _esc(v: Any) -> str:
        return html.escape(str(v))

    def _render_summary_bar(
        self,
        static_stats: dict,
        scope_counters: dict[str, dict],
        global_counters: dict,
    ) -> str:
        """Summary cards: persistent static + scope-dependent + global derived."""
        def _card(label: str, value: Any, extra_class: str = "") -> str:
            cls = f"card{' ' + extra_class if extra_class else ''}"
            return f'<div class="{cls}"><span class="card-val">{self._esc(value)}</span><span class="card-lbl">{self._esc(label)}</span></div>'

        static_cards = "".join([
            _card("Total agents",  static_stats.get("n_total_agents", 0)),
            # _card("Humans",        static_stats.get("n_humans", 0)),
            # _card("AIs",           static_stats.get("n_ais", 0)),
            _card("Active rooms",  global_counters.get("n_active_rooms", 0)),
            _card("Active floors", global_counters.get("n_active_floors", 0)),
        ])

        # n_total_votes varies per scope - render one card per scope, hide/show via JS
        scope_vote_cards = ""
        for scope_key in _SCOPE_WINDOWS_MS:
            n = scope_counters.get(scope_key, {}).get("n_total_votes", 0)
            scope_vote_cards += (
                f'<div class="card scope-card" data-scope="{scope_key}" style="display:none">'
                f'<span class="card-val">{self._esc(n)}</span>'
                f'<span class="card-lbl">Votes ({_SCOPE_LABELS[scope_key]})</span></div>'
            )

        age_s = max(0, (int(time.time() * 1000) - global_counters.get("refreshed_ms", int(time.time() * 1000))) // 1000)
        # refresh_card = _card("Refreshed", f"{age_s}s ago", "muted")

        return (
            f'<div class="summary-bar">'
            f'{static_cards}{scope_vote_cards}'  # {refresh_card}'
            f'</div>'
        )

    @staticmethod
    def _render_confusion_table(cm: dict) -> str:
        """Coloured 2x2 confusion matrix table."""
        counts = cm.get("counts", {})
        pct = cm.get("pct", {})
        truths = ("human", "ai")
        vote_cols = ("human", "ai")

        def _bg(p: float) -> str:
            # white → soft blue-green
            r = int(255 - p * 0.8)
            g = int(255 - p * 0.5)
            b = int(255 - p * 0.1)
            return f"rgb({r},{g},{b})"

        header = (
            "<thead><tr>"
            "<th>Truth \\ Vote</th>"
            + "".join(f"<th>{c}</th>" for c in vote_cols)
            + "</tr></thead>"
        )
        body_rows = []
        for gt in truths:
            cells = f"<td><strong>{gt}</strong></td>"
            for vt in vote_cols:
                c = counts.get(gt, {}).get(vt, 0)
                p = pct.get(gt, {}).get(vt, 0.0)
                cells += f'<td style="background:{_bg(p)}">{c}<br><small>{p:.1f}%</small></td>'
            body_rows.append(f"<tr>{cells}</tr>")
        body = "<tbody>" + "".join(body_rows) + "</tbody>"
        return f'<table class="cm-table">{header}{body}</table>'

    @staticmethod
    def _make_ops_plotly_json(ops_series: dict[str, list[tuple[int, int]]]) -> str:
        """Convert ops time-series to a JSON list of Plotly scatter traces."""
        traces = []
        for i, stat_name in enumerate(_HOTEL_OPS_STATS):
            pts = ops_series.get(stat_name, [])
            if not pts:
                continue
            xs = [
                datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                for ts, _ in pts
            ]
            ys = [v for _, v in pts]
            colour = _PALETTE[i % len(_PALETTE)]
            traces.append({
                "x": xs,
                "y": ys,
                "name": _HOTEL_OPS_LABELS.get(stat_name, stat_name),
                "type": "scatter",
                "mode": "lines",
                "line": {"color": colour, "width": 2, "shape": "spline"},
            })
        return json.dumps(traces)

    def _render_scope_block_cm(self, scope_key: str, scope_data: dict) -> str:
        """Render the confusion matrix panel for one scope (placed in mid-row left column)."""
        cm_html = self._render_confusion_table(scope_data["confusion"])
        return (
            f'<div class="scope-panel" data-scope="{scope_key}">'
            f'<div class="cm-card">{cm_html}</div>'
            f'</div>'
        )

    def _render_scope_block_lb(self, scope_key: str, scope_data: dict) -> str:
        """Render the leaderboard panels for one scope.
        Data is serialised as JSON into window.__LB_DATA; Grid.js tables and
        podium cards are built entirely client-side so they paginate natively."""
        _MAX_ROWS = 100

        def _clean(rows: list[dict]) -> list[dict]:
            """Add rank, strip internal _ keys, truncate to _MAX_ROWS."""
            out = []
            for i, row in enumerate(rows[:_MAX_ROWS], start=1):
                r = {k: v for k, v in row.items() if not k.startswith("_")}
                r["rank"] = i
                out.append(r)
            return out

        votee_clean = _clean(scope_data["votee"])
        voter_clean = _clean(scope_data["voter"])

        esc_scope = self._esc(scope_key)
        votee_json = json.dumps(votee_clean)
        voter_json = json.dumps(voter_clean)

        return (
            f'<div class="scope-panel" data-scope="{esc_scope}">'
            f'<div class="lb-panel visible" data-lb="fooling">'
            f'  <div class="podium-container" data-gridid="votee-{esc_scope}"></div>'
            f'  <div class="grid-container" data-gridid="votee-{esc_scope}"></div>'
            f'</div>'
            f'<div class="lb-panel" data-lb="detecting">'
            f'  <div class="podium-container" data-gridid="voter-{esc_scope}"></div>'
            f'  <div class="grid-container" data-gridid="voter-{esc_scope}"></div>'
            f'</div>'
            f'<script>'
            f'window.__LB_DATA=window.__LB_DATA||{{}};'
            f'window.__LB_DATA["votee-{esc_scope}"]={votee_json};'
            f'window.__LB_DATA["voter-{esc_scope}"]={voter_json};'
            f'</script>'
            f'</div>'
        )

    def _render_page(
        self,
        summary_html: str,
        scope_cms_html: str,
        scope_lbs_html: str,
        ops_json: str,
    ) -> str:
        """Compose the full HTML document.
        The html_renderer import is deferred here so that module-level exec on
        agent nodes never touches html_renderer (agents return None from plot()
        before this method is ever called).
        """
        from .html_renderer import render  # safe: only reached after is_world guard

        default_scope = "max"  # Show max available
        scope_tab_buttons = "".join(
            f'<button class="tab-btn" data-scope="{k}" onclick="switchScope(\'{k}\')">'
            f'{_SCOPE_LABELS[k]}</button>'
            for k in _SCOPE_WINDOWS_MS
        )

        return render(
            summary_html=summary_html,
            scope_tab_buttons=scope_tab_buttons,
            scope_cms_html=scope_cms_html,
            scope_lbs_html=scope_lbs_html,
            default_scope=default_scope,
            ops_json=ops_json,
        )

    # ========================================================== plot() entry

    def plot(self, since_timestamp: int = 0) -> str | None:
        if not self.is_world:
            return None

        cache = self._refresh_aggregates_if_stale()
        scopes = cache["scopes"]

        # Static world counters
        static_stats = {
            k: self._stats.get(k, 0)
            for k in ("n_total_agents", "n_humans", "n_ais")
        }
        global_counters = {
            k: cache[k]
            for k in ("n_active_rooms", "n_active_floors", "refreshed_ms")
        }
        scope_counters = {k: scopes[k] for k in scopes}

        summary_html = self._render_summary_bar(static_stats, scope_counters, global_counters)

        scope_cms_html = "".join(
            self._render_scope_block_cm(scope_key, scope_data)
            for scope_key, scope_data in scopes.items()
        )
        scope_lbs_html = "".join(
            self._render_scope_block_lb(scope_key, scope_data)
            for scope_key, scope_data in scopes.items()
        )

        ops_series = cache.get("ops_series", {})
        ops_json = self._make_ops_plotly_json(ops_series)

        return self._render_page(summary_html, scope_cms_html, scope_lbs_html, ops_json)
