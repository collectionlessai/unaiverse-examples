/* ═══════════════════════════════════════════════════════
   Hotel delle Imitazioni (Turing Hotel Italia) — single-page app over the MySQL mirror of the world
   stats DB (via api.php). Pages: #/ overview (KPI + ops chart) · #/floors (floors and rooms, from
   the votes and the logged conversations) · #/room/<session> (conversation + votes of the room) ·
   #/users · #/user/<unaid> · #/leaderboard (the SAME leaderboard of the dashboard shown when
   joining the world: the src/stats.py aggregations are replicated here 1:1 — scopes, K, thresholds
   and roundings).
   ═══════════════════════════════════════════════════════ */

const API = window.API_OVERRIDE || "api.php";  // The override serves local tests (see the README)
const MEDALS = ["\u{1F947}", "\u{1F948}", "\u{1F949}"];
const MIN_VOTES = 1;             // src/stats.py: _MIN_VOTES
const K_TURING = 5;              // src/stats.py: _K of the votee (fooling) leaderboard
const K_DETECTION = 10;          // src/stats.py: _K of the voter (detection) leaderboard
const SCOPES = { max: 30 * 864e5, "7d": 7 * 864e5, "24h": 864e5 };  // src/stats.py: _SCOPE_WINDOWS_MS
const OPS_STATS = ["hotel_n_floors_active", "hotel_n_rooms_active", "hotel_n_rooms_overbooked",
                   "hotel_n_agents_present", "hotel_n_agents_waiting"];
const OPS_PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f"];  // src/stats.py: _PALETTE

const L = {
  site_loading: "Loading the Hotel…",
  site_error_api: "Could not load the Hotel data (<ERROR>). Is api.php configured?",
  site_error_generic: "Something went wrong: <ERROR>",
  site_error_convo: "Could not load the conversation: <ERROR>",
  site_not_found: "Page not found.",
  // Stats vocabulary as in src/stats.py (_HOTEL_OPS_LABELS, _SCOPE_LABELS, summary cards, confusion
  // matrix); leaderboard terms as in the English Turing Hotel renderer (Best Fooling/Detecting, ...)
  ops_labels: { hotel_n_floors_active: "Floors active", hotel_n_rooms_active: "Rooms active",
                hotel_n_rooms_overbooked: "Rooms overbooked",
                hotel_n_agents_present: "Agents in rooms", hotel_n_agents_waiting: "Agents waiting" },
  card_total_agents: "Total agents", card_active_rooms: "Active rooms", card_active_floors: "Active floors",
  card_votes: "Votes (<SCOPE>)",
  scope_labels: { max: "1 month (Max)", "7d": "7 days", "24h": "24 hours" },
  overview_title: "Overview", overview_chart: "Operational activity over time",
  floors_title: "Floors and rooms — present and past",
  floors_note: "Everything the archive knows: the rooms where votes were recorded and the logged " +
               "conversations.",
  floor_label: "Floor", room_label: "Room", rooms_label: "rooms",
  no_floors: "No recorded activity yet.",
  room_votes_badge_one: "1 vote", room_votes_badge: "<N> votes",
  room_convo_badge: "conversation logged",
  room_conversation: "Conversation", room_votes: "Votes cast in this room",
  room_not_logged: "The conversation of this room was not logged.",
  vote_cols: { voter: "Voter", nature: "Nature", vote: "Vote", truth: "Truth", outcome: "Outcome" },
  users_title: "Users", user_cols: { user: "User", nature: "Nature", cast: "Votes cast",
                                     received: "Votes received", last: "Last activity" },
  user_votes_cast: "Votes cast by", user_votes_received: "Votes received by",
  // The leaderboard labels below are VERBATIM from src/html_renderer.py (the dashboard shown when
  // joining the world IS this leaderboard: same tabs, columns, podium score labels, nature values)
  lb_title: "Leaderboard", lb_fooling: "Best Fooling", lb_detecting: "Best Detecting",
  lb_score_fooling: "Turing Score", lb_score_detecting: "Detection Score",
  lb_none: "No data (minimum vote threshold not reached).",
  cm_title: "Confusion matrix", cm_corner: "Truth \\ Vote",
  votee_cols: { peer: "AI Agent", votes: "Votes received", fooling: "Fooling rate %",
                avg_msgs: "Avg msgs sent", turing: "Turing score" },
  voter_cols: { peer: "Agent", nature: "Nature", votes: "Votes cast", precision: "Precision %",
                recall: "Recall %", f1: "F1 %", detection: "Detection score" },
  nature_human: "human", nature_ai: "ai",  // Raw values, as in the renderer's voter table
  search_placeholder: "Search…", pg_showing: "Showing", pg_results: () => "results",
};

