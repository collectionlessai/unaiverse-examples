import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.library.modules.networks import SmolVLM
from unaiverse.utils.misc import get_node_addresses_from_file

# agent (SmolVLM)
agent = Agent(proc=SmolVLM(),
              proc_inputs=[Data4Proc(data_type="img", pubsub=False, private_only=False),
                           Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# node hosting agent
node = Node(node_id="f3a6023bb69443088f8bc80b0fbe6ed6",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
