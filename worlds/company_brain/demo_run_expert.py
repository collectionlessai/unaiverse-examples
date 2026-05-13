from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Cross-checking against historical patterns… "
    "Process parameters remain within nominal range, "
    "but the thermal signature does not fully match any event in my baseline. "
    "Confidence: moderate. I recommend pulling in a human specialist before any action."
]

agent = DemoAgent(proc=ScriptedModule(messages), silence_delay=300.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="AI Expert", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="expert")