/* ─── helpers ──────────────────────────────────────────── */
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fill = (t, map) => Object.entries(map).reduce((z, [k, v]) => z.split("<" + k + ">").join(String(v)), t);
const shortId = (unaid) => { const s = String(unaid || ""); const i = s.lastIndexOf("/");
  return i >= 0 ? s.substring(i + 1) : s; };
const short8 = (u) => String(u || "").substring(0, 8);
const round1 = (x) => Math.round(x * 10) / 10;
const fmtTs = (ts) => ts ? new Date(ts).toLocaleString() : "-";
const seg = (s) => encodeURIComponent(String(s));
const unseg = (s) => decodeURIComponent(String(s));
const natureLabel = (n) => n === "human" ? L.nature_human : (n === "ai" ? L.nature_ai : "-");
const GRID_LANG = () => ({ search: { placeholder: L.search_placeholder },
                           pagination: { previous: "←", next: "→",
                                         showing: L.pg_showing, results: L.pg_results } });

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  const body = await r.text();  // Read once: the error detail of api.php (or PHP error text) is in here
  if (!r.ok) throw new Error(url + " -> HTTP " + r.status + (body ? " — " + body.slice(0, 600) : ""));
  try {
    return JSON.parse(body);
  } catch (e) {
    throw new Error(url + " -> invalid JSON: " + body.slice(0, 600));
  }
}

/* ─── theme engine (same behavior as the dashboard) ────── */
let _theme = "dark";
function setTheme(m) {
  if (m !== "dark" && m !== "light") return;
  _theme = m;
  document.documentElement.setAttribute("data-theme", m);
  drawOpsChart();  // Re-style the Plotly chart, if on page
}
function toggleTheme() { setTheme(_theme === "dark" ? "light" : "dark"); }
window.toggleTheme = toggleTheme;
try {
  if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) setTheme("light");
} catch (e) { /* keep dark */ }

/* ─── data ─────────────────────────────────────────────── */
const DB = { ops: null, votes: [], sessions: [], floors: null, loaded: false, error: null };

async function loadAll() {
  const [ops, votes, sessions] = await Promise.all([
    getJSON(API + "?q=ops"), getJSON(API + "?q=votes"), getJSON(API + "?q=sessions")]);
  DB.ops = ops;
  DB.votes = votes;
  DB.sessions = sessions;

  // Floors -> rooms, from the votes (session_id = "<floor id>:<room id>") and the logged conversations
  const floors = new Map();
  const roomOf = (session) => {
    const parts = String(session || "").split(":");
    if (parts.length !== 2) return null;
    const [fid, rid] = parts;
    if (!floors.has(fid)) floors.set(fid, new Map());
    const rooms = floors.get(fid);
    if (!rooms.has(rid)) rooms.set(rid, { session, votes: [], convo: null, last_ts: 0 });
    return rooms.get(rid);
  };
  for (const rec of votes) {
    const room = roomOf(rec.v && rec.v.session_id);
    if (room) { room.votes.push(rec); room.last_ts = Math.max(room.last_ts, rec.ts); }
  }
  for (const s of sessions) {
    const room = roomOf(s.session);
    if (room) { room.convo = s; room.last_ts = Math.max(room.last_ts, s.last_ts); }
  }
  DB.floors = floors;
  DB.loaded = true;
}

/* ─── aggregations: 1:1 ports of src/stats.py ──────────── */
function votesInScope(scope) {
  const now = Date.now();
  return DB.votes.filter((r) => (now - r.ts) <= SCOPES[scope]);
}

