from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Pressure stable, slightly decreasing."
]

agent = DemoAgent(proc=ScriptedModule(messages), silence_delay=300.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

node = Node(agent, node_name="Luca Human Member", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
