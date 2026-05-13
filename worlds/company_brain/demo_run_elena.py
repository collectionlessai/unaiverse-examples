from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Sounds like the March event. That kind of spike usually settles within ten minutes. "
    "Luca, can you confirm pressure on Line 4 stayed stable in the last fifteen?",

    "Good. Standard procedure, log as Type-B thermal event and let it cool. "
    "Brain, please record this resolution. I will review the drone footage tonight."
]

agent = DemoAgent(proc=ScriptedModule(messages),
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="Elena", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_member")
