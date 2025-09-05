import os
import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNNCNU
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent
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

# TODO replace node_id="..." with node_name="Test2"
# TODO replace password with unaiverse key
# node hosting agent
node = Node(node_id="ade8d52bd2ae4c5ebd3e2bdb17ba99c6",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 1000.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
