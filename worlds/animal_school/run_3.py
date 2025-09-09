import os
import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# Agent
net = CNN(3, return_input=True, seed=42)
agent = Agent(proc=net,
              proc_opts={'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.0025),
                         'losses': [torch.nn.functional.mse_loss, torch.nn.functional.binary_cross_entropy]},
              buffer_generated_by_others="all")
agent.proc_outputs[1].set_tensor_labels(["albatross", "cheetah", "giraffe"])

# Node hosting agent
node = Node(node_name="Test3", unaiverse_key="<UNAIVERSE_KEY_GOES_HERE>",
            hosted=agent, clock_delta=1. / 1000.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run()
