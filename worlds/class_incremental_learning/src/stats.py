import json
from typing import Dict
from unaiverse.stats import Stats, UIPlot, THEME


class WorldSidebarDash:
    """
    Refined Layout:
    - Left (20%): Graph (Top), Table 1 (Mid), Table 2 (Bot)
    - Mid (60%): Exam Error (Top), Full Test Error (Bot)
    - Right (20%): Legend (Top Overlay), State Dist (Top), Action Dist (Bot)
    """
    def __init__(self, title="World Dashboard"):
        self.traces = []
        self.layout = {
            "title": title,
            "height": 900,
            "template": "plotly_dark",
            "paper_bgcolor": THEME['bg_paper'],
            "grid": {"rows": 3, "columns": 3, "pattern": "independent"},
            
            # --- COLUMN 1: LEFT (Sidebar 20%) ---
            # Top: Graph (Network Topology)
            "xaxis1":  {"domain": [0, 0.18], "visible": False}, "yaxis1": {"domain": [0.60, 1], "visible": False},
            
            # --- COLUMN 2: CENTER (Main 60%) ---
            # Top: Exam Error
            "xaxis2": {"domain": [0.23, 0.78]}, "yaxis2": {"domain": [0.55, 1]},
            # Bot: Full Test Error
            "xaxis4": {"domain": [0.23, 0.78]}, "yaxis4": {"domain": [0, 0.45]},

            # --- COLUMN 3: RIGHT (Utils 20%) ---
            # Top: State Distribution
            # We leave space at the very top (y > 0.9) for the legend
            "xaxis5": {"domain": [0.82, 1]}, "yaxis5": {"domain": [0.55, 0.90]},
            # Bot: Action Distribution
            "xaxis6": {"domain": [0.82, 1]}, "yaxis6": {"domain": [0, 0.45]},
        }
        self._map = {
            "left_top": ("xaxis1", "yaxis1"), "left_mid": ("domain_left_mid"), "left_bot": ("domain_left_bot"),
            "center_top": ("xaxis2", "yaxis2"), "center_bot": ("xaxis4", "yaxis4"),
            "right_top": ("xaxis5", "yaxis5"), "right_bot": ("xaxis6", "yaxis6")
        }

    def add_panel(self, ui_plot: UIPlot, position: str):
        if position not in self._map:
            return
        
        # Handle Tables specifically as they rely on 'domain' not 'xaxis/yaxis'
        if position == "left_mid":
            x_dom, y_dom = [0, 0.20], [0.35, 0.55] # Explicit coords for Table 1
            axis_key = None
        elif position == "left_bot":
            x_dom, y_dom = [0, 0.20], [0.0, 0.30]  # Explicit coords for Table 2
            axis_key = None
        else:
            # Standard Cartesian Plots
            xa, ya = self._map[position]
            x_dom = self.layout[xa]["domain"]
            y_dom = self.layout[ya]["domain"]
            axis_key = (xa, ya)

        # Merge Traces
        for t in ui_plot._data:
            nt = t.copy()
            if nt.get("type") == "table":
                # Tables use 'domain' for positioning, not axis references
                nt["domain"] = {"x": x_dom, "y": y_dom}
            else:
                # Cartesian plots use axis references
                nt["xaxis"] = xa.replace("xaxis", "x")
                nt["yaxis"] = ya.replace("yaxis", "y")
            
            self.traces.append(nt)

        # Merge Layout (Titles, Ranges) - Skip if it's just a table container
        if axis_key:
            xa, ya = axis_key
            src_l = ui_plot._layout
            dest_x = self.layout.setdefault(xa, {})
            dest_y = self.layout.setdefault(ya, {})
            
            if "xaxis" in src_l: dest_x.update({k:v for k,v in src_l["xaxis"].items() if k != "domain"})
            if "yaxis" in src_l: dest_y.update({k:v for k,v in src_l["yaxis"].items() if k != "domain"})

            # Add Title via Annotation
            if src_l.get("title"):
                if "annotations" not in self.layout:
                    self.layout["annotations"] = []
                self.layout["annotations"].append({
                    "text": src_l["title"],
                    "x": (x_dom[0] + x_dom[1]) / 2, 
                    "y": y_dom[1] + 0.02,
                    "xref": "paper", "yref": "paper", 
                    "showarrow": False, "xanchor": "center",
                    "font": {"size": 14, "color": THEME['text_main']}
                })
        
        # Merge Legend settings if present in the source plot
        if "legend" in ui_plot._layout:
             self.layout["legend"] = ui_plot._layout["legend"]

    def to_json(self):
        return json.dumps({"data": self.traces, "layout": self.layout})


