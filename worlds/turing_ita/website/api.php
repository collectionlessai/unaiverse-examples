<?php
// Turing Hotel Italia website: the ONLY server-side piece — a read-only JSON bridge between the static
// site (app.js) and the MySQL mirror of the world stats DB (see src/mirror.py + run_w.py).
// Endpoints (GET):
//   ?q=ops                        -> hotel ops series + totals   {n_total_agents, series: {stat: [[ts, v], ...]}}
//   ?q=votes                      -> validated turing_vote rows  [{ts, votee, v}, ...] (the *_SKIPPED
//                                    reason groups are excluded, like in src/stats.py)
//   ?q=sessions                   -> logged-conversation sessions [{session, n, first_ts, last_ts, authors}, ...]
//   ?q=presence                   -> who is in each room now      {session: [{author, fake_name, nature,
//                                    since_ts}, ...]} (from the recent join/left/disconnected events)
//   ?q=export_csv                 -> the WHOLE hotel archive as a CSV download (chats, room events and
//                                    voting acts, one row each, roughly chronological; see the case below);
//                                    &blank=1 replaces every UNaID with "user1", "user2", ... pseudonyms
//   ?q=events&session=S           -> the 'kind: event' chunks only [{id, ts, m}, ...] (join/left/disconnected)
//   ?q=conversation&session=S     -> a PAGE of the session transcript: {rows: [{id, ts, m}, ...], more: bool}
//        Room transcripts are UNBOUNDED (rooms never close), so this endpoint never returns them whole:
//        - default: the LATEST 'limit' chunks (limit <= 1000, default 300)
//        - &before_id=X          -> the 'limit' chunks right before id X (backward pagination)
//        - &from_ts=A&to_ts=B    -> chunks in a time range, ascending, first 'limit' (+ &after_id=X to go on)
//        - &from_id=A&to_id=B    -> chunks in an id range, ascending (the vote-context windows), 'limit'-paged
// The g_session/g_kind columns used below are GENERATED columns (see schema.sql): run its migration
// ALTER TABLE before deploying this file on a database created with the old schema.
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
            // The mirror is an ARCHIVE (it never prunes) and the hotel writes these metrics every few
            // seconds: loading the WHOLE history exhausts the PHP memory after a few days of running.
            // The chart shows the last 30 days anyway (the widest scope), capped at the most recent
            // OPS_MAX_POINTS rows per stat (newest first, then reversed back to chronological order)
            define('OPS_WINDOW_MS', 30 * 24 * 3600 * 1000);
            define('OPS_MAX_POINTS', 5000);
            $cutoff = (int)(microtime(true) * 1000) - OPS_WINDOW_MS;
            $series = [];
            $st = $pdo->prepare("SELECT ts, val_num FROM dynamic_stats WHERE stat_name = ? AND ts >= ? " .
                                "ORDER BY id DESC LIMIT " . OPS_MAX_POINTS);
            foreach ($OPS_STATS as $stat) {
                $st->execute([$stat, $cutoff]);
                $pts = [];
                foreach ($st as $row) {
                    $pts[] = [(int)$row['ts'], (float)$row['val_num']];
                }
                $series[$stat] = array_reverse($pts);
            }
            $tot = $pdo->query("SELECT val_json FROM static_stats WHERE stat_name = 'n_total_agents' " .
                               "ORDER BY id DESC LIMIT 1")->fetch();
            echo json_encode(['n_total_agents' => $tot === false ? null : json_decode($tot['val_json'], true),
                              'series' => $series]);
            break;

        case 'votes':
            $st = $pdo->query("SELECT id, ts, peer_id, val_json FROM dynamic_stats " .
                              "WHERE stat_name = 'turing_vote' " .
                              "AND peer_id NOT LIKE '%\\_SKIPPED' ORDER BY id");
            $out = [];
            foreach ($st as $row) {
                $out[] = ['id' => (int)$row['id'], 'ts' => (int)$row['ts'],
                          'votee' => $row['peer_id'], 'v' => json_decode($row['val_json'], true)];
            }
            echo json_encode($out);
            break;

        case 'empty_votes':
            // 'turing_empty_vote' rows: votes that could not be parsed/handled (their val_json carries
            // a 'reason'). NEVER part of any performance computation: the site only DISPLAYS them
            // (vote tables, bracketed counts), which is why they travel on their own endpoint
            $st = $pdo->query("SELECT id, ts, peer_id, val_json FROM dynamic_stats " .
                              "WHERE stat_name = 'turing_empty_vote' " .
                              "AND peer_id NOT LIKE '%\\_SKIPPED' ORDER BY id");
            $out = [];
            foreach ($st as $row) {
                $out[] = ['id' => (int)$row['id'], 'ts' => (int)$row['ts'],
                          'votee' => $row['peer_id'], 'v' => json_decode($row['val_json'], true),
                          'empty' => true];
            }
            echo json_encode($out);
            break;

        case 'sessions':
            // Conversations are grouped by the session_id INSIDE the chunk (see src/stats.py: the DB
            // group key of a chunk is a different string, "<room.uuid>:<activation_ts>")
            // n counts the CHAT messages only: 'kind: event' records (joined/left/disconnected) are
            // part of the transcript but not of the message count (their author still counts as a
            // participant: it is the AFFECTED guest, so even silent guests leave a trace)
            // MySQL SILENTLY truncates GROUP_CONCAT at group_concat_max_len (default 1024 chars):
            // ~30 authors already exceed it, cutting the list MID-UNaID — a garbage participant plus
            // missing ones. Raise the cap first (MySQL only: SQLite, used by the test twin, has none)
            if ($pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql') {
                $pdo->exec("SET SESSION group_concat_max_len = 1000000");
            }
            $st = $pdo->query("SELECT g_session AS session, " .
                              "SUM(CASE WHEN g_kind IS NULL THEN 1 ELSE 0 END) AS n, " .
                              "MIN(ts) AS first_ts, MAX(ts) AS last_ts, " .
                              "GROUP_CONCAT(DISTINCT g_author) AS authors " .
                              "FROM dynamic_stats WHERE stat_name = 'conversation_chunk' " .
                              "GROUP BY g_session ORDER BY last_ts DESC");
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

        case 'export_csv':
            // The WHOLE hotel archive as one CSV: chat messages, room events (joined/left/disconnected)
            // and voting acts, one row each, ordered by timestamp. Columns:
            //   floor_id, room_id, ts_ms, datetime (ISO 8601 UTC), event (chat|joined|left|disconnected|
            //   vote), fake_name, user (UNaID), nature, msg, structured
            // 'msg' carries the chat/event text, or the raw words the voter wrote. 'structured' is a
            // JSON dict where information was parsed: for events {agent: {fake_name, user}, event}; for
            // votes {voter: {fake_name, user}, votees: [{fake_name, user, ground_truth, vote,
            // correct (1|0), conversation_from_ts, conversation_to_ts}, ...]} — one VOTING ACT per row,
            // each votee with ITS OWN conversation window (the same pairWindows/pickWindow logic of the
            // site; nulls when the events cannot isolate it, vote ts closes a still-open window). The
            // unreadable acts (turing_empty_vote) are NOT special-cased: same 'vote' rows, null
            // vote/correct, plus their 'reason'. Every cell is quoted, always (messages carry commas,
            // quotes and newlines); the leading BOM keeps Excel happy with UTF-8.
            // The archive is unbounded, so rows are STREAMED in keyset-paginated chunks (never all in
            // memory); only the room events are preloaded (they are few, and every vote row needs them).
            // A voting act spans several DB records (one per votee) whose timestamps may differ by a few
            // ms (they are stamped per record): records of the same (stat, session, voter) within
            // EXPORT_ACT_TOLERANCE_MS are one act (a voter votes at most once per room cycle)
            // &blank=1 -> the BLANKED variant: every UNaID (the 'user' column and every 'user' field
            // inside 'structured') is replaced by a pseudonym "user1", "user2", ... assigned in order
            // of first appearance and consistent across the whole file; the fake names (room aliases,
            // anonymous by construction) are kept as they are
            define('EXPORT_ACT_TOLERANCE_MS', 2000);
            define('EXPORT_CHUNK_ROWS', 5000);
            set_time_limit(0);  // The archive is unbounded and this endpoint STREAMS it: the default
                                // 30s execution cap would kill the export mid-file (and append the
                                // fatal-error HTML to the CSV). Memory stays bounded by the chunking
            $blank = ($_GET['blank'] ?? '') === '1';
            $userMap = [];
            $anon = function ($unaid) use (&$userMap, $blank) {
                if (!$blank || (string)$unaid === '') {
                    return (string)$unaid;
                }
                if (!isset($userMap[$unaid])) {
                    $userMap[$unaid] = 'user' . (count($userMap) + 1);
                }
                return $userMap[$unaid];
            };
            header('Content-Type: text/csv; charset=utf-8');
            header('Content-Disposition: attachment; filename="turing_hotel_export'
                   . ($blank ? '_blanked' : '') . '.csv"');
            $out = fopen('php://output', 'wb');
            $csv = function (array $cells) use ($out) {
                fwrite($out, implode(',', array_map(function ($v) {
                    return '"' . str_replace('"', '""', $v === null ? '' : (string)$v) . '"';
                }, $cells)) . "\r\n");
            };
            $iso = function ($ms) {
                return gmdate('Y-m-d\TH:i:s', intdiv((int)$ms, 1000)) . sprintf('.%03dZ', ((int)$ms) % 1000);
            };
            $split = function ($session) {  // "floor_id:room_id" -> [floor_id, room_id]
                $p = explode(':', (string)$session, 2);
                return count($p) === 2 ? $p : ['', (string)$session];
            };
            $jenc = function ($x) {
                return json_encode($x, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
            };
            fwrite($out, "\xEF\xBB\xBF");
            $csv(['floor_id', 'room_id', 'ts_ms', 'datetime', 'event', 'fake_name', 'user', 'nature',
                  'msg', 'structured']);

            // Room events per session (they also feed the per-votee conversation windows)
            $eventsBySession = [];
            $st = $pdo->query("SELECT id, ts, val_json FROM dynamic_stats " .
                              "WHERE stat_name = 'conversation_chunk' AND g_kind = 'event' ORDER BY id");
            foreach ($st as $row) {
                $m = json_decode($row['val_json'], true);
                if (is_array($m)) {
                    $eventsBySession[$m['session_id'] ?? ''][] =
                        ['id' => (int)$row['id'], 'ts' => (int)$row['ts'], 'm' => $m];
                }
            }

            // pairWindows/pickWindow, ported 1:1 from app.js: the [join .. first left/disconnected]
            // windows in which the two identities (unaid + fake name, rooms are reused) were in the
            // room together, then the window whose right extreme is closest BEFORE the vote
            $evTs = function ($ev) { return (int)($ev['m']['ts'] ?? $ev['ts']); };
            $pairWindows = function (array $events, $a, $aFake, $b, $bFake) {
                $match = function ($m, $unaid, $fake) {
                    return ($m['author'] ?? '') === $unaid &&
                           ((string)$fake === '' || (string)($m['author_fake_name'] ?? '') === '' ||
                            $m['author_fake_name'] === $fake);
                };
                $present = ['a' => false, 'b' => false];
                $windows = [];
                $start = null;
                foreach ($events as $ev) {
                    $m = $ev['m'];
                    if ($match($m, $a, $aFake)) {
                        $who = 'a';
                    } elseif ($match($m, $b, $bFake)) {
                        $who = 'b';
                    } else {
                        continue;
                    }
                    if (($m['event'] ?? '') === 'joined') {
                        $present[$who] = true;
                        if ($start === null && $present['a'] && $present['b']) {
                            $start = $ev;
                        }
                    } else {
                        if ($start !== null) {
                            $windows[] = [$start, $ev];
                        }
                        $start = null;
                        $present[$who] = false;
                    }
                }
                if ($start !== null) {
                    $windows[] = [$start, null];  // Still open
                }
                return $windows;
            };
            $pickWindow = function (array $windows, $voteTs) use ($evTs) {
                if (count($windows) === 0) {
                    return null;
                }
                $best = null;
                $bestEnd = null;
                foreach ($windows as $w) {
                    $end = $w[1] === null ? INF : $evTs($w[1]);
                    if ($end <= $voteTs && ($best === null || $end > $bestEnd)) {
                        $best = $w;
                        $bestEnd = $end;
                    }
                }
                if ($best === null) {
                    foreach ($windows as $w) {
                        $end = $w[1] === null ? INF : $evTs($w[1]);
                        if ($best === null || $end < $bestEnd) {
                            $best = $w;
                            $bestEnd = $end;
                        }
                    }
                }
                return $best;
            };

            $flushAct = function (array $act) use ($csv, $iso, $split, $jenc, $pairWindows, $pickWindow,
                                                   $evTs, &$eventsBySession, $anon) {
                $first = $act['records'][0];
                $v0 = $first['v'];
                [$floorId, $roomId] = $split($v0['session_id'] ?? '');
                $events = $eventsBySession[$v0['session_id'] ?? ''] ?? [];
                $votees = [];
                foreach ($act['records'] as $rec) {
                    $v = $rec['v'];
                    $vote = $v['vote'] ?? null;  // null: an unreadable act (turing_empty_vote)
                    $win = $pickWindow($pairWindows($events, $v0['voter'] ?? '',
                                                    $v0['voter_fake_name'] ?? '',
                                                    $rec['votee'], $v['votee_fake_name'] ?? ''),
                                       $rec['ts']);
                    $votees[] = [
                        'fake_name' => $v['votee_fake_name'] ?? '',
                        'user' => $anon($rec['votee']),
                        'ground_truth' => $v['ground_truth'] ?? null,
                        'vote' => $vote,
                        'correct' => $vote === null ? null : (int)($vote === ($v['ground_truth'] ?? null)),
                        'conversation_from_ts' => $win === null ? null : $evTs($win[0]),
                        'conversation_to_ts' => $win === null ? null
                            : ($win[1] === null ? $rec['ts'] : $evTs($win[1])),
                    ];
                }
                $structured = ['voter' => ['fake_name' => $v0['voter_fake_name'] ?? '',
                                           'user' => $anon($v0['voter'] ?? '')],
                               'votees' => $votees];
                if (isset($v0['reason'])) {
                    $structured['reason'] = $v0['reason'];
                }
                $csv([$floorId, $roomId, $first['ts'], $iso($first['ts']), 'vote',
                      $v0['voter_fake_name'] ?? '', $anon($v0['voter'] ?? ''),
                      $v0['voter_nature'] ?? '', $v0['VOTE_MSG'] ?? '', $jenc($structured)]);
            };

            $pending = [];  // "stat|session|voter" -> ['ts' => last record ts, 'records' => [...]]
            $lastTs = -1;
            $lastId = -1;
            $chunk = $pdo->prepare(
                "SELECT id, ts, stat_name, peer_id, val_json FROM dynamic_stats " .
                "WHERE stat_name IN ('conversation_chunk', 'turing_vote', 'turing_empty_vote') " .
                "AND peer_id NOT LIKE '%\\_SKIPPED' " .
                "AND (ts > ? OR (ts = ? AND id > ?)) ORDER BY ts, id LIMIT " . EXPORT_CHUNK_ROWS);
            while (true) {
                $chunk->execute([$lastTs, $lastTs, $lastId]);
                $rows = $chunk->fetchAll();
                if (count($rows) === 0) {
                    break;
                }
                foreach ($rows as $row) {
                    $ts = (int)$row['ts'];
                    $lastTs = $ts;
                    $lastId = (int)$row['id'];
                    foreach ($pending as $key => $act) {  // Acts settle once the tolerance has passed
                        if ($ts - $act['ts'] > EXPORT_ACT_TOLERANCE_MS) {
                            $flushAct($act);
                            unset($pending[$key]);
                        }
                    }
                    $m = json_decode($row['val_json'], true);
                    if (!is_array($m)) {
                        continue;
                    }
                    if ($row['stat_name'] === 'conversation_chunk') {
                        [$floorId, $roomId] = $split($m['session_id'] ?? '');
                        if (($m['kind'] ?? '') === 'event') {
                            $csv([$floorId, $roomId, $ts, $iso($ts), $m['event'] ?? 'event',
                                  $m['author_fake_name'] ?? '', $anon($m['author'] ?? ''),
                                  $m['author_nature'] ?? '', $m['text'] ?? '',
                                  $jenc(['agent' => ['fake_name' => $m['author_fake_name'] ?? '',
                                                     'user' => $anon($m['author'] ?? '')],
                                         'event' => $m['event'] ?? ''])]);
                        } else {
                            $csv([$floorId, $roomId, $ts, $iso($ts), 'chat',
                                  $m['author_fake_name'] ?? '', $anon($m['author'] ?? ''),
                                  $m['author_nature'] ?? '', $m['text'] ?? '', '']);
                        }
                    } else {
                        $key = $row['stat_name'] . '|' . ($m['session_id'] ?? '') . '|' . ($m['voter'] ?? '');
                        if (isset($pending[$key]) && $ts - $pending[$key]['ts'] > EXPORT_ACT_TOLERANCE_MS) {
                            $flushAct($pending[$key]);
                            unset($pending[$key]);
                        }
                        if (!isset($pending[$key])) {
                            $pending[$key] = ['ts' => $ts, 'records' => []];
                        }
                        $pending[$key]['records'][] = ['ts' => $ts, 'votee' => $row['peer_id'], 'v' => $m];
                        $pending[$key]['ts'] = $ts;
                    }
                }
            }
            foreach ($pending as $act) {
                $flushAct($act);
            }
            exit;

        case 'presence':
            // Who is in each room RIGHT NOW (as of the last mirror sync): replay of the recent
            // 'kind: event' chunks — an identity (author unaid + fake name: rooms are reused) whose
            // LAST event is a 'joined' is still at the round table (moving to the voting booth logs a
            // 'left', a disconnection logs 'left' or 'disconnected': every exit path leaves an event).
            // Only the last PRESENCE_WINDOW_MS of events are replayed: guests cycle rooms every few
            // minutes, so the join of anyone actually present is always recent — and a guest seated
            // when the world was restarted (whose exit event was therefore never written) lives in a
            // session of the PREVIOUS run (new run = new floor id), which app.js hides as stale.
            // 'author_nature' ("human"/"ai") entered the chunks later than the other fields: rows
            // stored before that change simply have no nature (null here, "-" on the site)
            define('PRESENCE_WINDOW_MS', 48 * 3600 * 1000);
            define('PRESENCE_MAX_ROWS', 20000);
            $cutoff = (int)(microtime(true) * 1000) - PRESENCE_WINDOW_MS;
            $st = $pdo->prepare("SELECT id, ts, val_json FROM dynamic_stats " .
                                "WHERE stat_name = 'conversation_chunk' AND g_kind = 'event' " .
                                "AND ts >= ? ORDER BY id LIMIT " . PRESENCE_MAX_ROWS);
            $st->execute([$cutoff]);
            $last = [];  // "<session>\x00<author>\x00<fake>" -> last event record of that identity
            foreach ($st as $row) {
                $m = json_decode($row['val_json'], true);
                if (!is_array($m) || ($m['session_id'] ?? '') === '' || ($m['author'] ?? '') === '') {
                    continue;
                }
                $key = $m['session_id'] . "\x00" . $m['author'] . "\x00" . ($m['author_fake_name'] ?? '');
                $last[$key] = ['session' => $m['session_id'], 'event' => $m['event'] ?? '',
                               'author' => $m['author'], 'fake_name' => $m['author_fake_name'] ?? '',
                               'nature' => $m['author_nature'] ?? null, 'since_ts' => (int)$row['ts']];
            }
            $out = [];  // session -> [{author, fake_name, nature, since_ts}, ...]
            foreach ($last as $rec) {
                if ($rec['event'] !== 'joined') {
                    continue;
                }
                $out[$rec['session']][] = ['author' => $rec['author'], 'fake_name' => $rec['fake_name'],
                                           'nature' => $rec['nature'], 'since_ts' => $rec['since_ts']];
            }
            echo json_encode((object)$out);
            break;

        case 'events':
            $session = $_GET['session'] ?? '';
            if ($session === '') {
                fail(400, "Missing 'session'");
            }
            $st = $pdo->prepare("SELECT id, ts, val_json FROM dynamic_stats " .
                                "WHERE stat_name = 'conversation_chunk' AND g_session = ? " .
                                "AND g_kind = 'event' ORDER BY id");
            $st->execute([$session]);
            $out = [];
            foreach ($st as $row) {
                $out[] = ['id' => (int)$row['id'], 'ts' => (int)$row['ts'],
                          'm' => json_decode($row['val_json'], true)];
            }
            echo json_encode($out);
            break;

        case 'conversation':
            $session = $_GET['session'] ?? '';
            if ($session === '') {
                fail(400, "Missing 'session'");
            }
            $limit = max(1, min((int)($_GET['limit'] ?? 300), 1000));
            $conds = ["stat_name = 'conversation_chunk'", "g_session = ?"];
            $args = [$session];
            foreach ([['from_ts', 'ts >= ?'], ['to_ts', 'ts <= ?'], ['from_id', 'id >= ?'],
                      ['to_id', 'id <= ?'], ['after_id', 'id > ?'], ['before_id', 'id < ?']] as $p) {
                if (isset($_GET[$p[0]]) && $_GET[$p[0]] !== '') {
                    $conds[] = $p[1];
                    $args[] = (int)$_GET[$p[0]];
                }
            }
            // Backward (latest page, and 'load older' via before_id) unless an explicit range or a
            // forward cursor asks for ascending; one extra row probes whether more pages exist
            $backward = !isset($_GET['from_ts']) && !isset($_GET['from_id']) && !isset($_GET['after_id']);
            $st = $pdo->prepare("SELECT id, ts, val_json FROM dynamic_stats WHERE " .
                                implode(" AND ", $conds) .
                                " ORDER BY id " . ($backward ? "DESC" : "ASC") . " LIMIT " . ($limit + 1));
            $st->execute($args);
            $rows = [];
            foreach ($st as $row) {
                $rows[] = ['id' => (int)$row['id'], 'ts' => (int)$row['ts'],
                           'm' => json_decode($row['val_json'], true)];
            }
            $more = count($rows) > $limit;
            if ($more) {
                array_pop($rows);
            }
            if ($backward) {
                $rows = array_reverse($rows);  // Back to chronological order
            }
            echo json_encode(['rows' => $rows, 'more' => $more]);
            break;

        default:
            fail(400, "Unknown endpoint '$q' (use: ops, votes, empty_votes, sessions, presence, " .
                      "events, conversation, export_csv)");
    }
} catch (Throwable $e) {  // PDO errors AND any other PHP error: always a JSON reply, never a white page
    fail(500, 'Query failed' . detail($e));
}
