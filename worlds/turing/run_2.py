#from unaiverse.agent import Agent
from src.floor_manager import WAgent as Agent
from unaiverse.streams.dataprops import Data4Proc
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)])

# Node hosting agent
node = Node(node_name="TuringFloorManager", hosted=agent, hidden=True, clock_delta=1. / 2.)

# Running node
node.run(join_world="_TuringHotel")
