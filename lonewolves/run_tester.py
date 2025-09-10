from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None,
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],  # It must be public
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False)],  # It must be public
              proc_opts={})

# Node hosting agent
node_agent = Node(node_name="Tester", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Connecting to a lone wolf
agent_name = input("Name of the lone wolf to connect to: ").strip()
wolf_peer_id = node_agent.ask_to_get_in_touch(node_name=agent_name)

# Running node
if wolf_peer_id is not None:
    node_agent.run(interact_mode_opts={"lone_wolf_peer_id": wolf_peer_id})
