from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Morning team. Today we focus on Line 4 tuning. Brain, can you sync us with what we closed yesterday?",
    "Perfect. I am off to another call. Luca, take it from here, ping only if needed."
]

agent = DemoAgent(proc=ScriptedModule(messages),
                  auto_start=True, respond_to_any=True, silence_delay=30.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="Sara", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
