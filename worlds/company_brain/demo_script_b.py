SCRIPT = [
    ("Luca Human Member",
     "Brain, can you brief Elena on what happened?"),
    
    ("Company Brain",
     "Hi Elena, quick brief. Drone-07 flagged a thermal anomaly in Area B-3. "
     "Expert assessed it as out-of-pattern with moderate confidence. "
     "Luca is on site, waiting on your input."),

    ("HUMAN", None),   # Elena: "Sounds like the March event. That kind of spike usually settles within ten minutes."
    
    ("HUMAN", None),   # Luca, can you confirm pressure on Line 4 stayed stable in the last 15?"

    ("Luca Human Member",
     "Pressure stable, slightly decreasing."),

    ("HUMAN", None),   # Elena: "Good. Standard procedure, log as Type-B thermal event and let it cool."
    
    ("HUMAN", None),   # Elena: "Brain, please record this resolution. I will review the drone footage tonight."

    ("Company Brain",
     "Event logged. Resolution path stored in the Company World. "
     "I will surface this case automatically if a similar pattern reappears."),
]

LOG_ON_FINISH = "\U0001f4cb Knowledge Base updated: Type-B thermal event — Area B-3 — resolution stored."
INDEX_FILE = "demo_index_b.txt"