function aggConfusion(votes) {  // WStats._compute_confusion_matrix
  const counts = { human: { human: 0, ai: 0 }, ai: { human: 0, ai: 0 } };
  for (const rec of votes) {
    const gt = rec.v.ground_truth, vt = rec.v.vote;
    if (counts[gt] && (vt === "human" || vt === "ai")) counts[gt][vt] += 1;
  }
  const pct = { human: { human: 0, ai: 0 }, ai: { human: 0, ai: 0 } };
  for (const gt of ["human", "ai"]) {
    const tot = counts[gt].human + counts[gt].ai;
    for (const vt of ["human", "ai"]) pct[gt][vt] = tot ? counts[gt][vt] / tot * 100 : 0;
  }
  return { counts, pct };
}

function aggVotee(votes) {  // WStats._compute_votee_leaderboard (AI-only, Turing score)
  const by = new Map();
  for (const rec of votes) {
    const vid = rec.votee || "", gt = rec.v.ground_truth;
    if (!vid || gt !== "ai") continue;
    if (!by.has(vid)) by.set(vid, { votes: 0, fooling: 0, msgs_total: 0 });
    const e = by.get(vid);
    e.votes += 1;
    if (rec.v.vote && rec.v.vote !== gt) e.fooling += 1;
    e.msgs_total += Number(rec.v.msgs_from_votee) || 0;
  }
  const rows = [];
  for (const [vid, e] of by) {
    if (e.votes < MIN_VOTES) continue;
    const fooling_rate = e.fooling / e.votes * 100;
    const avg_msgs = e.msgs_total / e.votes;
    rows.push({ peer_id: vid, votes: e.votes, fooling_rate: round1(fooling_rate),
                avg_msgs: round1(avg_msgs),
                turing_score: round1(fooling_rate * avg_msgs / (avg_msgs + K_TURING)) });
  }
  rows.sort((a, b) => b.turing_score - a.turing_score);
  return rows;
}

function aggVoter(votes) {  // WStats._compute_voter_leaderboard (positive class = human)
  const nature = new Map();
  for (const rec of votes) {
    const v = rec.v.voter, n = rec.v.voter_nature;
    if (v && (n === "human" || n === "ai")) nature.set(v, n);
  }
  const by = new Map();
  for (const rec of votes) {
    const vid = rec.v.voter || "";
    if (!vid) continue;
    if (!by.has(vid)) by.set(vid, { total: 0, tp: 0, fp: 0, tn: 0, fn: 0 });
    const e = by.get(vid);
    e.total += 1;
    const gt = rec.v.ground_truth, vt = rec.v.vote;
    if (vt !== "human" && vt !== "ai") continue;
    if (gt === "human" && vt === "human") e.tp += 1;
    else if (gt === "ai" && vt === "human") e.fp += 1;
    else if (gt === "ai" && vt === "ai") e.tn += 1;
    else if (gt === "human" && vt === "ai") e.fn += 1;
  }
  const fmt = (v) => v == null ? null : (v * 100).toFixed(1);
  const rows = [];
  for (const [vid, e] of by) {
    if (e.total < MIN_VOTES) continue;
    const prec = (e.tp + e.fp) ? e.tp / (e.tp + e.fp) : null;
    const rec_ = (e.tp + e.fn) ? e.tp / (e.tp + e.fn) : null;
    const f1 = (prec != null && rec_ != null && (prec + rec_) > 0)
      ? 2 * prec * rec_ / (prec + rec_) : null;
    const raw = f1 != null ? f1 * e.total / (e.total + K_DETECTION) : null;
    rows.push({ peer_id: vid, nature: nature.get(vid) || "-", votes: e.total,
                precision: fmt(prec), recall: fmt(rec_), f1: fmt(f1),
                detection_score: raw != null ? round1(raw * 100) : null,
                _sort: raw != null ? raw : -1 });
  }
  rows.sort((a, b) => b._sort - a._sort);
  return rows;
}

/* ─── shared fragments ─────────────────────────────────── */
const peerLink = (unaid) => `<a class="peer-cell" href="#/user/${seg(unaid)}" ` +
  `title="${esc(unaid)}">${esc(shortId(unaid))}</a>`;

