import torch
from unaiverse.agent import Agent
from unaiverse.modules.hl.hl_utils import HL
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import CTBEInitStateBZeroInput

# Agent
tot_num_labels = 6
net = CTBEInitStateBZeroInput(u_shape=(1,), d_dim=tot_num_labels, y_dim=1,
                              h_dim=1000, local=True,
                              delta=0.1, cnu_memories=20, seed=42)
agent = Agent(proc=net,
              proc_opts={
                  'optimizer': HL(net, gamma=1., theta=0.2, beta=0.01,
                                  reset_neuron_costate=False, reset_weight_costate=False, local=True),
                  'losses': [torch.nn.functional.mse_loss]
              },
              buffer_generated_by_others="all")

# Node hosting agent
node = Node(node_name="Test2", hosted=agent, hidden=True, clock_delta=1. / 1000.)

# Telling agent to join world
node.ask_to_join_world(node_name="Test0")

# Running node
node.run()
