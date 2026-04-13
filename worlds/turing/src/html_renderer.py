"""
Turing Hotel Leaderboard - Premium Dashboard Template
=====================================================

Responsive, theme-aware (dark/light) HTML dashboard with Material Design
aesthetics, Plotly.js charts, and Google Fonts typography.

Usage::

    from turing_leaderboard_template import render, THEMES

    html = render(
        summary_html=build_summary_cards(),
        scope_tab_buttons=build_tabs(),
        scope_blocks_html=build_scope_panels(),
        default_scope="overall",
        ops_html=build_occupancy_chart(),
    )

Iframe theme detection (auto):
    1. prefers-color-scheme media query
    2. postMessage from parent:  parent.postMessage({theme:'dark'}, '*')
    3. MutationObserver on parent data-theme attribute (same-origin)
    4. URL parameter: ?theme=light
"""

def render(
    summary_html: str = "",
    scope_tab_buttons: str = "",
    scope_blocks_html: str = "",
    default_scope: str = "overall",
    ops_json: str = "[]",
    top_foolers_json: str = "[]",
    top_detectors_json: str = "[]",
) -> str:
    """Return the complete leaderboard HTML."""

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=5.0">
<meta name="color-scheme" content="dark light">
<title>Turing Hotel - Leaderboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@300;400;500;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>

<style>
/* ═══════════════════════════════════════════════════════
   THEME VARIABLES
   ═══════════════════════════════════════════════════════ */
:root,[data-theme="dark"]{{
  --bg-body:#050507;
  --bg-subtle:#0E0F14;
  --bg-paper:#16171C;
  --bg-elevated:#1F2025;
  --border:#222A36;
  --border-subtle:#1F2025;
  --border-strong:#323C4A;
  --text-primary:#F5F6F8;
  --text-secondary:#C8CDD3;
  --text-muted:#677385;
  --text-disabled:#495464;
  --primary:#1A5CFF;
  --primary-light:#4D7FFF;
  --primary-dark:#1248CC;
  --primary-a12:rgba(26,92,255,.12);
  --primary-a20:rgba(26,92,255,.20);
  --teal:#00D4AA;
  --teal-a12:rgba(0,212,170,.12);
  --amber:#FFB347;
  --amber-a12:rgba(255,179,71,.12);
  --error:#FF3B30;
  --shadow-xs:inset 0 1px 0 rgba(255,255,255,.04),0 1px 2px rgba(0,0,0,.6);
  --shadow-sm:inset 0 1px 0 rgba(255,255,255,.05),0 2px 4px rgba(0,0,0,.5),0 4px 12px rgba(0,0,0,.4);
  --shadow-md:inset 0 1px 0 rgba(255,255,255,.06),0 4px 8px rgba(0,0,0,.55),0 8px 24px rgba(0,0,0,.5);
  --shadow-lg:inset 0 1px 0 rgba(255,255,255,.07),0 8px 16px rgba(0,0,0,.6),0 16px 40px rgba(0,0,0,.6);
  --hover-bg:rgba(255,255,255,.04);
  --hover-bg-strong:rgba(255,255,255,.08);
  --tab-active-bg:rgba(26,92,255,.18);
  --tab-active-text:#4D7FFF;
  --tab-active-shadow:inset 0 1px 0 rgba(26,92,255,.2),0 1px 2px rgba(0,0,0,.4);
  --card-hover-border:#323C4A;
  --table-header-bg:rgba(255,255,255,.03);
  --table-row-hover:rgba(255,255,255,.02);
  --table-stripe:rgba(255,255,255,.015);
  --scrollbar-thumb:#222A36;
  --scrollbar-hover:#323C4A;
  --glass-bg:rgba(10,22,40,.75);
  --glass-border:rgba(255,255,255,.08);
  --gradient-accent:linear-gradient(135deg,#1A5CFF,#00D4AA);
}}
[data-theme="light"]{{
  --bg-body:#EDF1F5;
  --bg-subtle:#F6F8FA;
  --bg-paper:#FFFFFF;
  --bg-elevated:#FFFFFF;
  --border:#C0C8D6;
  --border-subtle:#DBE1EB;
  --border-strong:#909CB0;
  --text-primary:#0A1628;
  --text-secondary:#666666;
  --text-muted:#677385;
  --text-disabled:#909CB0;
  --primary:#1A5CFF;
  --primary-light:#4D7FFF;
  --primary-dark:#1248CC;
  --primary-a12:rgba(26,92,255,.08);
  --primary-a20:rgba(26,92,255,.12);
  --teal:#00D4AA;
  --teal-a12:rgba(0,212,170,.08);
  --amber:#FFB347;
  --amber-a12:rgba(255,179,71,.08);
  --error:#FF3B30;
  --shadow-xs:0 1px 2px rgba(10,22,40,.06),0 1px 1px rgba(10,22,40,.04);
  --shadow-sm:0 1px 2px rgba(10,22,40,.05),0 2px 6px rgba(10,22,40,.06);
  --shadow-md:0 2px 4px rgba(10,22,40,.06),0 6px 16px rgba(10,22,40,.08);
  --shadow-lg:0 4px 8px rgba(10,22,40,.06),0 12px 28px rgba(10,22,40,.10);
  --hover-bg:rgba(10,22,40,.04);
  --hover-bg-strong:rgba(10,22,40,.06);
  --tab-active-bg:#FFFFFF;
  --tab-active-text:#0A1628;
  --tab-active-shadow:0 1px 2px rgba(10,22,40,.08),0 2px 4px rgba(10,22,40,.06),0 0 0 1px rgba(192,200,214,.6);
  --card-hover-border:#909CB0;
  --table-header-bg:#F6F8FA;
  --table-row-hover:rgba(10,22,40,.015);
  --table-stripe:rgba(10,22,40,.02);
  --scrollbar-thumb:#C0C8D6;
  --scrollbar-hover:#909CB0;
  --glass-bg:rgba(255,255,255,.72);
  --glass-border:rgba(0,0,0,.08);
  --gradient-accent:linear-gradient(135deg,#1A5CFF,#00D4AA);
}}

/* ═══════════════════════════════════════════════════════
   RESET & BASE
   ═══════════════════════════════════════════════════════ */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;-webkit-text-size-adjust:100%}}