function kpiCards() {
  const latest = (stat) => { const pts = (DB.ops.series || {})[stat] || [];
    return pts.length ? pts[pts.length - 1][1] : 0; };
  const cards = [
    [L.card_total_agents, DB.ops.n_total_agents == null ? 0 : DB.ops.n_total_agents],
    [L.card_active_rooms, latest("hotel_n_rooms_active")],
    [L.card_active_floors, latest("hotel_n_floors_active")],
    [fill(L.card_votes, { SCOPE: L.scope_labels[STATE.scope] }), votesInScope(STATE.scope).length],
  ];
  return '<div class="summary-bar">' + cards.map(([lbl, val]) =>
    `<div class="card"><span class="card-val">${esc(val)}</span>` +
    `<span class="card-lbl">${esc(lbl)}</span></div>`).join("") + "</div>";
}

/* ─── pages ────────────────────────────────────────────── */
const STATE = { scope: "max", lb: "fooling" };

function pageOverview() {
  return kpiCards() +
    `<div class="panel"><h3>${esc(L.overview_chart)}</h3>` +
    `<div id="chart-ops" style="height:320px"></div></div>`;
}

function drawOpsChart() {
  const el = document.getElementById("chart-ops");
  if (!el || !window.Plotly || !DB.ops) return;
  const css = getComputedStyle(document.documentElement);
  const traces = OPS_STATS.map((stat, i) => {
    const pts = (DB.ops.series || {})[stat] || [];
    return { x: pts.map(([ts]) => new Date(ts)), y: pts.map(([, v]) => v),
             name: L.ops_labels[stat], type: "scatter", mode: "lines",
             line: { color: OPS_PALETTE[i], width: 2, shape: "hv" } };
  }).filter((t) => t.x.length > 0);
  Plotly.react(el, traces, {
    margin: { l: 40, r: 10, t: 10, b: 40 },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: css.getPropertyValue("--text-secondary").trim() || "#888", size: 11 },
    xaxis: { gridcolor: css.getPropertyValue("--border").trim() },
    yaxis: { gridcolor: css.getPropertyValue("--border").trim(), rangemode: "tozero" },
    legend: { orientation: "h", y: -0.2 },
  }, { displayModeBar: false, responsive: true });
}

function pageFloors() {
  if (DB.floors.size === 0) return `<p class="empty">${esc(L.no_floors)}</p>`;
  let html = `<h2 class="section-title">${esc(L.floors_title)}</h2>` +
             `<p class="section-note">${esc(L.floors_note)}</p>`;
  const floors = [...DB.floors.entries()].sort((a, b) => {
    const last = (rooms) => Math.max(...[...rooms.values()].map((r) => r.last_ts));
    return last(b[1]) - last(a[1]);
  });
  for (const [fid, rooms] of floors) {
    const roomCards = [...rooms.entries()].sort((a, b) => b[1].last_ts - a[1].last_ts).map(([rid, r]) => {
      const badges = [];
      if (r.votes.length > 0) badges.push(`<span class="badge badge-past">` +
        esc(r.votes.length === 1 ? L.room_votes_badge_one
                                 : fill(L.room_votes_badge, { N: r.votes.length })) + `</span>`);
      if (r.convo) badges.push(`<span class="badge badge-live">${esc(L.room_convo_badge)}</span>`);
      return `<a class="circle-card" href="#/room/${seg(r.session)}">` +
        `<div class="circle-head"><span class="circle-code">${esc(short8(rid))}</span>` +
        `<span class="circle-occ">${esc(fmtTs(r.last_ts))}</span></div>` +
        `<div class="circle-name">${esc(L.room_label)} ${esc(short8(rid))}</div>` +
        `<div class="circle-topics">${badges.join(" ")}</div></a>`;
    }).join("");
    html += `<div class="sector-card"><div class="sector-head">` +
      `<h3>${esc(L.floor_label)} ${esc(short8(fid))}</h3>` +
      `<span class="sector-slots">${rooms.size} ${rooms.size === 1 ? esc(L.room_label.toLowerCase()) : esc(L.rooms_label)}</span>` +
      `</div><div class="circle-grid">${roomCards}</div></div>`;
  }
  return html;
}

