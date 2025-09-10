import os
import torch
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.streams import TokensStream
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import RNNTokenLM

# Creating a stream that will not be shared at all, just  to get the vocabulary
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'cats', 'stream_of_words.csv')
stream = TokensStream(tokens_file_csv=data_path, max_tokens=998)
voc_size = len(stream.get_props().proc_to_stream_transforms)
voc = stream.get_props().proc_to_stream_transforms

# Agent
net = RNNTokenLM(num_emb=voc_size, emb_dim=16, y_dim=voc_size, h_dim=100, seed=42)
agent = Agent(proc=net,
              proc_inputs=[],
              proc_outputs=[Data4Proc(data_type="text",
                                      stream_to_proc_transforms={w: i for i, w in enumerate(voc)},
                                      proc_to_stream_transforms=voc,
                                      pubsub=False)],
              proc_opts={
                  'optimizer': torch.optim.SGD(net.parameters(), lr=0.01),
                  'losses': [torch.nn.functional.cross_entropy]
              }, buffer_generated_by_others="all")

# Node hosting agent
node = Node(node_name="Test1", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="Test0")

# Running node
node.run()
