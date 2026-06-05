import os
import torch
from unaiverse.agent import Agent
from unaiverse.streams import TokensStream
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import RNNTokenLM
from unaiverse.streams.dataprops import StreamType

# Building the vocabulary from a private, non-shared stream
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'cats', 'stream_of_words.csv')
stream = TokensStream(tokens_file_csv=data_path, max_tokens=998)
voc = stream.get_props().proc_to_stream_transforms
assert isinstance(voc, list)
voc_size = len(voc)

# Agent (RNN-based language model student). Declaring proc_inputs (same shape as proc_outputs: text tokens
# from the same vocabulary) is REQUIRED in the modern interaction-driven path: the framework's
# match_streams iterates len(proc_inputs) to wire stdin, and an empty list leaves stdin unbound so
# `process` / `learn` would silently no-op.
net = RNNTokenLM(num_emb=voc_size, emb_dim=16, y_dim=voc_size, h_dim=100, seed=42)
agent = Agent(proc=net,
              proc_inputs=[StreamType(data_type="text",
                                      stream_to_proc_transforms={w: i for i, w in enumerate(voc)},
                                      proc_to_stream_transforms=voc)],
              proc_outputs=[StreamType(data_type="text",
                                       stream_to_proc_transforms={w: i for i, w in enumerate(voc)},
                                       proc_to_stream_transforms=voc)],
              proc_opts={'optimizer': torch.optim.SGD(net.parameters(), lr=0.01),
                         'losses': [torch.nn.functional.cross_entropy]},
              buffer_generated_by_others="all")

# Node hosting agent
node = Node(node_name="Test2", hosted=agent, hidden=True, clock_delta=1. / 100.)

# Running node
node.run(join_world="CatLibrary")
