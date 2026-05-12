"""Company Brain Knowledge Graph - HTML Dashboard Template."""


def render(vault_json: str = "{}") -> str:
    """Return the Company Brain knowledge graph HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Company Brain</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
--bg-primary:#1e1e1e;--bg-secondary:#252525;--bg-tertiary:#2b2b2b;
--bg-hover:#2e2e2e;--bg-active:#333;--bg-code:#2d2d2d;
--border:#3a3a3a;--border-light:#444;
--text:#dcddde;--text-muted:#999;--text-faint:#666;
--accent:#7f6df2;--accent-hover:#8b7cf3;
--link:#7f6df2;--tag:#e5c07b;
--h1:#e06c75;--h2:#61afef;--h3:#c678dd;
--bold:#e5c07b;
--green:#98c379;--red:#e06c75;--yellow:#e5c07b;--cyan:#56b6c2;
}}
html,body{{height:100%;overflow:hidden;background:var(--bg-primary);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px}}

.app{{display:flex;height:100vh;height:100%}}

/* ── SIDEBAR ────────────────────────── */
.sidebar{{width:260px;min-width:260px;background:var(--bg-secondary);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;user-select:none;transition:margin-left .25s ease,visibility .25s}}
.sidebar.collapsed{{margin-left:-260px;visibility:hidden;min-width:0}}
.sidebar-toggle{{background:none;border:none;color:var(--text-muted);cursor:pointer;padding:4px 6px;border-radius:3px;font-size:16px;line-height:1;flex-shrink:0}}
.sidebar-toggle:hover{{color:var(--text);background:var(--bg-hover)}}
.sidebar-top{{padding:8px 10px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}}
.sidebar-top input{{flex:1;background:var(--bg-tertiary);border:1px solid var(--border);border-radius:4px;padding:4px 8px;color:var(--text);font-size:12px;outline:none}}
.sidebar-top input:focus{{border-color:var(--accent)}}
.sidebar-top input::placeholder{{color:var(--text-faint)}}
.graph-btn{{background:none;border:1px solid var(--border);border-radius:4px;padding:4px 8px;color:var(--text-muted);cursor:pointer;font-size:11px;white-space:nowrap}}
.graph-btn:hover{{color:var(--text);border-color:var(--text-muted)}}
.graph-btn.active{{color:var(--accent);border-color:var(--accent)}}

.file-tree{{flex:1;overflow-y:auto;padding:4px 0}}
.file-tree::-webkit-scrollbar{{width:6px}}
.file-tree::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
.file-tree::-webkit-scrollbar-thumb:hover{{background:var(--border-light)}}

.folder{{margin:0}}
.folder-header{{display:flex;align-items:center;gap:4px;padding:2px 10px;cursor:pointer;color:var(--text-muted);font-size:13px}}
.folder-header:hover{{background:var(--bg-hover);color:var(--text)}}
.folder-header .arrow{{font-size:10px;width:14px;text-align:center;transition:transform .15s;color:var(--text-faint)}}
.folder-header.collapsed .arrow{{transform:rotate(-90deg)}}
.folder-header .fname{{flex:1}}
.folder-body{{padding-left:12px}}
.folder-body.hidden{{display:none}}

.file-item{{display:flex;align-items:center;gap:6px;padding:5px 10px 5px 16px;cursor:pointer;color:var(--text-muted);font-size:13px;border-radius:3px;margin:0 4px}}
.file-item:hover{{background:var(--bg-hover);color:var(--text)}}
.file-item.active{{background:var(--bg-active);color:var(--text)}}
.file-item .ficon{{color:var(--text-faint);font-size:11px;width:14px;text-align:center}}

.sidebar-bottom{{padding:6px 10px;border-top:1px solid var(--border);font-size:11px;color:var(--text-faint);display:flex;justify-content:space-between}}

/* ── MAIN ───────────────────────────── */
.main{{flex:1;display:flex;flex-direction:column;min-width:0}}

.topbar{{height:32px;min-height:32px;background:var(--bg-secondary);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 12px;gap:8px}}
.breadcrumb{{font-size:12px;color:var(--text-faint);flex:1;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.breadcrumb span{{color:var(--text-muted)}}
.view-toggle{{display:flex;gap:2px}}
.view-toggle button{{background:none;border:none;color:var(--text-faint);cursor:pointer;padding:2px 6px;font-size:11px;border-radius:3px}}
.view-toggle button:hover{{color:var(--text);background:var(--bg-hover)}}
.view-toggle button.active{{color:var(--accent)}}

.editor-area{{flex:1;overflow:hidden;display:flex}}

/* Source view */
.source-view{{width:100%;height:100%;display:none;overflow:auto}}
.source-view.active{{display:block}}
.source-view textarea{{width:100%;height:100%;background:var(--bg-primary);color:var(--text);border:none;outline:none;resize:none;padding:40px 60px;font-family:"SF Mono",Monaco,Menlo,"Courier New",monospace;font-size:14px;line-height:1.7;tab-size:4}}

/* Reading view */
.reading-view{{width:100%;height:100%;overflow-y:auto;display:none;padding:40px 60px}}
.reading-view.active{{display:block}}
.reading-view::-webkit-scrollbar{{width:6px}}
.reading-view::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

/* Markdown rendering */
.md-render{{max-width:760px;font-size:15px;line-height:1.75;color:var(--text)}}
.md-render h1{{font-size:1.8em;font-weight:700;color:var(--h1);margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--border)}}
.md-render h2{{font-size:1.4em;font-weight:600;color:var(--h2);margin:24px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--border)}}
.md-render h3{{font-size:1.15em;font-weight:600;color:var(--h3);margin:18px 0 6px}}
.md-render h4{{font-size:1em;font-weight:600;color:var(--text);margin:14px 0 4px}}
.md-render p{{margin:0 0 12px}}
.md-render ul,.md-render ol{{margin:0 0 12px;padding-left:22px}}
.md-render li{{margin:2px 0}}
.md-render li::marker{{color:var(--text-faint)}}
.md-render strong{{color:var(--bold);font-weight:600}}
.md-render em{{color:var(--text-muted)}}
.md-render a,.md-render .wikilink{{color:var(--link);text-decoration:none;cursor:pointer}}
.md-render a:hover,.md-render .wikilink:hover{{text-decoration:underline}}
.md-render .wikilink::before{{content:"";}} .md-render .wikilink::after{{content:"";}}
.md-render code{{font-family:"SF Mono",Monaco,Menlo,monospace;font-size:.88em;background:var(--bg-code);padding:2px 5px;border-radius:3px;color:var(--cyan)}}
.md-render pre{{background:var(--bg-code);border:1px solid var(--border);border-radius:4px;padding:14px;margin:10px 0;overflow-x:auto}}
.md-render pre code{{background:none;padding:0;font-size:13px;line-height:1.5;color:var(--text-muted)}}
.md-render blockquote{{border-left:3px solid var(--accent);padding:6px 14px;margin:10px 0;background:rgba(127,109,242,.06);color:var(--text-muted)}}
.md-render hr{{border:none;border-top:1px solid var(--border);margin:20px 0}}
.md-render table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
.md-render th{{text-align:left;padding:6px 10px;border-bottom:2px solid var(--border);color:var(--text);font-weight:600}}
.md-render td{{padding:6px 10px;border-bottom:1px solid var(--border)}}
.md-render tr:hover td{{background:var(--bg-hover)}}
.md-render .tag{{color:var(--tag);font-size:.9em}}
.md-render img{{max-width:100%;border-radius:4px}}

/* Backlinks */
.backlinks-section{{margin-top:40px;padding-top:20px;border-top:1px solid var(--border)}}
.backlinks-title{{font-size:12px;color:var(--text-faint);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.backlink-item{{display:block;padding:4px 0;color:var(--link);font-size:13px;cursor:pointer;text-decoration:none}}
.backlink-item:hover{{text-decoration:underline}}

/* ── GRAPH VIEW ─────────────────────── */
.graph-panel{{display:none;width:100%;height:100%;background:var(--bg-primary);position:relative}}
.graph-panel.active{{display:block}}
.graph-panel svg{{width:100%;height:100%}}
.graph-panel .node-label{{font-size:10px;fill:var(--text-muted);pointer-events:none;font-family:-apple-system,sans-serif}}
.graph-panel .node-circle{{cursor:pointer;transition:r .15s}}
.graph-panel .edge-line{{stroke:var(--border);stroke-width:.5}}
.graph-legend{{position:absolute;bottom:12px;left:12px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:4px;padding:8px 12px;font-size:11px}}
.graph-legend-item{{display:flex;align-items:center;gap:6px;margin:2px 0;color:var(--text-muted)}}
.graph-legend-dot{{width:8px;height:8px;border-radius:50%}}
.graph-info-bar{{position:absolute;top:8px;left:8px;font-size:11px;color:var(--text-faint)}}

/* Status bar */
.statusbar{{height:22px;min-height:22px;background:var(--bg-secondary);border-top:1px solid var(--border);display:flex;align-items:center;padding:0 10px;font-size:11px;color:var(--text-faint);gap:16px}}

/* ── RESPONSIVE ─────────────────────── */

/* Tables scroll horizontally on small screens */
.md-render .table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:12px -4px;padding:0 4px}}

/* Medium: sidebar overlay, narrower */
@media(max-width:760px){{
  .sidebar{{width:220px;min-width:220px;position:absolute;z-index:100;top:0;bottom:0;left:0;box-shadow:4px 0 12px rgba(0,0,0,.4)}}
  .sidebar.collapsed{{margin-left:-220px}}
  .reading-view{{padding:24px 20px}}
  .source-view textarea{{padding:24px 20px}}
  .md-render{{font-size:14px}}
  .md-render pre{{padding:10px;font-size:12px}}
  .md-render pre code{{font-size:11px}}
  .md-render table{{font-size:12px}}
  .md-render th,.md-render td{{padding:4px 6px}}
  .graph-legend{{padding:6px 8px;font-size:10px}}
}}

/* Small: even tighter, bigger touch targets */
@media(max-width:500px){{
  .sidebar{{width:85vw;min-width:0}}
  .sidebar.collapsed{{margin-left:-85vw}}
  .topbar{{padding:0 8px;gap:4px}}
  .breadcrumb{{font-size:11px}}
  .view-toggle button{{font-size:10px;padding:3px 5px}}
  .reading-view{{padding:16px 14px}}
  .source-view textarea{{padding:16px 14px;font-size:13px}}
  .md-render{{font-size:13px;line-height:1.65}}
  .md-render h1{{font-size:1.5em}}
  .md-render h2{{font-size:1.2em}}
  .md-render h3{{font-size:1.05em}}
  .md-render pre{{padding:8px;margin:8px 0}}
  .md-render pre code{{font-size:10.5px}}
  .md-render blockquote{{padding:4px 10px}}
  .file-item{{padding:7px 10px 7px 14px;font-size:14px}}
  .folder-header{{padding:6px 10px;font-size:14px}}
  .statusbar{{font-size:10px;gap:10px;padding:0 8px}}
  .graph-legend{{bottom:6px;left:6px;font-size:9px;padding:4px 6px}}
  .graph-info-bar{{font-size:10px}}
}}

/* Very small height: hide statusbar, compress topbar */
@media(max-height:450px){{
  .statusbar{{display:none}}
  .topbar{{height:28px;min-height:28px}}
  .reading-view{{padding-top:12px;padding-bottom:12px}}
}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="sidebar-top">
<input type="text" id="search" placeholder="Search..." spellcheck="false">
<button class="graph-btn" id="toggle-graph">Graph</button>
</div>
<div class="file-tree" id="file-tree"></div>
<div class="sidebar-bottom">
<span id="file-count"></span>
<span>Company Brain</span>
</div>
</aside>
<div class="main">
<div class="topbar">
<button class="sidebar-toggle" id="sidebar-toggle" title="Toggle sidebar">&#9776;</button>
<div class="breadcrumb" id="breadcrumb">Select a file</div>
<div class="view-toggle">
<button class="active" id="btn-read">Reading</button>
<button id="btn-source">Source</button>
</div>
</div>
<div class="editor-area" id="editor-area">
<div class="reading-view active" id="reading-view"><div class="md-render" id="md-render"><p style="color:var(--text-faint);margin-top:40px">Select a file from the sidebar to view its contents.</p></div></div>
<div class="source-view" id="source-view"><textarea id="source-editor" spellcheck="false"></textarea></div>
<div class="graph-panel" id="graph-panel"><svg id="graph-svg"></svg>
<div class="graph-legend" id="graph-legend"></div>
<div class="graph-info-bar" id="graph-info-bar"></div>
</div>
</div>
<div class="statusbar"><span id="sb-lines">0 lines</span><span id="sb-words">0 words</span><span id="sb-links">0 links</span></div>
</div>
</div>

<script>
const vault = {vault_json};


// ═══════════════════════════════════════════════════════════════
// APP LOGIC
// ═══════════════════════════════════════════════════════════════

const fileTree = {{}};
Object.keys(vault).forEach(path => {{
  const parts = path.split('/');
  const folder = parts[0];
  const file = parts.slice(1).join('/');
  if (!fileTree[folder]) fileTree[folder] = [];
  fileTree[folder].push({{ path, name: file }});
}});

// Build sidebar
function buildSidebar(filter = '') {{
  const el = document.getElementById('file-tree');
  el.innerHTML = '';
  const fl = filter.toLowerCase();
  let totalFiles = 0;

  Object.entries(fileTree).forEach(([folder, files]) => {{
    const filtered = files.filter(f => !fl || f.name.toLowerCase().includes(fl) || f.path.toLowerCase().includes(fl));
    if (filtered.length === 0) return;
    totalFiles += filtered.length;

    const div = document.createElement('div');
    div.className = 'folder';

    const header = document.createElement('div');
    header.className = 'folder-header';
    header.innerHTML = `<span class="arrow">▾</span><span class="fname">${{folder}}</span>`;
    header.addEventListener('click', () => {{
      header.classList.toggle('collapsed');
      body.classList.toggle('hidden');
    }});

    const body = document.createElement('div');
    body.className = 'folder-body';

    filtered.forEach(f => {{
      const item = document.createElement('div');
      item.className = 'file-item' + (currentFile === f.path ? ' active' : '');
      item.innerHTML = `<span class="ficon">◇</span><span>${{f.name}}</span>`;
      item.addEventListener('click', () => openFile(f.path));
      body.appendChild(item);
    }});

    div.appendChild(header);
    div.appendChild(body);
    el.appendChild(div);
  }});
  document.getElementById('file-count').textContent = totalFiles + ' files';
}}

// State
let currentFile = null;
let viewMode = 'reading'; // reading | source
let graphActive = false;

// Open file
function openFile(path) {{
  currentFile = path;
  const content = vault[path] || '';
  document.getElementById('breadcrumb').innerHTML = path.split('/').map(p => `<span>${{p}}</span>`).join(' / ');

  // Source
  document.getElementById('source-editor').value = content;

  // Reading
  renderMarkdown(content);

  // Update sidebar highlight
  document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.file-item').forEach(el => {{
    if (el.textContent.trim() === path.split('/').slice(1).join('/')) el.classList.add('active');
  }});

  // Status bar
  const lines = content.split('\\n').length;
  const words = content.split(/\\s+/).filter(w => w).length;
  const links = (content.match(/\\[\\[/g) || []).length;
  document.getElementById('sb-lines').textContent = lines + ' lines';
  document.getElementById('sb-words').textContent = words + ' words';
  document.getElementById('sb-links').textContent = links + ' links';

  // Show editor, hide graph
  if (graphActive) toggleGraph();
  showView(viewMode);
  buildSidebar(document.getElementById('search').value);

  // On small screens, close sidebar after file selection
  if (window.innerWidth <= 760) document.querySelector('.sidebar').classList.add('collapsed');
}}

function renderMarkdown(content) {{
  // Convert [[wikilinks]] to clickable spans
  let processed = content.replace(/\\[\\[([^\\]]+)\\]\\]/g, (match, name) => {{
    return `<span class="wikilink" data-link="${{name}}">${{name}}</span>`;
  }});

  const html = marked.parse(processed);
  const renderEl = document.getElementById('md-render');
  renderEl.innerHTML = html;

  // Add backlinks section
  const backlinks = findBacklinks(currentFile);
  if (backlinks.length > 0) {{
    const section = document.createElement('div');
    section.className = 'backlinks-section';
    section.innerHTML = `<div class="backlinks-title">${{backlinks.length}} Backlinks</div>`;
    backlinks.forEach(bl => {{
      const a = document.createElement('a');
      a.className = 'backlink-item';
      a.textContent = bl;
      a.addEventListener('click', () => navigateToLink(bl));
      section.appendChild(a);
    }});
    renderEl.appendChild(section);
  }}

  // Wire up wikilinks
  renderEl.querySelectorAll('.wikilink').forEach(el => {{
    el.addEventListener('click', () => navigateToLink(el.dataset.link));
  }});

  // Wrap tables for horizontal scroll on small screens
  renderEl.querySelectorAll('table').forEach(table => {{
    if (table.parentElement.classList.contains('table-wrap')) return;
    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  }});
}}

function findBacklinks(path) {{
  if (!path) return [];
  const name = path.split('/').pop();
  const results = [];
  Object.entries(vault).forEach(([p, content]) => {{
    if (p === path) return;
    if (content.includes(`[[${{name}}]]`)) {{
      results.push(p.split('/').pop());
    }}
  }});
  return results;
}}

function navigateToLink(name) {{
  // Find file matching the link name
  const match = Object.keys(vault).find(p => {{
    const fname = p.split('/').pop();
    return fname === name || fname.replace(/ /g, '') === name.replace(/ /g, '');
  }});
  if (match) openFile(match);
}}

// View toggle
function showView(mode) {{
  viewMode = mode;
  document.getElementById('reading-view').classList.toggle('active', mode === 'reading');
  document.getElementById('source-view').classList.toggle('active', mode === 'source');
  document.getElementById('btn-read').classList.toggle('active', mode === 'reading');
  document.getElementById('btn-source').classList.toggle('active', mode === 'source');
}}

document.getElementById('btn-read').addEventListener('click', () => {{
  // Sync changes from source editor
  if (currentFile) {{
    vault[currentFile] = document.getElementById('source-editor').value;
    renderMarkdown(vault[currentFile]);
  }}
  showView('reading');
}});
document.getElementById('btn-source').addEventListener('click', () => showView('source'));

// Source editor live sync
document.getElementById('source-editor').addEventListener('input', function() {{
  if (currentFile) {{
    vault[currentFile] = this.value;
    const lines = this.value.split('\\n').length;
    const words = this.value.split(/\\s+/).filter(w => w).length;
    const links = (this.value.match(/\\[\\[/g) || []).length;
    document.getElementById('sb-lines').textContent = lines + ' lines';
    document.getElementById('sb-words').textContent = words + ' words';
    document.getElementById('sb-links').textContent = links + ' links';
  }}
}});

// Search
document.getElementById('search').addEventListener('input', function() {{
  buildSidebar(this.value);
}});

// ═══════════════════════════════════════════════════════════════
// GRAPH VIEW
// ═══════════════════════════════════════════════════════════════

const GRAPH_COLORS = {{
  People: '#d97706',
  Agents: '#0891b2',
  Projects: '#059669',
  Knowledge: '#7c3aed',
  Meetings: '#2563eb',
  Incidents: '#dc2626',
  Decisions: '#e5c07b'
}};

function toggleGraph() {{
  graphActive = !graphActive;
  document.getElementById('toggle-graph').classList.toggle('active', graphActive);
  document.getElementById('graph-panel').classList.toggle('active', graphActive);
  document.getElementById('reading-view').classList.toggle('active', !graphActive && viewMode === 'reading');
  document.getElementById('source-view').classList.toggle('active', !graphActive && viewMode === 'source');
  if (graphActive) {{
    document.querySelector('.sidebar').classList.add('collapsed');
    buildGraph();
  }}
}}

document.getElementById('toggle-graph').addEventListener('click', toggleGraph);

function buildGraph() {{
  const svgEl = d3.select('#graph-svg');
  svgEl.selectAll('*').remove();

  const container = document.getElementById('graph-panel');
  const W = container.clientWidth;
  const H = container.clientHeight;
  svgEl.attr('width', W).attr('height', H);

  // Build nodes from vault
  const graphNodes = [];
  const nodeMap = {{}};
  Object.keys(vault).forEach(path => {{
    const parts = path.split('/');
    const folder = parts[0];
    const name = parts.slice(1).join('/');
    const id = name;
    const color = GRAPH_COLORS[folder] || '#999';
    graphNodes.push({{ id, path, folder, color, r: 5 }});
    nodeMap[name] = graphNodes.length - 1;
  }});

  // Build edges from [[wikilinks]]
  const graphEdges = [];
  const edgeSet = new Set();
  Object.entries(vault).forEach(([path, content]) => {{
    const sourceName = path.split('/').slice(1).join('/');
    const matches = content.match(/\\[\\[([^\\]]+)\\]\\]/g) || [];
    matches.forEach(m => {{
      const targetName = m.slice(2, -2);
      if (nodeMap[targetName] !== undefined && targetName !== sourceName) {{
        const key = [sourceName, targetName].sort().join('|||');
        if (!edgeSet.has(key)) {{
          edgeSet.add(key);
          graphEdges.push({{ source: sourceName, target: targetName }});
        }}
      }}
    }});
  }});

  // Count connections for sizing
  const connCount = {{}};
  graphNodes.forEach(n => connCount[n.id] = 0);
  graphEdges.forEach(e => {{
    if (connCount[e.source] !== undefined) connCount[e.source]++;
    if (connCount[e.target] !== undefined) connCount[e.target]++;
  }});
  graphNodes.forEach(n => {{ n.r = 3 + Math.min(connCount[n.id] * 1.2, 12); }});

  const g = svgEl.append('g');

  const zoom = d3.zoom().scaleExtent([0.2, 5]).on('zoom', ev => g.attr('transform', ev.transform));
  svgEl.call(zoom);

  const sim = d3.forceSimulation(graphNodes)
    .force('link', d3.forceLink(graphEdges).id(d => d.id).distance(80).strength(0.2))
    .force('charge', d3.forceManyBody().strength(-120).distanceMax(300))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide().radius(d => d.r + 4));

  const edges = g.append('g').selectAll('line').data(graphEdges).join('line')
    .attr('class', 'edge-line');

  const nodeGroups = g.append('g').selectAll('g').data(graphNodes).join('g')
    .attr('class', 'node-group')
    .call(d3.drag()
      .on('start', (ev, d) => {{ if (!ev.active) sim.alphaTarget(.3).restart(); d.fx = d.x; d.fy = d.y; }})
      .on('drag', (ev, d) => {{ d.fx = ev.x; d.fy = ev.y; }})
      .on('end', (ev, d) => {{ if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }}));

  nodeGroups.append('circle')
    .attr('class', 'node-circle')
    .attr('r', d => d.r)
    .attr('fill', d => d.color)
    .attr('fill-opacity', .85)
    .attr('stroke', d => d.color)
    .attr('stroke-width', .5)
    .attr('stroke-opacity', .3);

  const labels = nodeGroups.append('text')
    .attr('class', 'node-label')
    .attr('y', d => d.r + 12)
    .attr('text-anchor', 'middle')
    .text(d => d.id);

  // Hover
  nodeGroups.on('mouseenter', function(ev, d) {{
    d3.select(this).select('.node-circle').attr('r', d.r + 2);
    const connected = new Set();
    graphEdges.forEach(e => {{
      const s = typeof e.source === 'string' ? e.source : e.source.id;
      const t = typeof e.target === 'string' ? e.target : e.target.id;
      if (s === d.id) connected.add(t);
      if (t === d.id) connected.add(s);
    }});
    nodeGroups.select('.node-circle').attr('fill-opacity', n => n.id === d.id || connected.has(n.id) ? .9 : .15);
    labels.attr('fill-opacity', n => n.id === d.id || connected.has(n.id) ? 1 : .1);
    edges.attr('stroke-opacity', e => {{
      const s = typeof e.source === 'string' ? e.source : e.source.id;
      const t = typeof e.target === 'string' ? e.target : e.target.id;
      return s === d.id || t === d.id ? .6 : .05;
    }}).attr('stroke', e => {{
      const s = typeof e.source === 'string' ? e.source : e.source.id;
      const t = typeof e.target === 'string' ? e.target : e.target.id;
      return s === d.id || t === d.id ? d.color : '#3a3a3a';
    }});
  }}).on('mouseleave', function(ev, d) {{
    d3.select(this).select('.node-circle').attr('r', d.r);
    nodeGroups.select('.node-circle').attr('fill-opacity', .85);
    labels.attr('fill-opacity', 1);
    edges.attr('stroke-opacity', .3).attr('stroke', '#3a3a3a');
  }}).on('click', function(ev, d) {{
    ev.stopPropagation();
    openFile(d.path);
  }});

  sim.on('tick', () => {{
    edges.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
         .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    nodeGroups.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});

  // Info
  document.getElementById('graph-info-bar').textContent = `${{graphNodes.length}} notes · ${{graphEdges.length}} links`;

  // Legend
  const legend = document.getElementById('graph-legend');
  legend.innerHTML = '';
  Object.entries(GRAPH_COLORS).forEach(([name, color]) => {{
    const count = graphNodes.filter(n => n.folder === name).length;
    if (count === 0) return;
    const item = document.createElement('div');
    item.className = 'graph-legend-item';
    item.innerHTML = `<div class="graph-legend-dot" style="background:${{color}}"></div>${{name}} (${{count}})`;
    legend.appendChild(item);
  }});
}}

// Keyboard shortcuts
document.addEventListener('keydown', e => {{
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {{ e.preventDefault(); document.getElementById('search').focus(); }}
  if (e.key === 'Escape' && graphActive) toggleGraph();
  if ((e.metaKey || e.ctrlKey) && e.key === 'g') {{ e.preventDefault(); toggleGraph(); }}
}});

// ═══════════════════════════════════════════════════════════════
// RESPONSIVE
// ═══════════════════════════════════════════════════════════════

const sidebarEl = document.querySelector('.sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');

sidebarToggle.addEventListener('click', () => sidebarEl.classList.toggle('collapsed'));

function checkResponsive() {{
  const mobile = window.innerWidth <= 760;
  if (mobile) {{
    sidebarEl.classList.add('collapsed');
  }} else {{
    sidebarEl.classList.remove('collapsed');
  }}
}}
window.addEventListener('resize', checkResponsive);
checkResponsive();

// Init
buildSidebar();

// Open first file
openFile('People/Tommaso Guidi');
</script>
</body>
</html>"""
