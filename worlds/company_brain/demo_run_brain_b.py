from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Hi Elena, quick brief. Drone-07 flagged a thermal anomaly in Area B-3. "
    "Expert assessed it as out-of-pattern with moderate confidence. "
    "Luca is on site, waiting on your input.",

    "Event logged. Resolution path stored in the Company World. "
    "I will surface this case automatically if a similar pattern reappears."
]

log_msg = "\U0001f4cb Knowledge Base updated: Type-B thermal event — Area B-3 — resolution stored."

agent = DemoAgent(proc=ScriptedModule(messages, log_on_finish=log_msg),
                  auto_start=True, silence_delay=30.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="Brain", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="brain")