async function pageRoom(session) {
  const parts = String(session).split(":");
  const [fid, rid] = parts.length === 2 ? parts : ["?", session];
  const rooms = DB.floors.get(fid);
  const room = rooms ? rooms.get(rid) : null;

  let convo = `<p class="empty">${esc(L.room_not_logged)}</p>`;
  if (room && room.convo) {
    try {
      const chunks = await getJSON(API + "?q=conversation&session=" + seg(session));
      const hues = {};  // Author -> hue by order of first appearance (golden-angle: far-apart colors)
      const hueOf = (name) => {
        const k = String(name || "?");
        if (!(k in hues)) hues[k] = Math.round(210 + Object.keys(hues).length * 137.508) % 360;
        return hues[k];
      };
      convo = '<div class="chat">' + chunks.map((ch) => {
        const m = ch.m || {};
        return `<div class="msg"><div class="msg-author" ` +
          `style="color:hsl(${hueOf(m.author_fake_name)} 60% var(--author-l))">` +
          `${esc(m.author_fake_name || "?")}` +
          `<span class="msg-unaid">${esc(shortId(m.author || ""))}</span></div>` +
          `<div class="msg-text">${esc(m.text || "")}</div>` +
          `<div class="msg-time">${fmtTs(m.ts || ch.ts)}</div></div>`;
      }).join("") + "</div>";
    } catch (e) {
      convo = `<div class="error-banner">${esc(fill(L.site_error_convo, { ERROR: e.message }))}</div>`;
    }
  }

  const votes = room ? room.votes : [];
  const voteRows = votes.map((rec) => {
    const ok = rec.v.vote === rec.v.ground_truth;
    return `<tr><td>${peerLink(rec.v.voter)}</td><td>${esc(natureLabel(rec.v.voter_nature))}</td>` +
      `<td>${esc(rec.v.vote)}</td><td>${esc(rec.v.ground_truth)}</td>` +
      `<td>${ok ? "✓" : "✗"}</td></tr>`;
  }).join("");
  const votesHtml = votes.length === 0 ? `<p class="empty">-</p>` :
    `<table class="cm-table"><thead><tr><th>${esc(L.vote_cols.voter)}</th>` +
    `<th>${esc(L.vote_cols.nature)}</th><th>${esc(L.vote_cols.vote)}</th>` +
    `<th>${esc(L.vote_cols.truth)}</th><th>${esc(L.vote_cols.outcome)}</th></tr></thead>` +
    `<tbody>${voteRows}</tbody></table>`;

  return `<div class="crumbs"><a href="#/floors">${esc(L.floors_title)}</a> / ` +
    `${esc(L.floor_label)} ${esc(short8(fid))} / ${esc(L.room_label)} ${esc(short8(rid))}</div>` +
    `<div class="two-col"><div class="panel"><h3>${esc(L.room_conversation)}</h3>${convo}</div>` +
    `<div class="panel"><h3>${esc(L.room_votes)}</h3>${votesHtml}</div></div>`;
}

function usersIndex() {
  const users = new Map();  // unaid -> {nature, cast, received, last_ts}
  const touch = (unaid) => {
    if (!unaid) return null;
    if (!users.has(unaid)) users.set(unaid, { nature: "-", cast: 0, received: 0, last_ts: 0 });
    return users.get(unaid);
  };
  for (const rec of DB.votes) {
    const voter = touch(rec.v.voter);
    if (voter) { voter.cast += 1; voter.last_ts = Math.max(voter.last_ts, rec.ts);
      if (rec.v.voter_nature) voter.nature = rec.v.voter_nature; }
    const votee = touch(rec.votee);
    if (votee) { votee.received += 1; votee.last_ts = Math.max(votee.last_ts, rec.ts);
      if (rec.v.ground_truth) votee.nature = rec.v.ground_truth; }
  }
  return users;
}

function pageUsers() {
  const data = [...usersIndex().entries()].map(([unaid, u]) =>
    [unaid, natureLabel(u.nature), u.cast, u.received, u.last_ts]);
  setTimeout(() => {
    const el = document.getElementById("users-grid");
    if (!el) return;
    new gridjs.Grid({
      columns: [{ name: L.user_cols.user, formatter: (c) => gridjs.html(peerLink(c)) },
                L.user_cols.nature, L.user_cols.cast, L.user_cols.received,
                { name: L.user_cols.last, formatter: (c) => fmtTs(c) }],
      data, search: true, sort: true, pagination: { limit: 20 }, language: GRID_LANG(),
    }).render(el);
  }, 0);
  return `<h2 class="section-title">${esc(L.users_title)}</h2><div id="users-grid"></div>`;
}

