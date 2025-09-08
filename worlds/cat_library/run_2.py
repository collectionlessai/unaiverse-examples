import os
import sys
import torch
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.streams import TokensStream
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import RNNTokenLM
from unaiverse.utils.misc import get_node_addresses_from_file

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

# TODO replace node_id="..." with node_name="Test1"
# TODO replace password with unaiverse key
# Node hosting agent
node = Node(node_id="27ec668f13e644c782659a6ac1370a4a", hidden=True,
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# Running node
node.run()
