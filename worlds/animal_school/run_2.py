import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNNCNU
from unaiverse.networking.node.node import Node

# Agent
net = CNNCNU(3, cnu_memories=5, return_input=True, seed=42)
agent = Agent(proc=net,
              proc_opts={
                  'optimizer': torch.optim.SGD([
                      {'params': net.module[:-2].parameters(), 'lr': 0.0001},
                      {'params': net.module[-2:].parameters(), 'lr': 0.005}],
                      lr=0.0001),
                  'losses': [torch.nn.functional.mse_loss, torch.nn.functional.binary_cross_entropy]
              },
              buffer_generated_by_others="all")
agent.proc_outputs[1].set_tensor_labels(["albatross", "cheetah", "giraffe"])

# Node hosting agent
node = Node(node_name="Test2", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Telling agent to join world
node.ask_to_join_world(node_name="Test0")

# Running node
node.run()
