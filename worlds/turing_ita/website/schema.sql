-- Agora stats mirror: the two tables the MirrorMySQLTarget of run_w.py uploads into.
-- The 'id' columns ARE the local SQLite rowids (they drive the mirror alignment: do not auto-generate).
CREATE TABLE IF NOT EXISTS dynamic_stats (
    id        BIGINT       NOT NULL PRIMARY KEY,
    ts        BIGINT       NOT NULL,
    peer_id   VARCHAR(255) NOT NULL,
    stat_name VARCHAR(64)  NOT NULL,
    val_num   DOUBLE       NULL,
    val_str   TEXT         NULL,
    val_json  LONGTEXT     NULL,
    INDEX idx_stat (stat_name, id),
    INDEX idx_peer (peer_id(191))
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS static_stats (
    id        BIGINT       NOT NULL PRIMARY KEY,
    peer_id   VARCHAR(255) NOT NULL,
    stat_name VARCHAR(64)  NOT NULL,
    val_json  LONGTEXT     NULL,
    ts        BIGINT       NOT NULL,
    UNIQUE KEY uq_key (peer_id(191), stat_name)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