body{{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;
  background:var(--bg-body);
  color:var(--text-primary);
  line-height:1.55;font-size:.9375rem;
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  padding:0;margin:0;
  transition:background-color .4s ease,color .3s ease;
}}
::selection{{background:rgba(26,92,255,.25);color:inherit}}

/* Scrollbar */
::-webkit-scrollbar{{width:7px;height:7px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:var(--scrollbar-thumb);border-radius:4px}}
::-webkit-scrollbar-thumb:hover{{background:var(--scrollbar-hover)}}
*{{scrollbar-width:thin;scrollbar-color:var(--scrollbar-thumb) transparent}}

/* ═══════════════════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════════════════ */
h1,h2,h3,h4{{font-family:'Space Grotesk','Inter',sans-serif;letter-spacing:-.02em;line-height:1.2}}
h1{{font-weight:700;font-size:clamp(1.4rem,3vw,1.85rem);color:var(--text-primary)}}
h2{{
  font-weight:600;font-size:.75rem;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:.1em;margin:0 0 16px;
}}
h3{{font-weight:600;font-size:.9375rem;color:var(--text-primary);letter-spacing:-.01em}}

/* ═══════════════════════════════════════════════════════
   LAYOUT
   ═══════════════════════════════════════════════════════ */
.dashboard{{max-width:1440px;margin:0 auto;padding:28px 24px 40px}}

/* ═══════════════════════════════════════════════════════
   HEADER
   ═══════════════════════════════════════════════════════ */
