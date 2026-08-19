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
import time
import json
import sqlite3
import hashlib
from unaiverse.utils.logger import log
from concurrent.futures import ThreadPoolExecutor

# Mirror of the world stats DB toward an external destination (e.g., a MySQL on another machine),
# designed for the Node 'run_hook' (a callable invoked EVERY cycle ON the main loop, so the hook built
# here only DECIDES — the actual reads/uploads run on a single-worker background thread):
#
#   node = Node(..., run_hook=make_mirror_hook(world.stats.db_path, target, period=30.))
#
# 'target' is the deployment-specific side (see the class below), an object with three methods (all called on
# the mirror thread, free to be slow):
#   remote_last_id() -> int | None   (MAX stored id of the REMOTE dynamic_stats, 0 when empty;
#                                     None = unreachable, the init is retried at the next cycle)
#   clear() -> bool   (wipe both remote tables; only called when the local DB was reset/rewound)
#   upload(dynamic_rows, static_rows) -> bool   (True ONLY on full success; must be idempotent)
# Row shapes (the id is the local SQLite rowid, which the remote MUST store — it drives the alignment):
#   dynamic_rows: [(id, timestamp, peer_id, stat_name, val_num, val_str, val_json), ...] insert-ordered
#   static_rows:  [(id, peer_id, stat_name, val_json, timestamp), ...] FULL snapshot (small upsert table)
#
# How it works, and the invariants it guarantees:
# - The watermark is VOLATILE (in memory only, no sidecar files): on the FIRST cycle the last DYNAMIC id
#   of the two sides is compared. Remote == local -> in sync, resume; remote BEHIND (includes an empty
#   remote) -> catch up incrementally from the remote's last id, nothing is cleared; remote AHEAD (the
#   local DB was deleted/rewound, so the id spaces diverged) -> the remote is cleared and the local DB
#   fully re-uploaded in 'batch'-sized chunks. A crash mid-catch-up just realigns at the next start:
#   the scheme is self-healing with no persistent state.
# - The remote is an ARCHIVE: the local pruning (_prune_db) deletes old LOW rowids, which the alignment
#   deliberately ignores (last ids only, no row counts) — pruned rows stay on the remote forever. The
#   price of archive semantics: rows lost from the MIDDLE of the remote table go undetected.
# - 'static_stats' does NOT take part in the alignment (its values change in place, upserts keep their
#   rowid — counts/ids cannot see that): instead its FULL snapshot is re-shipped unconditionally on the
#   first cycle after every init, and whenever its content digest changes during the session. The remote
#   static table therefore always converges to the local one (REPLACE semantics on the target side).
# - The watermark advances ONLY when upload() returns True: on False/None/exception the SAME rows are
#   retried at the next cycle, and the world never notices (errors are just logged).
# - Reads happen on a dedicated READ-ONLY connection (only committed data; the node thread keeps writing
#   every SAVE_STATS_EVERY undisturbed).


def make_mirror_hook(db_path: str, target, period: float = 30., batch: int = 5000, max_batches: int = 20):
    """Build a 'run_hook' mirroring the stats DB at 'db_path' through 'target' (see the module notes).
    Each cycle DRAINS the backlog in batches (up to max_batches * batch rows per cycle): one batch per
    cycle cannot keep up with busy worlds (100 chatting rooms produce way more rows per hour)."""
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="stats-mirror")
    hook_state = {"last": 0., "future": None}  # Touched by the MAIN loop only
    job_state = {"conn": None, "watermark": None, "static_digest": None,  # Touched by the mirror thread
                 "reset_requested": False}  # Flipped by _hook.reset() (main loop): consumed at job start

    def _job():
        try:
            if job_state["reset_requested"]:  # The local DB was wiped: re-run the init alignment,
                job_state["reset_requested"] = False  # which will clear the remote (it is now AHEAD)
                job_state["watermark"] = None
                job_state["static_digest"] = None
                log.user("[stats-mirror] Reset requested: re-aligning with the (wiped) local DB")
            if job_state["conn"] is None:  # Lazy init (single-worker pool: always the same thread)
                conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                conn.execute("PRAGMA busy_timeout=5000")  # Tolerate the writer's commit moments
                job_state["conn"] = conn  # noqa
            conn = job_state["conn"]

            assert conn is not None and isinstance(conn, sqlite3.Connection)

            if job_state["watermark"] is None:  # First cycle: align the volatile watermark to the remote
                local_last = conn.execute("SELECT COALESCE(MAX(rowid), 0) FROM dynamic_stats").fetchone()[0]
                remote_last = target.remote_last_id()
                if remote_last is None:
                    log.error("[stats-mirror] Remote state unavailable, retrying at the next cycle")
                    return
                if remote_last <= local_last:  # In sync, or remote behind: catch up from where it stands
                    job_state["watermark"] = remote_last
                    log.user(f"[stats-mirror] Resuming incrementally (local last id={local_last}, "
                             f"remote last id={remote_last})")
                else:  # Remote AHEAD: the local DB was reset/rewound, its id space diverged from the remote
                    if target.clear() is not True:
                        log.error("[stats-mirror] Local DB behind the remote but clearing the remote "
                                  "failed, retrying at the next cycle")
                        return
                    job_state["watermark"] = 0  # noqa
                    log.user(f"[stats-mirror] Local DB was reset (local last id={local_last} < remote "
                             f"last id={remote_last}): remote cleared, fully re-uploading")
                job_state["static_digest"] = None  # Ship the static snapshot at least once after init

            # The static snapshot is read (and possibly shipped) ONCE per cycle; the dynamic backlog
            # is drained in batches, advancing the watermark after each successful upload (a failure
            # leaves it in place: the SAME rows are retried at the next cycle, at-least-once)
            static_rows = conn.execute(
                "SELECT rowid, peer_id, stat_name, val_json, timestamp FROM static_stats").fetchall()
            static_digest = hashlib.sha1(repr(static_rows).encode()).hexdigest()
            ship_static = static_digest != job_state["static_digest"]
            for _ in range(max_batches):
                dynamic_rows = conn.execute(
                    "SELECT rowid, timestamp, peer_id, stat_name, val_num, val_str, val_json "
                    "FROM dynamic_stats WHERE rowid > ? ORDER BY rowid LIMIT ?",
                    (job_state["watermark"], batch)).fetchall()
                if len(dynamic_rows) == 0 and not ship_static:
                    return  # Nothing new (or fully drained)
                if target.upload(dynamic_rows, static_rows if ship_static else []) is not True:
                    return  # Failure: retry from the same watermark at the next cycle
                if ship_static:
                    job_state["static_digest"] = static_digest  # noqa
                    ship_static = False
                if len(dynamic_rows) > 0:
                    job_state["watermark"] = dynamic_rows[-1][0]
                if len(dynamic_rows) < batch:
                    return  # Drained
        except Exception as e:
            log.error(f"[stats-mirror] Mirror cycle failed (will retry at the next one): {e}")

    def _hook(node):  # noqa (the Node passes itself)
        """Called EVERY node cycle ON the main loop: it must only decide, never work."""
        future = hook_state["future"]
        if time.monotonic() - hook_state["last"] < period or (future is not None and not future.done()):  # noqa
            return  # Not due yet, or the previous upload still running (never overlap)
        hook_state["last"] = time.monotonic()
        hook_state["future"] = pool.submit(_job)  # noqa

    def _request_reset():
        """Re-arm the init alignment (call AFTER wiping the local DB): just a flag flip, consumed at
        the START of the next mirror job — an in-flight cycle can never clobber the re-init."""
        job_state["reset_requested"] = True

    _hook.reset = _request_reset
    return _hook


