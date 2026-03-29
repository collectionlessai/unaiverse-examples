import os
import argparse
from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.custom import GenException
from unaiverse.modules.utils import HumanModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import PolicyFilterHuman

# Parsing command line
parser = argparse.ArgumentParser(description="Human interface to UNaIVERSE (Python)")
parser.add_argument("--node", type=str, required=False, help="Name of the node where to run this agent",
                    default="_HumanPython_")
group = parser.add_mutually_exclusive_group()
group.add_argument("--world", type=str, help="Name of the target world")
group.add_argument("--agent", type=str, help="Name of the target agent")
parser.add_argument("--no_img", action="store_true", help="Enable text-only mode")
cmd_args = parser.parse_args()

# Supported outputs
outputs = [StreamType(data_type="text", pubsub=False, private_only=False)]
if not cmd_args.no_img:
    outputs.append(StreamType(data_type="img", pubsub=False, private_only=False))

# Agent
agent = Agent(proc=HumanModule(),
              proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=False),
                           StreamType(data_type="img", pubsub=False, private_only=False),
                           StreamType(data_type="all", pubsub=False, private_only=False)],
              proc_outputs=outputs,
              proc_opts={},
              policy_filter=PolicyFilterHuman())

# Node hosting agent
node_agent = Node(node_name=cmd_args.node, hosted=agent, hidden=True, clock_delta=1.)

# Running node
try:
    os.environ["NODE_IGNORE_ALIVE"] = "1"
    if cmd_args.agent:
        node_agent.run(get_in_touch=cmd_args.agent, interact_mode=True)
    elif cmd_args.world:
        node_agent.run(join_world=cmd_args.world, interact_mode=True)
    else:
        node_agent.run(interact_mode=True)
except GenException as e:
    print(e)
