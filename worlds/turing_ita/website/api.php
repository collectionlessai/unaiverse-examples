<?php
// Turing Hotel Italia website: the ONLY server-side piece — a read-only JSON bridge between the static
// site (app.js) and the MySQL mirror of the world stats DB (see src/mirror.py + run_w.py).
// Endpoints (GET):
//   ?q=ops                        -> hotel ops series + totals   {n_total_agents, series: {stat: [[ts, v], ...]}}
//   ?q=votes                      -> validated turing_vote rows  [{ts, votee, v}, ...] (PARSER_SKIPPED excluded)
//   ?q=sessions                   -> logged-conversation sessions [{session, n, first_ts, last_ts}, ...]
//   ?q=conversation&session=S     -> the chunks of one session   [{ts, m}, ...]
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

require __DIR__ . '/config.php';

// Debug mode ($DEBUG in config.php): PHP errors/warnings are displayed (they land in the response body,
// which the site shows in its error banners) and the JSON error replies carry the full exception message
$DEBUG = $DEBUG ?? false;
ini_set('display_errors', $DEBUG ? '1' : '0');
ini_set('display_startup_errors', $DEBUG ? '1' : '0');
error_reporting($DEBUG ? E_ALL : 0);

function fail(int $code, string $msg): void {
    http_response_code($code);
    echo json_encode(['error' => $msg]);
    exit;
}

function detail(Throwable $e): string {
    global $DEBUG;
    return $DEBUG ? ': ' . $e->getMessage() . ' @ ' . $e->getFile() . ':' . $e->getLine() : '';
}

try {
    $pdo = new PDO("mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4", $DB_USER, $DB_PASS,
                   [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
} catch (PDOException $e) {
    fail(500, 'Database unreachable' . detail($e));
}

$OPS_STATS = ['hotel_n_floors_active', 'hotel_n_rooms_active', 'hotel_n_rooms_overbooked',
              'hotel_n_agents_present', 'hotel_n_agents_waiting'];

$q = $_GET['q'] ?? '';
try {
    switch ($q) {
        case 'ops':
            $series = [];
            $st = $pdo->prepare("SELECT ts, val_num FROM dynamic_stats WHERE stat_name = ? ORDER BY id");
            foreach ($OPS_STATS as $stat) {
                $st->execute([$stat]);
                $pts = [];
                foreach ($st as $row) {
                    $pts[] = [(int)$row['ts'], (float)$row['val_num']];
                }
                $series[$stat] = $pts;
            }
            $tot = $pdo->query("SELECT val_json FROM static_stats WHERE stat_name = 'n_total_agents' " .
                               "ORDER BY id DESC LIMIT 1")->fetch();
            echo json_encode(['n_total_agents' => $tot === false ? null : json_decode($tot['val_json'], true),
                              'series' => $series]);
            break;

        case 'votes':
            $st = $pdo->query("SELECT id, ts, peer_id, val_json FROM dynamic_stats " .
                              "WHERE stat_name = 'turing_vote' AND peer_id <> 'PARSER_SKIPPED' ORDER BY id");
            $out = [];
            foreach ($st as $row) {
                $out[] = ['id' => (int)$row['id'], 'ts' => (int)$row['ts'],
                          'votee' => $row['peer_id'], 'v' => json_decode($row['val_json'], true)];
            }
            echo json_encode($out);
            break;

        case 'sessions':
            // Conversations are grouped by the session_id INSIDE the chunk (see src/stats.py: the DB
            // group key of a chunk is a different string, "<room.uuid>:<activation_ts>")
            $st = $pdo->query("SELECT JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.session_id')) AS session, " .
                              "COUNT(*) AS n, MIN(ts) AS first_ts, MAX(ts) AS last_ts, " .
                              "GROUP_CONCAT(DISTINCT JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.author'))) " .
                              "AS authors " .
                              "FROM dynamic_stats WHERE stat_name = 'conversation_chunk' " .
                              "GROUP BY session ORDER BY last_ts DESC");
            $out = [];
            foreach ($st as $row) {
                if ($row['session'] === null) {
                    continue;
                }
                $out[] = ['session' => $row['session'], 'n' => (int)$row['n'],
                          'first_ts' => (int)$row['first_ts'], 'last_ts' => (int)$row['last_ts'],
                          'authors' => $row['authors'] === null ? [] : explode(',', $row['authors'])];
            }
            echo json_encode($out);
            break;

        case 'conversation':
            $session = $_GET['session'] ?? '';
            if ($session === '') {
                fail(400, "Missing 'session'");
            }
            $st = $pdo->prepare("SELECT ts, val_json FROM dynamic_stats " .
                                "WHERE stat_name = 'conversation_chunk' " .
                                "AND JSON_UNQUOTE(JSON_EXTRACT(val_json, '$.session_id')) = ? ORDER BY id");
            $st->execute([$session]);
            $out = [];
            foreach ($st as $row) {
                $out[] = ['ts' => (int)$row['ts'], 'm' => json_decode($row['val_json'], true)];
            }
            echo json_encode($out);
            break;

        default:
            fail(400, "Unknown endpoint '$q' (use: ops, votes, sessions, conversation)");
    }
} catch (Throwable $e) {  // PDO errors AND any other PHP error: always a JSON reply, never a white page
    fail(500, 'Query failed' . detail($e));
}