class MirrorMySQLTarget:
    """MySQL side of the mirror, running on the mirror thread (free to be slow). The row shapes below
    come from src/utils/mirror.py (the id is the local SQLite rowid — STORED remotely, remote_last_id
    is answered with it): dynamic_rows are (id, timestamp, peer_id, stat_name, val_num, val_str,
    val_json) in insert order; static_rows are (id, peer_id, stat_name, val_json, timestamp), a full
    snapshot (small, upserted). Every method swallows its errors (logged once per failure streak): the
    mirror layer retries the same rows until a call fully succeeds (at-least-once, idempotent SQL)."""

    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self._config = json.load(f)
        self._failing = False  # Only log the first error of a failure streak (one line every 30s is spam)

    def __connect(self):
        import mysql.connector  # Deferred: only the mirror thread needs it (pip install mysql-connector-python)
        c = self._config
        return mysql.connector.connect(host=c["host"], port=int(c.get("port", 3306)), user=c["user"],
                                       password=c["password"], database=c["database"],
                                       connection_timeout=10)

    def __failed(self, what: str, e: Exception):
        if not self._failing:
            self._failing = True
            log.error(f"[stats-mirror] {what} failed (will keep retrying, reported once): {e}")

    def __worked(self):
        if self._failing:
            self._failing = False
            log.user("[stats-mirror] Back in business")

    def remote_last_id(self) -> int | None:
        """Last stored id of the REMOTE dynamic_stats (0 = empty); None = unreachable (init retried)."""
        try:
            with self.__connect() as cnx:
                cur = cnx.cursor()
                cur.execute("SELECT COALESCE(MAX(id), 0) FROM dynamic_stats")
                last_id = int(cur.fetchone()[0])  # noqa
            self.__worked()
            return last_id
        except Exception as e:
            self.__failed("remote_last_id", e)
            return None

    def clear(self) -> bool:
        """Wipe both remote tables. Only called when the local DB was reset/rewound (its id space
        diverged from the remote one). Return True on success."""
        try:
            with self.__connect() as cnx:
                cur = cnx.cursor()
                cur.execute("TRUNCATE TABLE dynamic_stats")
                cur.execute("TRUNCATE TABLE static_stats")
                cnx.commit()
            self.__worked()
            return True
        except Exception as e:
            self.__failed("clear", e)
            return False

    def upload(self, dynamic_rows, static_rows) -> bool:
        """Return True ONLY on full success: the watermark advances and these rows are never offered
        again; on False/None/exception the SAME rows are retried. At-least-once: INSERT IGNORE/REPLACE
        keep the retries idempotent."""
        try:
            with self.__connect() as cnx:
                cur = cnx.cursor()
                if len(dynamic_rows) > 0:
                    cur.executemany("INSERT IGNORE INTO dynamic_stats (id, ts, peer_id, stat_name, "
                                    "val_num, val_str, val_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    dynamic_rows)
                if len(static_rows) > 0:
                    cur.executemany("REPLACE INTO static_stats (id, peer_id, stat_name, val_json, ts) "
                                    "VALUES (%s, %s, %s, %s, %s)", static_rows)
                cnx.commit()
            self.__worked()
            return True
        except Exception as e:
            self.__failed("upload", e)
            return False