.dashboard-header{{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:32px;padding-bottom:20px;
  border-bottom:1px solid var(--border);
  position:relative;
}}
.dashboard-header::after{{
  content:'';position:absolute;bottom:-1px;left:0;
  width:100px;height:2.5px;border-radius:2px;
  background:var(--gradient-accent);
}}
.header-left{{display:flex;align-items:center;gap:14px}}
.brand-mark{{
  width:38px;height:38px;border-radius:10px;flex-shrink:0;
  background:var(--gradient-accent);
  box-shadow:0 2px 10px rgba(26,92,255,.30);
  transition:transform .3s ease,box-shadow .3s ease;
}}
.brand-mark:hover{{transform:scale(1.06);box-shadow:0 4px 18px rgba(26,92,255,.40)}}
.header-subtitle{{
  font-family:'Inter',sans-serif;font-size:.6875rem;font-weight:600;
  color:var(--text-muted);letter-spacing:.08em;text-transform:uppercase;
  margin-top:2px;
}}

/* Theme toggle */
.theme-toggle{{
  background:var(--bg-subtle);border:1px solid var(--border);border-radius:8px;
  width:38px;height:38px;cursor:pointer;color:var(--text-muted);
  display:flex;align-items:center;justify-content:center;
  transition:all .2s ease;flex-shrink:0;
}}
.theme-toggle:hover{{border-color:var(--primary);color:var(--primary);background:var(--primary-a12)}}
[data-theme="dark"] .ico-dark{{display:none}}
[data-theme="dark"] .ico-light{{display:flex}}
[data-theme="light"] .ico-dark{{display:flex}}
[data-theme="light"] .ico-light{{display:none}}

/* ═══════════════════════════════════════════════════════
   KPI / SUMMARY CARDS
   ═══════════════════════════════════════════════════════ */
.summary-bar{{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
  gap:12px;margin-bottom:32px;
}}
.card{{
  background:var(--bg-paper);
  border:1px solid var(--border);border-radius:12px;
  padding:18px 16px 14px;
  display:flex;flex-direction:column;align-items:center;
  position:relative;overflow:hidden;
  transition:border-color .25s ease,box-shadow .25s ease,transform .25s cubic-bezier(.2,0,0,1),background-color .3s ease;
}}
.card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:var(--gradient-accent);opacity:0;
  transition:opacity .25s ease;
}}
.card:hover{{
  border-color:var(--card-hover-border);
  box-shadow:var(--shadow-md);
  transform:translateY(-2px);
}}
.card:hover::before{{opacity:1}}
.card-val{{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.75rem;font-weight:700;
  color:var(--text-primary);
  font-feature-settings:'tnum';line-height:1.1;
  transition:color .3s ease;
}}
.card-lbl{{
  font-size:.6875rem;font-weight:600;color:var(--text-muted);
  margin-top:6px;text-align:center;
  text-transform:uppercase;letter-spacing:.06em;
  transition:color .3s ease;
}}
.card.muted .card-val{{font-size:.9375rem;color:var(--text-muted)}}

/* ═══════════════════════════════════════════════════════
   TAB BAR
   ═══════════════════════════════════════════════════════ */
.tab-bar{{
  display:flex;gap:4px;margin-bottom:24px;padding:4px;
  background:var(--bg-subtle);border:1px solid var(--border);border-radius:10px;
  overflow-x:auto;-webkit-overflow-scrolling:touch;
  transition:background-color .3s ease,border-color .3s ease;
}}
.tab-bar::-webkit-scrollbar{{height:0;display:none}}
.tab-btn{{
  background:transparent;border:none;border-radius:7px;
  padding:8px 20px;color:var(--text-muted);cursor:pointer;
  font-family:'Inter',sans-serif;font-size:.8125rem;font-weight:600;
  white-space:nowrap;
  transition:all .2s cubic-bezier(.2,0,0,1);
}}
.tab-btn:hover{{color:var(--text-secondary);background:var(--hover-bg)}}
.tab-btn.active{{
  background:var(--tab-active-bg);
  color:var(--tab-active-text);
  box-shadow:var(--tab-active-shadow);
}}

/* ═══════════════════════════════════════════════════════
   SCOPE PANELS & TWO-COLUMN LAYOUT
   ═══════════════════════════════════════════════════════ */
.scope-panel{{display:none}}
.scope-panel.visible{{display:block;animation:fadeInUp .3s ease}}
.two-col{{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap}}
.col-narrow{{flex:0 0 auto;max-width:380px}}
.col-wide{{flex:1 1 300px;min-width:0;overflow-x:auto;-webkit-overflow-scrolling:touch}}