function pageUser(unaid) {
  const cast = DB.votes.filter((r) => r.v.voter === unaid);
  const received = DB.votes.filter((r) => r.votee === unaid);
  const u = usersIndex().get(unaid);
  const row = (rec, other) => `<tr><td>${peerLink(other)}</td><td>${esc(rec.v.vote)}</td>` +
    `<td>${esc(rec.v.ground_truth)}</td><td>${rec.v.vote === rec.v.ground_truth ? "✓" : "✗"}</td>` +
    `<td><a href="#/room/${seg(rec.v.session_id)}">${esc(short8(rec.v.session_id.split(":")[1] || ""))}</a></td>` +
    `<td>${esc(fmtTs(rec.ts))}</td></tr>`;
  const table = (rows) => rows.length === 0 ? `<p class="empty">-</p>` :
    `<table class="cm-table"><thead><tr><th>${esc(L.user_cols.user)}</th>` +
    `<th>${esc(L.vote_cols.vote)}</th><th>${esc(L.vote_cols.truth)}</th>` +
    `<th>${esc(L.vote_cols.outcome)}</th><th>${esc(L.room_label)}</th><th></th></tr></thead>` +
    `<tbody>${rows.join("")}</tbody></table>`;
  return `<div class="user-header"><div class="user-avatar">${esc(shortId(unaid).substring(0, 2).toUpperCase())}</div>` +
    `<div><h2>${esc(shortId(unaid))}</h2><div class="user-unaid">${esc(unaid)}` +
    `${u ? " · " + esc(natureLabel(u.nature)) : ""}</div></div></div>` +
    `<div class="two-col">` +
    `<div class="panel"><h3>${esc(L.user_votes_cast)} ${esc(shortId(unaid))}</h3>` +
    table(cast.map((r) => row(r, r.votee))) + `</div>` +
    `<div class="panel"><h3>${esc(L.user_votes_received)} ${esc(shortId(unaid))}</h3>` +
    table(received.map((r) => row(r, r.v.voter))) + `</div></div>`;
}

/* ─── leaderboard (same as the world dashboard) ────────── */
function cmTable(cm) {
  const bg = (p) => `rgb(${Math.round(255 - p * 0.8)},${Math.round(255 - p * 0.5)},${Math.round(255 - p * 0.1)})`;
  const fg = (p) => p > 45 ? "#0A1628" : "";  // Keep the cell text readable on the darker fills
  let html = `<table class="cm-table cm-colored"><thead><tr><th>${esc(L.cm_corner)}</th>` +
    `<th>human</th><th>ai</th></tr></thead><tbody>`;
  for (const gt of ["human", "ai"]) {
    html += `<tr><td><strong>${gt}</strong></td>`;
    for (const vt of ["human", "ai"]) {
      const c = cm.counts[gt][vt], p = cm.pct[gt][vt];
      html += `<td style="background:${bg(p)};color:${fg(p) || "#0A1628"}">${c}<br>` +
        `<small>${p.toFixed(1)}%</small></td>`;
    }
    html += "</tr>";
  }
  return html + "</tbody></table>";
}

function podium(rows, scoreKey, scoreLabel) {
  const top = rows.slice(0, 3);
  if (top.length === 0) return `<p class="empty">${esc(L.lb_none)}</p>`;
  return '<div class="podium">' + top.map((r, i) =>
    `<div class="podium-card"><div class="podium-medal">${MEDALS[i]}</div>` +
    `<div class="podium-rank">#${i + 1}</div>` +
    `<div class="podium-name">${peerLink(r.peer_id)}</div>` +
    `<div class="podium-score">${esc(r[scoreKey] == null ? "-" : r[scoreKey])}</div>` +
    `<div class="podium-score-label">${esc(scoreLabel)}</div></div>`).join("") + "</div>";
}

