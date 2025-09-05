import os
import torch
from unaiverse.agent import Agent
from unaiverse.modules.hl.hl_utils import HL
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file
from unaiverse.modules.networks import CTBEInitStateBZeroInput

tot_num_labels = 6

# agent "Bob" (student 1)
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

# node hosting agent "Bob"
node = Node(node_id="5bacc8b5504c417d880ac1a8d147fbe1",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 1000.)

# telling "Bob" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
