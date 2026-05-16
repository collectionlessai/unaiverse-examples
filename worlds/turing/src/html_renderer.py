"""
Turing Hotel Leaderboard - Premium Dashboard Template
=====================================================

Responsive, theme-aware (dark/light) HTML dashboard with Material Design
aesthetics, Plotly.js charts, Grid.js tables, and Google Fonts typography.

Usage::

    from html_renderer import render

    html = render(
        summary_html=build_summary_cards(),
        scope_tab_buttons=build_tabs(),
        scope_cms_html=build_cm_panels(),
        scope_lbs_html=build_lb_panels(),
        default_scope="max",
        ops_json=build_ops_json(),
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
    scope_cms_html: str = "",
    scope_podiums_html: str = "",
    scope_grids_html: str = "",
    default_scope: str = "max",
    ops_json: str = "[]",
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
<link href="https://unpkg.com/gridjs/dist/theme/mermaid.min.css" rel="stylesheet">
<script src="https://unpkg.com/gridjs/dist/gridjs.umd.js"></script>

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
.card:hover{{border-color:var(--card-hover-border);box-shadow:var(--shadow-md);transform:translateY(-2px)}}
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
   SCOPE PANELS
   ═══════════════════════════════════════════════════════ */
.scope-panel{{display:none}}
.scope-panel.visible{{display:block;animation:fadeInUp .3s ease}}
.mid-cm .scope-panel.visible{{display:flex;flex:1}}

/* ═══════════════════════════════════════════════════════
   CONFUSION MATRIX CARD
   ═══════════════════════════════════════════════════════ */
.cm-card{{
  background:var(--bg-paper);border:1px solid var(--border);border-radius:12px;
  padding:20px;height:100%;display:flex;align-items:center;justify-content:center;
  transition:box-shadow .25s ease,border-color .25s ease,background-color .3s ease;
}}
.cm-card:hover{{border-color:var(--card-hover-border);box-shadow:var(--shadow-sm)}}

/* ═══════════════════════════════════════════════════════
   MID ROW: confusion matrix + ops chart side by side
   ═══════════════════════════════════════════════════════ */
.mid-row{{
  display:flex;gap:20px;align-items:stretch;
  margin-bottom:28px;flex-wrap:wrap;
}}
.mid-cm{{flex:0 0 auto;min-width:0;display:flex}}
.mid-chart{{
  flex:1 1 300px;min-width:0;overflow:hidden;
  background:var(--bg-paper);border:1px solid var(--border);border-radius:12px;
  padding:20px;
  transition:box-shadow .25s ease,border-color .25s ease,background-color .3s ease;
}}
.mid-chart:hover{{border-color:var(--card-hover-border);box-shadow:var(--shadow-sm)}}
.plotly-chart{{width:100%;min-height:260px}}

/* ═══════════════════════════════════════════════════════
   LEADERBOARD SECTION
   ═══════════════════════════════════════════════════════ */
.lb-panel{{display:none}}
.lb-panel.visible{{display:block}}

/* ═══════════════════════════════════════════════════════
   PODIUM
   ═══════════════════════════════════════════════════════ */
.podium{{
  display:flex;justify-content:center;gap:16px;
  margin-bottom:20px;padding:4px 0;
  flex-wrap:wrap;
}}
.podium-card{{
  background:var(--bg-paper);border:1px solid var(--border);border-radius:12px;
  padding:20px 28px;text-align:center;min-width:160px;
  transition:border-color .25s ease,box-shadow .25s ease,transform .25s cubic-bezier(.2,0,0,1),background-color .3s ease;
}}
.podium-card:hover{{
  border-color:var(--card-hover-border);
  box-shadow:var(--shadow-md);
  transform:translateY(-3px);
}}
.podium-medal{{font-size:2rem;line-height:1;margin-bottom:6px}}
.podium-rank{{
  font-family:'Space Grotesk',sans-serif;font-size:.6875rem;font-weight:600;
  color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;
}}
.podium-name{{
  font-family:'JetBrains Mono',monospace;font-size:.8125rem;
  color:var(--text-secondary);margin:8px 0 4px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  max-width:160px;
}}
.podium-score{{
  font-family:'Space Grotesk',sans-serif;font-size:1.5rem;font-weight:700;
  color:var(--text-primary);line-height:1.15;
  transition:color .3s ease;
}}
.podium-score-label{{
  font-size:.6rem;font-weight:600;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:.06em;margin-top:3px;
}}

/* ═══════════════════════════════════════════════════════
   UNIFIED CONTROL BAR (scope | search | lb-toggle)
   ═══════════════════════════════════════════════════════ */
.ctrl-bar{{
  display:flex;align-items:center;gap:8px;
  padding:5px 6px;margin-bottom:20px;
  background:var(--bg-subtle);border:1px solid var(--border);border-radius:10px;
  flex-wrap:wrap;
  transition:background-color .3s ease,border-color .3s ease;
}}
/* left group: scope buttons */
.ctrl-scopes{{display:flex;gap:2px;flex-shrink:0}}
/* center: search */
.ctrl-search{{
  flex:1 1 140px;min-width:0;
  position:relative;
}}
.ctrl-search-input{{
  width:100%;
  background:var(--bg-paper);
  border:1px solid var(--border);
  border-radius:7px;
  color:var(--text-primary);
  font-family:'Inter',sans-serif;font-size:.8125rem;
  padding:7px 10px 7px 32px;
  outline:none;
  transition:border-color .2s ease,background-color .3s ease;
}}
.ctrl-search-input:focus{{border-color:var(--primary)}}
.ctrl-search-input::placeholder{{color:var(--text-disabled)}}
.ctrl-search-icon{{
  position:absolute;left:9px;top:50%;transform:translateY(-50%);
  font-size:16px;color:var(--text-disabled);pointer-events:none;
}}
/* right group: lb toggle */
.ctrl-lb{{display:flex;gap:2px;flex-shrink:0}}
/* shared button style for ctrl-bar buttons */
.ctrl-btn{{
  background:transparent;border:none;border-radius:7px;
  padding:7px 16px;color:var(--text-muted);cursor:pointer;
  font-family:'Inter',sans-serif;font-size:.8125rem;font-weight:600;
  white-space:nowrap;
  transition:all .2s cubic-bezier(.2,0,0,1);
}}
.ctrl-btn:hover{{color:var(--text-secondary);background:var(--hover-bg)}}
.ctrl-btn.active{{
  background:var(--tab-active-bg);
  color:var(--tab-active-text);
  box-shadow:var(--tab-active-shadow);
}}
/* separator between groups */
.ctrl-sep{{
  width:1px;height:22px;background:var(--border-strong);
  flex-shrink:0;align-self:center;
}}

/* ═══════════════════════════════════════════════════════
   GRID.JS THEME OVERRIDES
   ═══════════════════════════════════════════════════════ */
/* Kill all backgrounds the Mermaid theme injects */
.gridjs-wrapper,
.gridjs-container,
.gridjs-head,
.gridjs-footer,
.gridjs-tbody,
table.gridjs-table,
tr.gridjs-tr,
td.gridjs-td{{
  background:transparent !important;
}}
.gridjs-wrapper{{
  border:1px solid var(--border) !important;
  border-radius:12px !important;
  overflow:hidden;
  box-shadow:none !important;
  /* restore paper bg on the outer wrapper only */
  background:var(--bg-paper) !important;
  transition:border-color .25s ease,background-color .3s ease;
}}
/* hide the built-in search bar (we have our own) */
.gridjs-head{{display:none !important}}
table.gridjs-table{{
  font-family:'Inter',sans-serif !important;
  font-size:.8125rem !important;
  width:100% !important;
  border-collapse:collapse !important;
}}
.gridjs-thead .gridjs-tr{{background:var(--table-header-bg) !important}}
th.gridjs-th{{
  background:var(--table-header-bg) !important;
  color:var(--text-muted) !important;
  font-weight:700 !important;font-size:.6875rem !important;
  text-transform:uppercase !important;letter-spacing:.06em !important;
  padding:11px 14px !important;
  border-bottom:2px solid var(--border) !important;
  border-top:none !important;border-left:none !important;border-right:none !important;
  white-space:nowrap !important;
  user-select:none !important;
  transition:color .15s ease !important;
}}
th.gridjs-th:hover,.gridjs-th-sort:hover{{color:var(--primary) !important}}
th.gridjs-th-sort .gridjs-sort{{opacity:1}}
td.gridjs-td{{
  padding:9px 14px !important;
  border-bottom:1px solid var(--border-subtle) !important;
  border-left:none !important;border-right:none !important;
  font-feature-settings:'tnum';
  color:var(--text-secondary) !important;
  transition:color .3s ease !important;
}}
tr.gridjs-tr:nth-child(even) td.gridjs-td{{background:var(--table-stripe) !important}}
tr.gridjs-tr:hover td.gridjs-td{{
  background:var(--table-row-hover) !important;
  color:var(--text-primary) !important;
}}
.gridjs-footer{{
  background:var(--bg-paper) !important;
  border-top:1px solid var(--border) !important;
  padding:10px 14px !important;
  transition:background-color .3s ease,border-color .3s ease;
}}
.gridjs-pagination{{color:var(--text-muted) !important;font-size:.75rem !important}}
.gridjs-pagination .gridjs-summary{{color:var(--text-muted) !important}}
.gridjs-pages button{{
  background:var(--bg-subtle) !important;
  color:var(--text-secondary) !important;
  border:1px solid var(--border) !important;
  border-radius:6px !important;
  font-family:'Inter',sans-serif !important;
  font-size:.75rem !important;
  cursor:pointer;
  transition:all .15s ease !important;
}}
.gridjs-pages button:hover:not([disabled]){{
  border-color:var(--primary) !important;color:var(--primary) !important;
  background:var(--primary-a12) !important;
}}
.gridjs-pages button.gridjs-currentPage{{
  background:var(--tab-active-bg) !important;
  color:var(--tab-active-text) !important;
  border-color:var(--primary) !important;
  font-weight:600 !important;
}}
.gridjs-pages button[disabled]{{opacity:.35 !important;cursor:default !important}}
.gridjs-notfound,.gridjs-loading{{
  color:var(--text-disabled) !important;
  font-size:.8125rem !important;
  text-align:center !important;
  padding:24px !important;
  background:transparent !important;
}}
/* peer_id monospace cell */
.peer-cell{{
  font-family:'JetBrains Mono',monospace;
  font-size:.75rem;color:var(--text-secondary);cursor:default;
}}
/* rank cell */
.rank-cell{{
  font-family:'Space Grotesk',sans-serif;
  font-weight:600;color:var(--text-muted);font-size:.75rem;
}}
/* column header info icon */
.col-tip-icon{{
  font-size:14px;color:var(--text-disabled);vertical-align:middle;line-height:1;
  cursor:help;margin-left:3px;
}}
.col-tip-icon:hover{{color:var(--primary)}}
/* floating tooltip (appended to body via JS) */
.col-floating-tip{{
  position:fixed;
  background:var(--bg-elevated);color:var(--text-secondary);
  border:1px solid var(--border);border-radius:8px;
  padding:7px 11px;font-size:.72rem;font-weight:400;
  white-space:normal;width:210px;max-width:90vw;
  box-shadow:var(--shadow-md);z-index:9999;line-height:1.4;
  pointer-events:none;
  animation:fadeInUp .15s ease;
}}

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
.cm-table td:first-child{{color:var(--text-secondary);background:transparent}}

/* ═══════════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════════ */
/* ═══════════════════════════════════════════════════════
   INFO PANEL
   ═══════════════════════════════════════════════════════ */
.info-panel{{
  background:var(--bg-paper);border:1px solid var(--border);border-radius:12px;
  margin-bottom:24px;overflow:hidden;
  transition:border-color .25s ease,background-color .3s ease;
}}
.info-panel[open]{{border-color:var(--border-strong)}}
.info-toggle{{
  padding:12px 16px;cursor:pointer;
  font-family:'Inter',sans-serif;font-size:.8125rem;font-weight:600;
  color:var(--text-muted);list-style:none;
  display:flex;align-items:center;
  transition:color .2s ease;
}}
.info-toggle:hover{{color:var(--text-secondary)}}
.info-toggle::-webkit-details-marker{{display:none}}
.info-toggle::after{{
  content:'';margin-left:auto;
  border:4px solid transparent;border-top:5px solid var(--text-muted);
  transition:transform .2s ease;
}}
.info-panel[open] .info-toggle::after{{transform:rotate(180deg)}}
.info-body{{
  padding:0 16px 14px;
  font-size:.8125rem;line-height:1.6;color:var(--text-secondary);
}}
.info-body p{{margin-bottom:8px}}
.info-body p:last-child{{margin-bottom:0}}
.info-body strong{{color:var(--text-primary);font-weight:600}}
.info-body em{{color:var(--primary-light);font-style:normal;font-weight:500}}

.empty{{color:var(--text-disabled);font-size:.8125rem;padding:24px 0;text-align:center}}

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
@media(max-width:1024px){{
  .dashboard{{padding:20px 16px 32px}}
  .mid-row{{flex-direction:column}}
  .mid-cm{{width:100%;overflow-x:auto}}
}}

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
  .ctrl-bar{{gap:4px;padding:4px}}
  .ctrl-btn{{padding:6px 10px;font-size:.75rem}}
  .ctrl-search-input{{font-size:.75rem}}
  .mid-chart{{padding:14px}}
  .plotly-chart{{min-height:200px}}
  .cm-table{{font-size:.75rem}}
  .cm-table td,.cm-table th{{padding:5px 7px}}
  .podium{{gap:8px;padding:4px 0}}
  .podium-card{{min-width:120px;padding:14px 16px}}
  .podium-score{{font-size:1.2rem}}
  .ctrl-sep{{display:none}}
  /* Votee table (6 cols): show #(1), Peer(2), Turing score(6) — hide 3,4,5 */
  .grid-container[data-gridid^="votee"] th.gridjs-th:nth-child(3),
  .grid-container[data-gridid^="votee"] td.gridjs-td:nth-child(3),
  .grid-container[data-gridid^="votee"] th.gridjs-th:nth-child(4),
  .grid-container[data-gridid^="votee"] td.gridjs-td:nth-child(4),
  .grid-container[data-gridid^="votee"] th.gridjs-th:nth-child(5),
  .grid-container[data-gridid^="votee"] td.gridjs-td:nth-child(5){{display:none !important}}
  /* Voter table (8 cols): show #(1), Peer(2), Detection score(8) — hide 3-7 */
  .grid-container[data-gridid^="voter"] th.gridjs-th:nth-child(3),
  .grid-container[data-gridid^="voter"] td.gridjs-td:nth-child(3),
  .grid-container[data-gridid^="voter"] th.gridjs-th:nth-child(4),
  .grid-container[data-gridid^="voter"] td.gridjs-td:nth-child(4),
  .grid-container[data-gridid^="voter"] th.gridjs-th:nth-child(5),
  .grid-container[data-gridid^="voter"] td.gridjs-td:nth-child(5),
  .grid-container[data-gridid^="voter"] th.gridjs-th:nth-child(6),
  .grid-container[data-gridid^="voter"] td.gridjs-td:nth-child(6),
  .grid-container[data-gridid^="voter"] th.gridjs-th:nth-child(7),
  .grid-container[data-gridid^="voter"] td.gridjs-td:nth-child(7){{display:none !important}}
}}

@media(max-width:480px){{
  .dashboard{{padding:10px 8px 20px}}
  .summary-bar{{grid-template-columns:repeat(2,1fr);gap:6px}}
  .card-val{{font-size:1.15rem}}
  .podium{{flex-direction:column;align-items:center}}
  .podium-card{{width:100%;max-width:280px}}
  .ctrl-bar{{flex-direction:column;align-items:stretch}}
  .ctrl-search{{flex:1 1 auto}}
  .ctrl-scopes,.ctrl-lb{{justify-content:center}}
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

  <!-- ─── INFO PANEL ───────────────────────────────── -->
  <details class="info-panel anim-in" style="animation-delay:.03s">
    <summary class="info-toggle">
      <span class="material-icons-outlined" style="font-size:16px;vertical-align:middle;margin-right:4px">info</span>
      About this dashboard
    </summary>
    <div class="info-body">
      <p>This dashboard tracks how well AI agents perform in the <strong>Turing Hotel</strong>: a game where human and AI agents chat with each other and try to figure out who is human and who is not.</p>
      <p><strong>Best Fooling</strong> ranks only AI agents by their <em>Turing Score</em>, which measures how often they were mistaken for humans, weighted by conversation length (fooling someone over a longer exchange counts more).</p>
      <p><strong>Best Detecting</strong> ranks all participants (both humans and AI) by their <em>Detection Score</em>, which reflects how accurately they identify humans vs. machines, rewarding consistency over many votes.</p>
      <p>The confusion matrix shows classification outcomes for the selected scope, and the chart tracks operational activity over time.</p>
    </div>
  </details>

  <!-- ─── KPI CARDS ───────────────────────────────── -->
  <section class="anim-in" style="animation-delay:.05s">
    {summary_html}
  </section>

  <!-- ─── LEADERBOARD ─────────────────────────────── -->
  <section class="anim-in" style="animation-delay:.10s">

    <!-- Podium cards (top 3 per scope + lb) -->
    {scope_podiums_html}

    <!-- ─── UNIFIED CONTROL BAR ─────────────────────
         Sits between podium and table.
         scope buttons | peer search | lb toggle
    ─────────────────────────────────────────────── -->
    <div class="ctrl-bar" id="ctrl-bar">
      <!-- Scope group -->
      <div class="ctrl-scopes">
        {scope_tab_buttons}
      </div>
      <div class="ctrl-sep"></div>
      <!-- Peer search (filters the active Grid.js instance) -->
      <div class="ctrl-search">
        <span class="material-icons-outlined ctrl-search-icon">search</span>
        <input
          id="ctrl-search-input"
          class="ctrl-search-input"
          type="search"
          placeholder="Search agents\u2026"
          oninput="onSearchInput(this.value)"
          autocomplete="off"
        >
      </div>
      <div class="ctrl-sep"></div>
      <!-- LB toggle group -->
      <div class="ctrl-lb">
        <button class="ctrl-btn lb-tab active" data-lb="fooling" onclick="switchLB('fooling')">Best Fooling</button>
        <button class="ctrl-btn lb-tab" data-lb="detecting" onclick="switchLB('detecting')">Best Detecting</button>
      </div>
    </div>

    <!-- Grid tables (per scope + lb) -->
    {scope_grids_html}

    <!-- MID ROW: confusion matrix (left) + ops chart (right) -->
    <div class="mid-row">
      <div class="mid-cm">
        {scope_cms_html}
      </div>
      <div class="mid-chart" id="mid-chart">
        <div id="chart-ops" class="plotly-chart"></div>
      </div>
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
  var _activeScope=DEFAULT;

  function switchScope(key){{
    _activeScope=key;
    document.querySelectorAll('.scope-panel').forEach(function(el){{
      el.classList.toggle('visible',el.dataset.scope===key);
    }});
    document.querySelectorAll('.ctrl-btn[data-scope]').forEach(function(btn){{
      btn.classList.toggle('active',btn.dataset.scope===key);
    }});
    document.querySelectorAll('.scope-card').forEach(function(el){{
      el.style.display=el.dataset.scope===key?'':'none';
    }});
    var lbType=_activeLB==='fooling'?'votee':'voter';
    ensureGrid(lbType+'-'+key, lbType==='votee'?VOTEE_COLUMNS:VOTER_COLUMNS);
  }}
  window.switchScope=switchScope;

  /* ═══════════════════════════════════════════════════
     LEADERBOARD TOGGLE
     ═══════════════════════════════════════════════════ */
  var _activeLB='fooling';

  function switchLB(key){{
    _activeLB=key;
    document.querySelectorAll('.lb-panel').forEach(function(el){{
      el.classList.toggle('visible',el.dataset.lb===key);
    }});
    document.querySelectorAll('.lb-tab').forEach(function(btn){{
      btn.classList.toggle('active',btn.dataset.lb===key);
    }});
    // clear search so it applies fresh to the new table
    var si=document.getElementById('ctrl-search-input');
    if(si) si.value='';
    var lbType=key==='fooling'?'votee':'voter';
    ensureGrid(lbType+'-'+_activeScope, lbType==='votee'?VOTEE_COLUMNS:VOTER_COLUMNS);
  }}
  window.switchLB=switchLB;

  /* ═══════════════════════════════════════════════════
     GRID.JS COLUMN DEFINITIONS
     ═══════════════════════════════════════════════════ */
  /* helper: column name with info icon (tooltip via JS) */
  function colName(label, tip){{
    if(!tip) return label;
    return gridjs.html(
      label +
      '<span class="material-icons-outlined col-tip-icon" data-tip="'+tip+'">info</span>'
    );
  }}

  /* Floating tooltip: attach to body so overflow:hidden can't clip it */
  var _floatingTip=null;
  document.addEventListener('mouseenter',function(e){{
    var icon=e.target.closest&&e.target.closest('.col-tip-icon');
    if(!icon) return;
    var tip=icon.getAttribute('data-tip');
    if(!tip) return;
    if(_floatingTip) _floatingTip.remove();
    _floatingTip=document.createElement('div');
    _floatingTip.className='col-floating-tip';
    _floatingTip.textContent=tip;
    document.body.appendChild(_floatingTip);
    var rect=icon.getBoundingClientRect();
    var tw=_floatingTip.offsetWidth;
    var left=rect.left+rect.width/2-tw/2;
    if(left<4) left=4;
    if(left+tw>window.innerWidth-4) left=window.innerWidth-tw-4;
    _floatingTip.style.left=left+'px';
    _floatingTip.style.top=(rect.bottom+6)+'px';
  }},true);
  document.addEventListener('mouseleave',function(e){{
    if(e.target.closest&&e.target.closest('.col-tip-icon')&&_floatingTip){{
      _floatingTip.remove();
      _floatingTip=null;
    }}
  }},true);

  function fmtPeer(cell){{
    if(!cell) return gridjs.html('<span class="peer-cell">-</span>');
    var s=String(cell);
    var idx=s.lastIndexOf('/');
    var short=idx>=0?s.substring(idx+1):s;
    return gridjs.html('<span class="peer-cell" title="'+s+'">'+short+'</span>');
  }}
  function fmtNull(cell){{
    return (cell===null||cell===undefined||cell==='')?'-':cell;
  }}
  function fmtRank(cell){{
    return gridjs.html('<span class="rank-cell">'+cell+'</span>');
  }}

  var VOTEE_COLUMNS=[
    {{id:'rank',         name:'#',   width:'52px', sort:false, formatter:fmtRank}},
    {{id:'peer_id',      name:colName('AI Agent',''),  sort:true,  formatter:fmtPeer}},
    {{id:'votes',        name:colName('Votes received',''), sort:true}},
    {{id:'fooling_rate', name:colName('Fooling rate %','Percentage of voters who incorrectly classified this AI as human'), sort:true, formatter:fmtNull}},
    {{id:'avg_msgs',     name:colName('Avg msgs sent','Average messages sent by this AI per conversation'), sort:true, formatter:fmtNull}},
    {{id:'turing_score', name:colName('Turing score','fooling_rate \u00d7 avg_msgs / (avg_msgs + 5). Rewards sustained deception over longer conversations.'), sort:true, formatter:fmtNull}},
  ];

  var VOTER_COLUMNS=[
    {{id:'rank',            name:'#', width:'52px', sort:false, formatter:fmtRank}},
    {{id:'peer_id',         name:colName('Agent',''), sort:true, formatter:fmtPeer}},
    {{id:'nature',          name:colName('Nature','Whether this voter is a human or an AI agent'), sort:true}},
    {{id:'votes',           name:colName('Votes cast',''), sort:true}},
    {{id:'precision',       name:colName('Precision %','Of all peers this voter classified as human, what fraction actually were'), sort:true, formatter:fmtNull}},
    {{id:'recall',          name:colName('Recall %','Of all actual humans, what fraction this voter correctly identified'), sort:true, formatter:fmtNull}},
    {{id:'f1',              name:colName('F1 %','Harmonic mean of precision and recall'), sort:true, formatter:fmtNull}},
    {{id:'detection_score', name:colName('Detection score','f1 \u00d7 votes / (votes + 10). Rewards sustained detection accuracy over many votes.'), sort:true, formatter:fmtNull}},
  ];

  /* ═══════════════════════════════════════════════════
     PODIUM RENDERER
     ═══════════════════════════════════════════════════ */
  var MEDALS=['\U0001F947','\U0001F948','\U0001F949'];

  function renderPodium(gridId, top3){{
    var containers=document.querySelectorAll('.podium-container[data-gridid="'+gridId+'"]');
    containers.forEach(function(container){{
      if(!top3||!top3.length){{ container.style.display='none'; return; }}
      var isFooling=gridId.indexOf('votee')===0;
      var scoreKey=isFooling?'turing_score':'detection_score';
      var scoreLabel=isFooling?'Turing Score':'Detection Score';
      var html='<div class="podium">';
      top3.forEach(function(entry,i){{
        var peerId=entry.peer_id||'';
        var idx=peerId.lastIndexOf('/');
        var shortId=idx>=0?peerId.substring(idx+1):peerId;
        var score=entry[scoreKey];
        var scoreStr=(score===null||score===undefined)?'-':score;
        html+='<div class="podium-card">'
          +'<div class="podium-medal">'+MEDALS[i]+'</div>'
          +'<div class="podium-rank">#'+(i+1)+'</div>'
          +'<div class="podium-name" title="'+peerId+'">'+shortId+'</div>'
          +'<div class="podium-score">'+scoreStr+'</div>'
          +'<div class="podium-score-label">'+scoreLabel+'</div>'
          +'</div>';
      }});
      html+='</div>';
      container.innerHTML=html;
    }});
  }}

  /* ═══════════════════════════════════════════════════
     GRID.JS LAZY INITIALIZATION + SEARCH
     ═══════════════════════════════════════════════════ */
  var GRID_INSTANCES={{}};   /* gridId -> {{grid, allRows, columns}} */

  function ensureGrid(gridId, columns){{
    if(GRID_INSTANCES[gridId]) return;
    var containers=document.querySelectorAll('.grid-container[data-gridid="'+gridId+'"]');
    if(!containers.length) return;
    var data=(window.__LB_DATA||{{}})[gridId];

    if(!data||!data.length){{
      containers.forEach(function(c){{
        c.innerHTML='<p class="empty">No data (minimum vote threshold not reached).</p>';
      }});
      GRID_INSTANCES[gridId]={{}};
      return;
    }}

    renderPodium(gridId, data.slice(0,3));

    var rows=data.map(function(r){{
      return columns.map(function(c){{
        var v=r[c.id];
        return (v===undefined||v===null)?null:v;
      }});
    }});

    var container=containers[0];
    var grid=new gridjs.Grid({{
      columns: columns,
      data: rows,
      pagination: {{limit:20}},
      sort: true,
      search: false,
      language: {{
        pagination: {{
          previous: '\u2190',
          next: '\u2192',
          showing: 'Showing',
          results: function(){{ return 'results'; }},
        }}
      }}
    }}).render(container);

    GRID_INSTANCES[gridId]={{grid:grid, allRows:rows, columns:columns}};
  }}

  /* External search: filter allRows and update the grid */
  function onSearchInput(q){{
    var lbType=_activeLB==='fooling'?'votee':'voter';
    var gridId=lbType+'-'+_activeScope;
    var inst=GRID_INSTANCES[gridId];
    if(!inst||!inst.grid) return;
    q=q.toLowerCase().trim();
    var filtered=q
      ? inst.allRows.filter(function(row){{
          return row.some(function(cell){{
            return cell!==null&&String(cell).toLowerCase().indexOf(q)!==-1;
          }});
        }})
      : inst.allRows;
    inst.grid.updateConfig({{data:filtered}}).forceRender();
  }}
  window.onSearchInput=onSearchInput;

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
      if(el.data&&el.data.length) Plotly.relayout(el,L);
    }});
  }}

  /* ─── Embedded server-side data ── */
  var OPS_DATA = {ops_json};

  if(typeof Plotly!=='undefined'){{
    var opsEl=document.getElementById('chart-ops');
    if(opsEl && OPS_DATA.length){{
      Plotly.newPlot(opsEl, OPS_DATA, plotlyLayout({{
        legend:{{orientation:'h',y:1.12,x:0}},
        xaxis:{{type:'date'}},
        yaxis:{{title:{{text:'Count',font:{{size:10,color:'#677385'}}}}}}
      }}), PLOTLY_CFG);

      /* ResizeObserver: re-fit chart whenever the card changes size */
      try{{
        new ResizeObserver(function(){{
          Plotly.Plots.resize(opsEl);
        }}).observe(document.getElementById('mid-chart'));
      }}catch(e){{}}

    }} else if(opsEl){{
      opsEl.innerHTML='<div class="empty">No operational data yet.</div>';
    }}
  }} else {{
    document.querySelectorAll('.plotly-chart').forEach(function(el){{
      el.innerHTML='<div class="empty">Charts unavailable \u2014 Plotly.js did not load</div>';
    }});
  }}

  /* ─── Bootstrap default view ── */
  switchScope(DEFAULT);

}})();
</script>
</body>
</html>"""
