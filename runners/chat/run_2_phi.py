import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.library.modules.networks import Phi
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Generic2" (user 1)
agent = Agent(proc=Phi(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],
              proc_opts={})

# node hosting agent "Generic2" (user 1)
node = Node(node_id="3054024a135c4e65b495e8720e775881",  # "beaea0e7a13b44b3aa2339c11cfc2020",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling "Bob" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
