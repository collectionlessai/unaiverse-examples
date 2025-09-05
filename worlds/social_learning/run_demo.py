import os
import sys
import torch
import importlib.util
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.modules.utils import error_rate_mnist_test_set
from unaiverse.utils.misc import get_node_addresses_from_file, countdown_start, countdown_wait

# creating neural network
net = CNN(d_dim=10, in_channels=1, seed=62)
net.transforms = lambda x: x  # processing tensor data

# evaluating before 'living'
spec = importlib.util.find_spec("unaiverse.worlds.social_learning.world")
save_path = os.path.join(os.path.dirname(os.path.abspath(spec.origin)), "mnist_data")
error_rate_initial = error_rate_mnist_test_set(net, mnist_data_save_path=save_path)
print(f"\n*** Error: {error_rate_initial}")

# creating agent
agent = Agent(proc=net,
              proc_inputs=[Data4Proc(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                     pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                      pubsub=False, private_only=True,
                                      proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts={'optimizer': torch.optim.Adam(net.parameters(), lr=0.0005),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="none")

# node hosting agent
node = Node(node_id="02c1de71207c48acbb7c62c74c04673e",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
if node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__))) is None:
    print("Connection error!")
    sys.exit(0)

# starting countdown
living_seconds = 90
c = countdown_start(living_seconds, msg="Living")

# running node
node.run(max_time=living_seconds)

# evaluating after 'living
error_rate_final = error_rate_mnist_test_set(net, mnist_data_save_path=save_path)

# final prints
countdown_wait(c)
print(f"\n*** Error (initial): {error_rate_initial}")
print(f"*** Error (final):   {error_rate_final}\n")
