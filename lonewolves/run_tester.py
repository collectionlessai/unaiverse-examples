from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.utils import HumanModule
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=HumanModule(),
              proc_inputs=[Data4Proc(data_type="text", pubsub=False, private_only=False),
                           Data4Proc(data_type="img", pubsub=False, private_only=False)],
              proc_outputs=[Data4Proc(data_type="text", pubsub=False, private_only=False),
                            Data4Proc(data_type="img", pubsub=False, private_only=False)],
              proc_opts={})

# Node hosting agent
node_agent = Node(node_name="Test0", hosted=agent, hidden=True, clock_delta=1)  # TODO set name as Tester

# Connecting to a lone wolf
#agent_name = input("Name of the lone wolf to connect to: ").strip()

agent_name = "LangSAM"
#import time
#start = time.time()
#while time.time() - start < 20:
#    pass # Keep the Python interpreter "active"

# Running node
node_agent.run(get_in_touch=agent_name, interact_mode=True)