class WStats(Stats):
    """
    This is our custom Stats class for the MNIST world.
    """
    
    # 1. Define custom stats schemas

    per_class_accuracy_schema = {f"peer_acc_per_class_{cls}": (float, -1.0) for cls in range(10)}
    # We want the teacher to track the best student (outer)
    CUSTOM_OUTER_STATS_DYNAMIC_SCHEMA = {
        'accuracy': (float, -1.0),
        **per_class_accuracy_schema
    }
    
    # Finally, we want the world to track the best exam error across all agents
    CUSTOM_WORLD_STATS_STATIC_SCHEMA = {
        'overall_best_student': (str, None),  # set by the world
    }

    # 2. The __init__ will be called automatically by the framework.
    #    The base __init__ will automatically merge your custom schemas.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can add custom initialization here if needed
        self._deb("Custom MNIST Stats Class Initialized!")
    
    def _deb(self, msg: str):
        """Prints a debug message if enabled."""
        if self.DEBUG:
            prefix = "[DEBUG " + ("WORLD" if self.is_world else "AGENT") + "]"
            self._out(f"{prefix} [WStats] {msg}")

    def _err(self, msg: str):
        """Prints an error message."""
        self._out("<ERROR> [WStats] " + msg)
    
    def _load_static_from_db(self):
        if not self._db_conn:
            return
        try:
            cursor = self._db_conn.execute("SELECT peer_id, stat_name, val_json, timestamp FROM static_stats")
            for group_key, stat_name, value_json, timestamp in cursor:
                # the only stats we want to load are the best overall
                if stat_name in self.CUSTOM_WORLD_STATS_STATIC_SCHEMA:  # stat_name are the keys of schema dicts
                    value = json.loads(value_json)
                    self._store_static(stat_name, value, group_key, timestamp)
            
            # Clear the buffer generated by loading
            self._static_db_buffer = []
            self._deb("Loaded static stats snapshot from DB.")
        except Exception as e:
            self._err(f"Failed to load static stats from DB: {e}")
    
    def plot(self, since_timestamp: int = 0) -> str | None:
        """
        Implementation of the specific Dashboard.
        Uses the `Stats` toolbox methods to populate `WorldSidebarDash`.
        """
        # 1. Get Data view
        view = self.get_view(since_timestamp) if self.is_world else self._world_view
        if not view:
            return None
        
        # 2. Initialize Layout
        dash = WorldSidebarDash("MNIST Monitor")

        # --- LEFT COLUMN ---
        p1 = UIPlot(title="Graph")
        self._populate_graph(p1, view, "graph")
        dash.add_panel(p1, "left_top")

        p_tbl1 = UIPlot(title="World Summary")
        self._populate_world_counters_table(p_tbl1, view)
        dash.add_panel(p_tbl1, "left_mid")

        p_tbl2 = UIPlot(title="Best Student")
        self._populate_best_student_table(p_tbl2, view)
        dash.add_panel(p_tbl2, "left_bot")

        # --- CENTER COLUMN ---
        p4 = UIPlot(title="Exam Error")
        self._populate_time_series(p4, view, "exam_err")
        p4.set_layout_opt("xaxis", {"showticklabels": False})
        p4.set_layout_opt('yaxis', {"title": None})
        p4.set_legend(orientation='h', x=0.82, y=1.0, xanchor='left', yanchor='bottom')
        dash.add_panel(p4, "center_top")

        p5 = UIPlot(title="Full Test Error")
        self._populate_time_series(p5, view, "full_test_err", show_legend=False)
        p5.set_layout_opt("xaxis", {"showticklabels": False})
        p5.set_layout_opt('yaxis', {"title": None})
        dash.add_panel(p5, "center_bot")

        # --- RIGHT COLUMN (Custom Summary Table) ---
        p2 = UIPlot()
        self._populate_distribution(p2, view, "state")
        p2.set_layout_opt("xaxis", {"title": None})
        p2.set_layout_opt("yaxis", {"title": "#Peers per State"})
        dash.add_panel(p2, "right_top")

        p3 = UIPlot()
        self._populate_distribution(p3, view, "last_action")
        p3.set_layout_opt("xaxis", {"title": None})
        p3.set_layout_opt("yaxis", {"title": "#Peers per Action"})
        dash.add_panel(p3, "right_bot")

        return dash.to_json()
    
    def _populate_best_student_table(self, panel: UIPlot, view: Dict):
        """Table 1: Student Specifics"""
        best = self._get_last_val_from_view(view, "overall_best_student")
        rows = [
            ["Best Student", best[-6:] if best else "N/A"],
            ["Best Acc", self._get_last_val_from_view(view, "accuracy") or "N/A"],
        ]
        panel.add_table(headers=None, columns=[[r[0] for r in rows], [r[1] for r in rows]])
    
    def _populate_world_counters_table(self, panel: UIPlot, view: Dict):
        """Table 2: Global Counters"""
        rows = [
            ["#World Masters", self._get_last_val_from_view(view, "world_masters")],
            ["#World Agents", self._get_last_val_from_view(view, "world_agents")],
            ["#Human Agents", self._get_last_val_from_view(view, "human_agents")]
        ]
        panel.add_table(headers=None, columns=[[r[0] for r in rows], [r[1] for r in rows]])
