import argparse
from unaiverse.agent import Agent
from unaiverse.modules.utils import HumanModule
from unaiverse.networking.node.node import Node
from unaiverse.custom import GenException, Custom

# Parsing command line
parser = argparse.ArgumentParser(description="Human interface to UNaIVERSE (Python)")
parser.add_argument("--node", type=str, required=False, help="Name of the node where to run this agent",
                    default="HumanPython")
group = parser.add_mutually_exclusive_group()
group.add_argument("--world", type=str, help="Name of the target world")
group.add_argument("--agent", type=str, help="Name of the target agent")
parser.add_argument("--no_img", action="store_true", help="Enable text-only mode")
cmd_args = parser.parse_args()
Custom.SKIP_WAS_ALIVE_CHECK = True

# Agent
agent = Agent(proc=HumanModule(),
              proc_inputs=["text", "img", "all"],
              proc_outputs=["text"] if cmd_args.no_img else ["text", "img"])

# Node hosting agent
node_agent = Node(agent, node_name=cmd_args.node, clock_delta=1./10.)

# Running node
try:
    if cmd_args.agent:
        node_agent.run(get_in_touch=cmd_args.agent, interact_mode=True)
    elif cmd_args.world:
        node_agent.run(join_world=cmd_args.world, interact_mode=True)
    else:
        node_agent.run(interact_mode=True)
except GenException as e:
    print(e)
