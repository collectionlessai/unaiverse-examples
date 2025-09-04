import os
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Generic1" (broadcaster)
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=True)])  # also switch to pubsub=True

# node hosting agent "Generic1" (broadcaster)
node = Node(node_id="255b2dbf73134e18877365d4b9323f46",  # "31a6cea30df847caa22579d55ac06f8d"
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling "Generic1" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
