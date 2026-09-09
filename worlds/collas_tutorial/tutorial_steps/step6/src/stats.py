"""
       █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
      ░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
       ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░
       ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████
       ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█
       ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
       ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
        ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░
                 A Collectionless AI Project (https://collectionless.ai)
                 Registration/Login: https://unaiverse.io
                 Code Repositories:  https://github.com/collectionlessai/
                 Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""
import html
import json
from unaiverse.stats import Stats
from datetime import datetime, timezone


class WStats(Stats):
    """Custom stats for the CoLLAs 2026 tutorial world: per-student quality and exam history.
    This file describes those stats that are saved to the local DB of the world node.
    The stats we save change over time, so they are DYNAMIC stats. There is only one stat we consider, we named it
    'exam_result'. The value associated to each stat is a dictionary, fully customizable.
    For the Web UI, it is possible to visualize the stats of the world that was joined. They are shown by an HTML file
    that is generated from the plot() method down here.

    Stats schema
    ------------
    OUTER dynamic (group key = the student's UNaID):

      exam_result - one record per (exam, student), stored by the teacher right after evaluate_results.
                    Value shape:
                      {
                        "score":     <float in [0,1]>,  (fraction of correct answers in this exam)
                        "correct":   <int>,             (number of correct answers)
                        "questions": <int>,             (number of exam questions)
                        "quality":   <float in [0,1]>,  (the student's quality index AFTER this exam)
                      }
                    Only the last MAX_EXAMS_PER_STUDENT records per student are kept (pruned at save time).

    The plot() method (world only) renders a simple self-contained HTML page: one card per student, with
    the current quality index and the history of the last exams.
    """
    MAX_EXAMS_PER_STUDENT = 30  # The max number of results that are kept per student
    MAX_STUDENTS_SHOWN = 10  # The HTML page only shows the most recently examined students

    # This is read by the UNaIVERSE core to understand the stats that are declared in this world
    CUSTOM_OUTER_STATS_DYNAMIC_SCHEMA = {
        "exam_result": (dict, None),
    }

    # ---------------------------------------------------------------
    # DATABASE MANAGEMENT
    # ---------------------------------------------------------------

    def _fetch_exam_history(self) -> dict[str, list[dict]]:
        """Utility used by plot(). Reads the local DB and return {student_unaid: [exam records, newest first, capped]}
        from SQLite."""
        if not self.is_world:
            return {}
        assert self._db_conn is not None
        rows = self._db_conn.execute(
            "SELECT timestamp, peer_id, val_json FROM dynamic_stats "
            "WHERE stat_name = 'exam_result' ORDER BY timestamp DESC"
        ).fetchall()
        history: dict[str, list[dict]] = {}
        for ts, unaid, val_json in rows:
            try:
                record = json.loads(val_json)
                record["_ts"] = ts
            except (json.JSONDecodeError, TypeError):
                continue
            exams = history.setdefault(unaid, [])
            if len(exams) < self.MAX_EXAMS_PER_STUDENT:  # Read-side cap too (prune runs at save time)
                exams.append(record)
        return history

    def _prune_db(self):
        """Override of a predefined method, which is automatically called when saving stats to disk
        (commit happens in Stats.save_to_disk(), which is what calls _prune_db)."""
        if not self.is_world or self._db_conn is None:
            return
        self._db_conn.execute(
            "DELETE FROM dynamic_stats WHERE stat_name = 'exam_result' AND rowid NOT IN ("
            "  SELECT rowid FROM ("
            "    SELECT rowid, ROW_NUMBER() OVER (PARTITION BY peer_id ORDER BY timestamp DESC) AS rn"
            "    FROM dynamic_stats WHERE stat_name = 'exam_result'"
            "  ) WHERE rn <= ?"
            ")",
            (self.MAX_EXAMS_PER_STUDENT,)
        )

    # ---------------------------------------------------------------
    # HTML RENDERING
    # ---------------------------------------------------------------

    @staticmethod
    def _esc(v) -> str:
        """Utility used by plot()."""
        return html.escape(str(v))

    @staticmethod
    def _stars(q: float) -> str:
        """Utility used by plot()."""
        full = max(0, min(5, round(q * 5.)))
        return "★" * full + "☆" * (5 - full)

    def _render_student_card(self, unaid: str, exams: list[dict]) -> str:
        """Utility used by plot(). One card per student: header with quality index, then exam history (newest first)."""
        quality = float(exams[0].get("quality", 0.)) if exams else 0.
        rows = ""
        for i, e in enumerate(exams):
            when = datetime.fromtimestamp(e.get("_ts", 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            score = float(e.get("score", 0.))
            rows += (
                f"<tr><td>{len(exams) - i}</td><td>{self._esc(when)}</td>"
                f"<td>{e.get('correct', '?')}/{e.get('questions', '?')}</td>"
                f"<td><div class='bar'><div style='width:{score * 100:.0f}%'></div></div> {score:.0%}</td></tr>"
            )
        return (
            f"<div class='card'>"
            f"<div class='card-head'><span class='unaid'>{self._esc(unaid)}</span>"
            f"<span class='quality'>quality {self._stars(quality)} ({quality:.0%})</span></div>"
            f"<table><thead><tr><th>#</th><th>When</th><th>Correct</th><th>Score</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
            f"</div>"
        )

    def plot(self, since_timestamp: int = 0) -> str | None:
        """The main method that is called to generate the HTML."""
        if not self.is_world:
            return None

        # Reading the DB
        history = self._fetch_exam_history()

        # Only the last MAX_STUDENTS_SHOWN students (by most recent exam), sorted by current quality (descending)
        recent = sorted(history.items(), key=lambda kv: kv[1][0].get("_ts", 0) if kv[1] else 0,
                        reverse=True)[:self.MAX_STUDENTS_SHOWN]
        ordered = sorted(recent, key=lambda kv: kv[1][0].get("quality", 0.) if kv[1] else 0., reverse=True)
        cards = "".join(self._render_student_card(unaid, exams) for unaid, exams in ordered)
        if not cards:
            cards = "<p class='empty'>No exams recorded yet: waiting for the first classroom round...</p>"
        n_exams = sum(len(v) for v in history.values())

        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CoLLAs 2026 Tutorial - Classroom Stats</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px;
          background: #f4f5f7; color: #1c1e21; }}
  h1 {{ font-size: 1.3rem; margin: 0 0 4px; }}
  .subtitle {{ color: #667; margin: 0 0 20px; font-size: .9rem; }}
  .card {{ background: #fff; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;
           box-shadow: 0 1px 3px rgba(0,0,0,.08); max-width: 760px; }}
  .card-head {{ display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;
                gap: 6px; margin-bottom: 8px; }}
  .unaid {{ font-weight: 600; word-break: break-all; }}
  .quality {{ color: #b8860b; white-space: nowrap; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .85rem; }}
  th {{ text-align: left; color: #667; font-weight: 500; padding: 2px 10px 4px 0; }}
  td {{ padding: 3px 10px 3px 0; border-top: 1px solid #eee; }}
  .bar {{ display: inline-block; vertical-align: middle; width: 110px; height: 9px;
          background: #e8eaee; border-radius: 5px; overflow: hidden; }}
  .bar > div {{ height: 100%; background: #4e79a7; border-radius: 5px; }}
  .empty {{ color: #667; }}
</style></head><body>
<h1>🎓 CoLLAs 2026 Tutorial - Classroom Stats</h1>
<p class="subtitle">Students: {len(ordered)} shown of {len(history)} &middot; Exams recorded: {n_exams}
(last {self.MAX_EXAMS_PER_STUDENT} per student)</p>
{cards}
</body></html>"""
