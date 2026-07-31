from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.modules.utils import LoggerModule
from unaiverse.utils.misc import PolicyFilterDelayAction

# Agent
processor = LoggerModule()
agent = Agent(proc=processor, proc_inputs=["text"], proc_outputs=["text"],
              policy_filter=PolicyFilterDelayAction({"process"}, wait=1., add_random_up_to=1.))

# Node hosting agent
node = Node(node_name="Grazia", hosted=agent, hidden=False, clock_delta=1. / 10.)

# Running node
node.run(join_world="TuringHotelItaly")
