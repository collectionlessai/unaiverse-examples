import argparse
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.utils import HumanModule
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import GenException, PolicyFilterHuman

# Parsing command line
parser = argparse.ArgumentParser(description="Python connector")
group = parser.add_mutually_exclusive_group()
group.add_argument("--world", type=str, help="Name of the target world")
group.add_argument("--agent", type=str, help="Name of the target agent")
parser.add_argument("--no_img", action="store_true", help="Enable text-only mode")
cmd_args = parser.parse_args()

# Getting arguments that were not provided by command line
if not cmd_args.world and not cmd_args.agent:
    while True:
        wanna_join_world = input("Do you want to join a world? [y/n]").strip().lower()
        if wanna_join_world == 'y':
            wanna_join_world = True
            break
        elif wanna_join_world == 'n':
            wanna_join_world = False
            break
    agent_world_name = None
    while True:
        if wanna_join_world:
            agent_world_name = input("Name of the world to connect to: ").strip()
        else:
            agent_world_name = input("Name of the lone wolf to connect to: ").strip()
        if len(agent_world_name) > 0:
            break
elif cmd_args.world:
    wanna_join_world = True
    agent_world_name = cmd_args.world
else:
    wanna_join_world = False
    agent_world_name = cmd_args.agent

# Supported outputs
outputs = [Data4Proc(data_type="text", pubsub=False, private_only=False)]
if not cmd_args.no_img:
    outputs.append(Data4Proc(data_type="img", pubsub=False, private_only=False))

# Agent
agent = Agent(proc=HumanModule(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False),
                           Data4Proc(data_type="img", pubsub=False, private_only=False),
                           Data4Proc(data_type="all", pubsub=False, private_only=False)],
              proc_outputs=outputs,
              proc_opts={},
              policy_filter=PolicyFilterHuman())

# Node hosting agent
node_agent = Node(node_name="Test0", hosted=agent, hidden=True, clock_delta=1.)  # TODO set name as Tester

# Running node
try:
    if not wanna_join_world:
        node_agent.run(get_in_touch=agent_world_name, interact_mode=True)
    else:
        node_agent.run(join_world=agent_world_name, interact_mode=True)
except GenException as e:
    print(e)
