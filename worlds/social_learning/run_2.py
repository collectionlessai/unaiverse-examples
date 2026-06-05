import torch
from unaiverse.agent import Agent
from unaiverse.modules.networks import CNN
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType


# Example
def my_wandb_logger(_node: Node):
    # Define a callback to log yo wandb every N cycles
    if _node.clock.get_cycle() % 100 != 0:
        return

    metrics = {
        "cycle": _node.clock.get_cycle(),
        "state": _node.hosted.behav.get_state_name(),
        "action": _node.hosted.behav.get_action_name(),
        "last_completed_action": _node.hosted.behav.get_last_completed_action_name(),
    }
    # print(metrics)
    # wandb.log(metrics)


# Agent
net = CNN(d_dim=10, in_channels=1, seed=42)
net.transforms = lambda x: x  # Processing tensor data
agent = Agent(proc=net,
              proc_inputs=[StreamType(data_type="tensor", tensor_shape=(None, 1, 28, 28), tensor_dtype=torch.float32,
                                      pubsub=False, private_only=True)],
              proc_outputs=[StreamType(data_type="tensor", tensor_shape=(None,), tensor_dtype=torch.long,
                                       pubsub=False, private_only=True,
                                       proc_to_stream_transforms=lambda x: torch.argmax(x, dim=1))],
              proc_opts={'optimizer': torch.optim.Adam(net.parameters(), lr=0.001),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="none")

# Node hosting agent
node = Node(agent, node_name="DigitClassifier2", hidden=True, clock_delta=1. / 15.,
            run_hook=my_wandb_logger)

# Init W&B
# wandb.init(project="social_learning_new_example", name="DigitClassifierNew2")

# Running node
node.run(join_world="DigitSocialLearning", resume_from_checkpoint=True)
