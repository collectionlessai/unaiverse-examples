import torch
import wandb
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node


def my_wandb_logger(node: Node):
    # Define a callback to log yo wandb every N cycles
    if node.clock.get_cycle() % 100 != 0:
        return

    metrics = {
        "cycle": node.clock.get_cycle(),
        "state": node.hosted.behav.get_state_name(),
        "action": node.hosted.behav.get_action_name(),
        "last_completed_action": node.hosted.behav.get_last_completed_action_name(),
    }
    print(metrics)
    # wandb.log(metrics)

# Agent
net = CNN(d_dim=10, in_channels=1, seed=42)
net.transforms = lambda x: x  # Processing tensor data
agent = Agent(proc=net,
              proc_inputs=[Data4Proc(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                     pubsub=False, private_only=True)],
              proc_outputs=[Data4Proc(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                      pubsub=False, private_only=True,
                                      proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts={'optimizer': torch.optim.Adam(net.parameters(), lr=0.001),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="none")

# Node hosting agent
node = Node(node_name="DigitClassifier2", hosted=agent, hidden=True, clock_delta=1. / 10.,
            run_hook=my_wandb_logger)

# Init wandb
# wandb.init(project="social_learning_example", name="DigitClassifier2")

# Running node
node.run(join_world="DigitSocialLearning")
