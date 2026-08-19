-- Turing Hotel Italia stats mirror: the two tables the MirrorMySQLTarget of run_w.py uploads into.
-- The 'id' columns ARE the local SQLite rowids (they drive the mirror alignment: do not auto-generate).
-- The g_* columns are GENERATED from val_json (the mirror never writes them: MySQL fills them), so the
-- api.php queries over sessions/kinds/authors are index lookups instead of full-table JSON scans.
-- Requires MySQL >= 5.7. On a database created with an OLDER version of this file, run the ALTER TABLE
-- statements at the bottom (once) instead of the CREATE.
CREATE TABLE IF NOT EXISTS dynamic_stats (
    id        BIGINT       NOT NULL PRIMARY KEY,
    ts        BIGINT       NOT NULL,
    peer_id   VARCHAR(255) NOT NULL,
    stat_name VARCHAR(64)  NOT NULL,
    val_num   DOUBLE       NULL,
    val_str   TEXT         NULL,
    val_json  LONGTEXT     NULL,
    g_session VARCHAR(80)  GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.session_id'))) STORED,
    g_kind    VARCHAR(16)  GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.kind'))) STORED,
    g_author  VARCHAR(255) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.author'))) STORED,
    INDEX idx_stat (stat_name, id),
    INDEX idx_peer (peer_id(191)),
    INDEX idx_session (stat_name, g_session, id),
    INDEX idx_session_ts (stat_name, g_session, ts),
    INDEX idx_kind (stat_name, g_session, g_kind, id),
    INDEX idx_stat_ts (stat_name, ts)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS static_stats (
    id        BIGINT       NOT NULL PRIMARY KEY,
    peer_id   VARCHAR(255) NOT NULL,
    stat_name VARCHAR(64)  NOT NULL,
    val_json  LONGTEXT     NULL,
    ts        BIGINT       NOT NULL,
    UNIQUE KEY uq_key (peer_id(191), stat_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

-- ============================ MIGRATION of a pre-existing database ============================
-- Run ONCE on a dynamic_stats table created without the g_* columns (comment removed):
-- ALTER TABLE dynamic_stats
--   ADD COLUMN g_session VARCHAR(80)  GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.session_id'))) STORED,
--   ADD COLUMN g_kind    VARCHAR(16)  GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.kind'))) STORED,
--   ADD COLUMN g_author  VARCHAR(255) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.author'))) STORED,
--   ADD INDEX idx_session (stat_name, g_session, id),
--   ADD INDEX idx_session_ts (stat_name, g_session, ts),
--   ADD INDEX idx_kind (stat_name, g_session, g_kind, id),
--   ADD INDEX idx_stat_ts (stat_name, ts);
