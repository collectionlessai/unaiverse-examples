from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Sara, yesterday's session, three key outcomes: "
    "Calibration drift on Line 4 was attributed to humidity in Area B. "
    "Maintenance window scheduled for Thursday. "
    "Pending action on your side, Luca, validate the new sensor thresholds.",

    "I checked past resolutions for Area B-3. "
    "Elena handled a comparable case last March. "
    "She is the best match available right now.",

    "Hi Elena, quick brief. Drone-07 flagged a thermal anomaly in Area B-3. "
    "Expert assessed it as out-of-pattern with moderate confidence. "
    "Luca is on site, waiting on your input.",

    "Event logged. Resolution path stored in the Company World. "
    "I will surface this case automatically if a similar pattern reappears."
]

log_msg = "\U0001f4cb Knowledge Base updated: Type-B thermal event — Area B-3 — resolution stored."

agent = DemoAgent(proc=ScriptedModule(messages, log_on_finish=log_msg), silence_delay=300.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="Company Brain", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="brain")