/* ═══════════════════════════════════════════════════════
   LEADERBOARD TABLE
   ═══════════════════════════════════════════════════════ */
.lb-table{{border-collapse:collapse;font-size:.8125rem;width:100%}}
.lb-table th{{
  background:var(--table-header-bg);
  color:var(--text-muted);font-weight:700;font-size:.6875rem;
  text-transform:uppercase;letter-spacing:.06em;
  padding:11px 14px;
  border-bottom:2px solid var(--border);
  cursor:pointer;user-select:none;text-align:center;white-space:nowrap;
  transition:color .15s ease,background-color .3s ease;
}}
.lb-table th:hover{{color:var(--primary)}}
.lb-table th:first-child,.lb-table td:first-child{{text-align:left}}
.lb-table td{{
  padding:9px 14px;text-align:right;
  border-bottom:1px solid var(--border-subtle);
  font-feature-settings:'tnum';color:var(--text-secondary);
  transition:background-color .1s ease,color .3s ease;
}}
.lb-table tbody tr:nth-child(even){{background:var(--table-stripe)}}
.lb-table tbody tr:hover{{background:var(--table-row-hover)}}
.lb-table tbody tr:hover td{{color:var(--text-primary)}}
.sort-arrow{{font-size:.65rem;color:var(--text-disabled);margin-left:3px}}

/* ═══════════════════════════════════════════════════════
   CONFUSION MATRIX TABLE
   ═══════════════════════════════════════════════════════ */
.cm-table{{border-collapse:collapse;font-size:.8125rem}}
.cm-table td,.cm-table th{{
  border:1px solid var(--border);padding:7px 11px;text-align:center;
  font-feature-settings:'tnum';transition:border-color .3s ease;
}}
.cm-table th{{
  background:var(--table-header-bg);color:var(--text-muted);
  font-weight:600;font-size:.75rem;
}}
.cm-table td{{color:#1a1a1a;font-weight:600}}

/* ═══════════════════════════════════════════════════════
   CHARTS
   ═══════════════════════════════════════════════════════ */
.charts-section{{margin-bottom:32px}}
.charts-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(360px,1fr));
  gap:14px;
}}
.chart-card{{
  background:var(--bg-paper);border:1px solid var(--border);border-radius:12px;
  padding:20px;
  transition:box-shadow .25s ease,border-color .25s ease,background-color .3s ease;
}}
.chart-card:hover{{border-color:var(--card-hover-border);box-shadow:var(--shadow-sm)}}
.chart-card h3{{margin-bottom:14px}}
.plotly-chart{{width:100%;min-height:260px}}

/* ═══════════════════════════════════════════════════════
   OPS / OCCUPANCY PANEL
   ═══════════════════════════════════════════════════════ */
.ops-panel{{margin-top:8px}}

/* ═══════════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════════ */
.empty{{color:var(--text-disabled);font-size:.8125rem;padding:24px 0;text-align:center}}
.section-divider{{
  border:none;border-top:1px solid var(--border-subtle);
  margin:32px 0;
}}

/* Footer */
.dashboard-footer{{
  margin-top:48px;padding-top:20px;
  border-top:1px solid var(--border-subtle);
  text-align:center;font-size:.6875rem;
  color:var(--text-disabled);letter-spacing:.04em;
  transition:border-color .3s ease,color .3s ease;
}}
.dashboard-footer a{{color:var(--primary);text-decoration:none}}
.dashboard-footer a:hover{{text-decoration:underline}}

/* ═══════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════ */

/* Tablet */
@media(max-width:1024px){{
  .dashboard{{padding:20px 16px 32px}}
  .two-col{{flex-direction:column}}
  .col-narrow{{max-width:100%;width:100%;overflow-x:auto}}
  .charts-grid{{grid-template-columns:1fr}}
}}

