SCRIPT = [
    # --- Blocco A: Il mondo si sveglia ---
    ("Sara Human Manager",
     "Morning team. Today we focus on Line 4 tuning. "
     "Brain, can you sync us with what we closed yesterday?"),

    ("Company Brain",
     "Sara, yesterday's session, three key outcomes: "
     "Calibration drift on Line 4 was attributed to humidity in Area B. "
     "Maintenance window scheduled for Thursday. "
     "Pending action on your side, Luca, validate the new sensor thresholds."),

    ("Sara Human Manager",
     "Perfect. I am off to another call. Luca, take it from here, ping only if needed."),

    # --- Blocco B: L'anomalia ---
    ("Drone-07",
     "Anomaly detected, Area B-3. Thermal reading 18% above the rolling baseline."),

    ("HUMAN", None),   # Luca: "Expert, can you look into this? Anything to worry about?"

    ("AI Expert",
     "Cross-checking against historical patterns… "
     "Process parameters remain within nominal range, "
     "but the thermal signature does not fully match any event in my baseline. "
     "Confidence: moderate. I recommend pulling in a human specialist before any action."),

    ("HUMAN", None),   # Luca: "Brain, any similar cases for Area B-3?"

    ("Company Brain",
     "I checked past resolutions for Area B-3. "
     "Elena handled a comparable case last March. "
     "She is the best match available right now."),

    ("HUMAN", None),   # Luca: "I'll try to reach her."

    # --- Blocco C: Asincronia e memoria ---
    ("HUMAN", None),   # Luca: "Brain, can you brief Elena on what happened?"

    ("Company Brain",
     "Hi Elena, quick brief. Drone-07 flagged a thermal anomaly in Area B-3. "
     "Expert assessed it as out-of-pattern with moderate confidence. "
     "Luca is on site, waiting on your input."),

    ("Elena Human Expert",
     "Sounds like the March event. That kind of spike usually settles within ten minutes."),
    
    ("Elena Human Expert",
     "Luca, can you confirm pressure on Line 4 stayed stable in the last 15?"),

    ("HUMAN", None),   # Luca: "Pressure stable, slightly decreasing."

    ("Elena Human Expert",
     "Good. Standard procedure, log as Type-B thermal event and let it cool."),
    
    ("Elena Human Expert",
     "Brain, please record this resolution. I will review the drone footage tonight."),

    ("Company Brain",
     "Event logged. Resolution path stored in the Company World. I will surface this case automatically if a similar pattern reappears."),
]

LOG_ON_FINISH = "\U0001f4cb Knowledge Base updated: Type-B thermal event — Area B-3 — resolution stored."
INDEX_FILE = "demo_index_a.txt"
