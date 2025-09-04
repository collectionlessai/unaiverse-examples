import os
import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import get_node_addresses_from_file

# agent "Fred" (student 2)
net = CNN(3, return_input=True, seed=42)
agent = Agent(proc=net,
              proc_opts={'optimizer': torch.optim.SGD(net.module.parameters(), lr=0.0025),
                         'losses': [torch.nn.functional.mse_loss, torch.nn.functional.binary_cross_entropy]},
              buffer_generated_by_others="all")
agent.proc_outputs[1].set_tensor_labels(["albatross", "cheetah", "giraffe"])

# node hosting agent "Fred" (student 1)
node = Node(node_id="80b825fe93e547ca8c75b094e1788e61",
            password="password", hosted=agent, clock_delta=1. / 1000.)

# telling "Alice" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