/* Mobile */
@media(max-width:768px){{
  .dashboard{{padding:14px 12px 28px}}
  .dashboard-header{{margin-bottom:22px;padding-bottom:14px}}
  .brand-mark{{width:32px;height:32px;border-radius:8px}}
  h1{{font-size:1.15rem}}
  .header-subtitle{{font-size:.6rem}}
  .summary-bar{{grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;margin-bottom:22px}}
  .card{{padding:12px 10px 10px;border-radius:10px}}
  .card-val{{font-size:1.35rem}}
  .card-lbl{{font-size:.6rem}}
  .tab-bar{{margin-bottom:18px;padding:3px}}
  .tab-btn{{padding:6px 14px;font-size:.75rem}}
  .chart-card{{padding:14px}}
  .plotly-chart{{min-height:200px}}
  .lb-table{{font-size:.75rem}}
  .lb-table th{{padding:8px 10px;font-size:.6rem}}
  .lb-table td{{padding:7px 10px}}
  .cm-table{{font-size:.75rem}}
  .cm-table td,.cm-table th{{padding:5px 7px}}
}}

/* Small mobile */
@media(max-width:480px){{
  .dashboard{{padding:10px 8px 20px}}
  .summary-bar{{grid-template-columns:repeat(2,1fr);gap:6px}}
  .card-val{{font-size:1.15rem}}
  .charts-grid{{grid-template-columns:1fr}}
}}

/* ═══════════════════════════════════════════════════════
   ANIMATIONS
   ═══════════════════════════════════════════════════════ */
@keyframes fadeInUp{{
  from{{opacity:0;transform:translateY(10px)}}
  to{{opacity:1;transform:translateY(0)}}
}}
.anim-in{{animation:fadeInUp .35s ease both}}
</style>
</head>

<body>
<div class="dashboard">

  <!-- ─── HEADER ──────────────────────────────────── -->
  <header class="dashboard-header">
    <div class="header-left">
      <div class="brand-mark" title="Turing Hotel"></div>
      <div>
        <h1>Turing Hotel</h1>
        <div class="header-subtitle">Performance Leaderboard</div>
      </div>
    </div>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme" aria-label="Toggle theme">
      <span class="material-icons-outlined ico-dark" style="font-size:20px">dark_mode</span>
      <span class="material-icons-outlined ico-light" style="font-size:20px">light_mode</span>
    </button>
  </header>

  <!-- ─── KPI CARDS ───────────────────────────────── -->
  <section class="anim-in" style="animation-delay:.05s">
    {summary_html}
  </section>

  <!-- ─── SCOPE TABS + CONTENT ────────────────────── -->
  <section class="anim-in" style="animation-delay:.10s">
    <div class="tab-bar">{scope_tab_buttons}</div>
    {scope_blocks_html}
  </section>

  <!-- ─── ANALYTICS CHARTS ────────────────────────── -->
  <section class="charts-section anim-in" style="animation-delay:.15s">
    <h2>Analytics</h2>
    <div class="charts-grid">
      <div class="chart-card">
        <h3>Best at Fooling</h3>
        <div id="chart-trend" class="plotly-chart"></div>
      </div>
      <div class="chart-card">
        <h3>Best at Detecting</h3>
        <div id="chart-distribution" class="plotly-chart"></div>
      </div>
    </div>
  </section>

  <!-- ─── OCCUPANCY ───────────────────────────────── -->
  <section class="ops-panel anim-in" style="animation-delay:.20s">
    <h2>Hotel Occupancy</h2>
    <div class="chart-card">
      <div id="chart-ops" class="plotly-chart"></div>
    </div>
  </section>

  <!-- ─── FOOTER ──────────────────────────────────── -->
  <footer class="dashboard-footer">Turing Hotel Analytics</footer>
</div>

