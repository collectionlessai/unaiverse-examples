import os
#from unaiverse.agent import Agent
from src.guest import WAgent as Agent
from unaiverse.streams.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.modules.utils import LoggerModule
from unaiverse.utils.misc import PolicyFilterDelayAction

# Agent
# processor = LoggerModule(os.path.join(os.path.dirname(os.path.abspath(__file__)), "log", "proc_run_3.log"))
processor = LoggerModule()
agent = Agent(proc=processor,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={},
              policy_filter=PolicyFilterDelayAction({"process"}, wait=1., add_random_up_to=1.))

# Node hosting agent
node = Node(node_name="Grace", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Running node
node.run(join_world="_TuringHotel")