function pageLeaderboard() {
  const votes = votesInScope(STATE.scope);
  const fooling = STATE.lb === "fooling";
  const rows = fooling ? aggVotee(votes) : aggVoter(votes);
  const cm = aggConfusion(votes);

  const scopeBtns = Object.keys(SCOPES).map((k) =>
    `<button class="ctrl-btn${k === STATE.scope ? " active" : ""}" ` +
    `onclick="setScope('${k}')">${esc(L.scope_labels[k])}</button>`).join("");
  const lbBtns = [["fooling", L.lb_fooling], ["detecting", L.lb_detecting]].map(([k, lbl]) =>
    `<button class="ctrl-btn${k === STATE.lb ? " active" : ""}" ` +
    `onclick="setLB('${k}')">${esc(lbl)}</button>`).join("");

  const columns = fooling
    ? [{ name: "#", width: "52px" }, { name: L.votee_cols.peer, formatter: (c) => gridjs.html(peerLink(c)) },
       L.votee_cols.votes, L.votee_cols.fooling, L.votee_cols.avg_msgs, L.votee_cols.turing]
    : [{ name: "#", width: "52px" }, { name: L.voter_cols.peer, formatter: (c) => gridjs.html(peerLink(c)) },
       L.voter_cols.nature, L.voter_cols.votes, L.voter_cols.precision, L.voter_cols.recall,
       L.voter_cols.f1, L.voter_cols.detection];
  const data = rows.slice(0, 100).map((r, i) => fooling
    ? [i + 1, r.peer_id, r.votes, r.fooling_rate, r.avg_msgs, r.turing_score]
    : [i + 1, r.peer_id, natureLabel(r.nature), r.votes, r.precision ?? "-", r.recall ?? "-",
       r.f1 ?? "-", r.detection_score ?? "-"]);
  setTimeout(() => {
    const el = document.getElementById("lb-grid");
    if (!el) return;
    new gridjs.Grid({ columns, data, search: true, sort: true, pagination: { limit: 20 },
                      language: GRID_LANG() }).render(el);
  }, 0);

  return `<h2 class="section-title">${esc(L.lb_title)}</h2>` +
    podium(rows, fooling ? "turing_score" : "detection_score",
           fooling ? L.lb_score_fooling : L.lb_score_detecting) +
    `<div class="ctrl-bar">${scopeBtns}<span style="flex:1"></span>${lbBtns}</div>` +
    `<div id="lb-grid"></div>` +
    `<div class="two-col" style="margin-top:18px"><div class="panel">` +
    `<h3>${esc(L.cm_title)} — ${esc(L.scope_labels[STATE.scope])}</h3>${cmTable(cm)}</div><div></div></div>`;
}

window.setScope = (k) => { STATE.scope = k; route(); };
window.setLB = (k) => { STATE.lb = k; route(); };

/* ─── router ───────────────────────────────────────────── */
function applyNav(page) {
  document.querySelectorAll(".topnav a").forEach((a) =>
    a.classList.toggle("active", a.getAttribute("data-nav") === page));
}

async function route() {
  const app = $("#app");
  if (!DB.loaded) return;
  if (DB.error) { app.innerHTML = `<div class="error-banner">${esc(DB.error)}</div>`; return; }
  const hash = location.hash.replace(/^#\/?/, "");
  const parts = hash.split("/");
  const page = parts[0] || "overview";
  applyNav(page === "room" ? "floors" : (page === "user" ? "users" : page));
  try {
    if (page === "overview" || page === "") { app.innerHTML = pageOverview(); drawOpsChart(); }
    else if (page === "floors") app.innerHTML = pageFloors();
    else if (page === "room" && parts.length >= 2) app.innerHTML = await pageRoom(unseg(parts.slice(1).join("/")));
    else if (page === "users") app.innerHTML = pageUsers();
    else if (page === "user" && parts.length >= 2) app.innerHTML = pageUser(unseg(parts.slice(1).join("/")));
    else if (page === "leaderboard") app.innerHTML = pageLeaderboard();
    else app.innerHTML = `<p class="empty">${esc(L.site_not_found)}</p>`;
  } catch (e) {
    app.innerHTML = `<div class="error-banner">${esc(fill(L.site_error_generic, { ERROR: e.message }))}</div>`;
  }
}

window.addEventListener("hashchange", route);
$("#app").innerHTML = `<p class="empty">${esc(L.site_loading)}</p>`;
loadAll().then(route).catch((e) => {
  DB.error = fill(L.site_error_api, { ERROR: e.message });
  DB.loaded = true;
  route();
});