<script>
(function(){{

  /* ═══════════════════════════════════════════════════
     THEME ENGINE
     ═══════════════════════════════════════════════════ */
  var _theme = 'dark';

  function setTheme(m){{
    if(m!=='dark'&&m!=='light') return;
    if(m===_theme&&document.documentElement.getAttribute('data-theme')===m) return;
    _theme=m;
    document.documentElement.setAttribute('data-theme',m);
    syncPlotlyTheme();
  }}

  function toggleTheme(){{ setTheme(_theme==='dark'?'light':'dark'); }}
  window.toggleTheme=toggleTheme;

  /* Detect: URL param */
  var _p=new URLSearchParams(window.location.search);
  if(_p.has('theme')){{ setTheme(_p.get('theme')); }}

  /* Detect: prefers-color-scheme */
  try{{
    var mq=window.matchMedia('(prefers-color-scheme:light)');
    if(!_p.has('theme')) setTheme(mq.matches?'light':'dark');
    mq.addEventListener('change',function(e){{ setTheme(e.matches?'light':'dark'); }});
  }}catch(e){{}}

  /* Detect: postMessage from parent */
  window.addEventListener('message',function(ev){{
    var d=ev.data;
    if(typeof d==='string'){{ try{{ d=JSON.parse(d); }}catch(x){{ return; }} }}
    if(!d) return;
    var t=d.theme||d.value||d.mode;
    if(d.type==='theme'||d.type==='set-theme') t=t||d.payload;
    if(t) setTheme(t);
  }});

  /* Detect: parent data-theme attribute (same-origin) */
  try{{
    var ph=window.parent.document.documentElement;
    var pt=ph.getAttribute('data-theme');
    if(pt) setTheme(pt);
    new MutationObserver(function(muts){{
      for(var i=0;i<muts.length;i++){{
        if(muts[i].attributeName==='data-theme'||muts[i].attributeName==='class'){{
          var v=ph.getAttribute('data-theme');
          if(!v){{
            if(ph.classList.contains('dark')) v='dark';
            else if(ph.classList.contains('light')) v='light';
          }}
          if(v) setTheme(v);
        }}
      }}
    }}).observe(ph,{{attributes:true,attributeFilter:['data-theme','class']}});
  }}catch(e){{}}

  /* ═══════════════════════════════════════════════════
     SCOPE SWITCHING
     ═══════════════════════════════════════════════════ */
  var DEFAULT='{default_scope}';

  function switchScope(key){{
    document.querySelectorAll('.scope-panel').forEach(function(el){{
      el.classList.toggle('visible',el.dataset.scope===key);
    }});
    document.querySelectorAll('.tab-btn').forEach(function(btn){{
      btn.classList.toggle('active',btn.dataset.scope===key);
    }});
    document.querySelectorAll('.scope-card').forEach(function(el){{
      el.style.display=el.dataset.scope===key?'':'none';
    }});
  }}
  window.switchScope=switchScope;
  switchScope(DEFAULT);

  /* ═══════════════════════════════════════════════════
     TABLE SORTING
     ═══════════════════════════════════════════════════ */
  window.sortTable=function(th){{
    var tbl=th.closest('table'),tbody=tbl.querySelector('tbody');
    var rows=Array.from(tbody.querySelectorAll('tr'));
    var asc=th.dataset.asc!=='1';
    th.dataset.asc=asc?'1':'0';
    tbl.querySelectorAll('th').forEach(function(h){{
      var a=h.querySelector('.sort-arrow'); if(a) a.textContent='\u21C5';
    }});
    var arrow=th.querySelector('.sort-arrow');
    if(arrow) arrow.textContent=asc?'\u25B2':'\u25BC';
    var idx=Array.from(th.parentNode.children).indexOf(th);
    rows.sort(function(a,b){{
      var av=a.querySelectorAll('td')[idx].dataset.val;
      var bv=b.querySelectorAll('td')[idx].dataset.val;
      var an=parseFloat(av),bn=parseFloat(bv);
      if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
      return asc?av.localeCompare(bv):bv.localeCompare(av);
    }});
    rows.forEach(function(r){{ tbody.appendChild(r); }});
  }};

  /* ═══════════════════════════════════════════════════
     PLOTLY HELPERS
     ═══════════════════════════════════════════════════ */
  var COLORS=['#1A5CFF','#00D4AA','#FFB347','#FF3B30','#4D7FFF',
              '#00B391','#FF6692','#33EABD','#FFD080','#6B9BFF'];

  function plotlyLayout(overrides){{
    var dk=_theme==='dark';
    var base={{
      paper_bgcolor:'rgba(0,0,0,0)',
      plot_bgcolor:'rgba(0,0,0,0)',
      font:{{family:'Inter, sans-serif',color:dk?'#C8CDD3':'#0A1628',size:11}},
      margin:{{l:44,r:12,t:8,b:36}},
      xaxis:{{
        gridcolor:dk?'#222A36':'#DBE1EB',
        zerolinecolor:dk?'#222A36':'#C0C8D6',
        linecolor:dk?'#222A36':'#C0C8D6',
        tickfont:{{color:dk?'#677385':'#677385',size:10}}
      }},
      yaxis:{{
        gridcolor:dk?'#222A36':'#DBE1EB',
        zerolinecolor:dk?'#222A36':'#C0C8D6',
        linecolor:dk?'#222A36':'#C0C8D6',
        tickfont:{{color:dk?'#677385':'#677385',size:10}}
      }},
      legend:{{
        font:{{color:dk?'#C8CDD3':'#495464',size:10}},
        bgcolor:'rgba(0,0,0,0)',borderwidth:0
      }},
      colorway:COLORS,
      hoverlabel:{{
        bgcolor:dk?'#1F2025':'#FFFFFF',
        bordercolor:dk?'#323C4A':'#C0C8D6',
        font:{{family:'Inter, sans-serif',color:dk?'#F5F6F8':'#0A1628',size:11}}
      }}
    }};
    if(overrides){{ for(var k in overrides) base[k]=overrides[k]; }}
    return base;
  }}
  window.getPlotlyLayout=plotlyLayout;

  var PLOTLY_CFG={{responsive:true,displayModeBar:false}};

  function syncPlotlyTheme(){{
    var L=plotlyLayout();
    document.querySelectorAll('.plotly-chart').forEach(function(el){{
      if(el.data && el.data.length) Plotly.relayout(el,L);
    }});
  }}

  /* ─── Embedded server-side data ── */
  var OPS_DATA    = {ops_json};
  var TREND_DATA  = {top_foolers_json};
  var DIST_DATA   = {top_detectors_json};

  if(typeof Plotly!=='undefined'){{

    /* Hotel Occupancy time-series */
    var opsEl=document.getElementById('chart-ops');
    if(opsEl && OPS_DATA.length){{
      Plotly.newPlot(opsEl, OPS_DATA, plotlyLayout({{
        legend:{{orientation:'h',y:1.12,x:0}},
        xaxis:{{type:'date'}},
        yaxis:{{title:{{text:'Count',font:{{size:10,color:'#677385'}}}}}}
      }}), PLOTLY_CFG);
    }} else if(opsEl){{
      opsEl.innerHTML='<div class="empty">No operational data yet.</div>';
    }}

    /* Best at Fooling - vertical bar */
    var trendEl=document.getElementById('chart-trend');
    if(trendEl && TREND_DATA.length){{
      Plotly.newPlot(trendEl, TREND_DATA, plotlyLayout({{
        yaxis:{{title:{{text:'Fooling rate %',font:{{size:10,color:'#677385'}}}}}},
        showlegend:false
      }}), PLOTLY_CFG);
    }} else if(trendEl){{
      trendEl.innerHTML='<div class="empty">No vote data yet.</div>';
    }}

    /* Best at Detecting - horizontal bar */
    var distEl=document.getElementById('chart-distribution');
    if(distEl && DIST_DATA.length){{
      Plotly.newPlot(distEl, DIST_DATA, plotlyLayout({{
        margin:{{l:90,r:40,t:8,b:36}},
        xaxis:{{title:{{text:'F1 %',font:{{size:10,color:'#677385'}}}}}},
        yaxis:{{tickfont:{{family:'Inter',size:11}}}},
        showlegend:false
      }}), PLOTLY_CFG);
    }} else if(distEl){{
      distEl.innerHTML='<div class="empty">No vote data yet.</div>';
    }}

  }} else {{
    document.querySelectorAll('.plotly-chart').forEach(function(el){{
      el.innerHTML='<div class="empty">Charts unavailable - Plotly.js did not load</div>';
    }});
  }}

}})();
</script>
</body>
</html>"""
