import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node

# Agent
net = CNN(3, return_input=True, seed=42)
agent = Agent(proc=net,
              proc_opts={'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.0025),
                         'losses': [torch.nn.functional.mse_loss, torch.nn.functional.binary_cross_entropy]},
              buffer_generated_by_others="all")
agent.proc_outputs[1].set_tensor_labels(["albatross", "cheetah", "giraffe"])

# Node hosting agent
node = Node(node_name="Test3", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Telling agent to join world
node.ask_to_join_world(node_name="Test0")

# Running node
node.run()
