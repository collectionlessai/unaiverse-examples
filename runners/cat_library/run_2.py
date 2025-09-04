import os
import sys
import torch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from unaiverse.agent import Agent
from unaiverse.dataprops import Data4Proc
from unaiverse.streams import TokensStream
from unaiverse.networking.node.node import Node
from unaiverse.library.modules.networks import RNNTokenLM
from unaiverse.utils.misc import get_node_addresses_from_file

# creating a stream that will not be shared at all, just  to get the vocabulary
data_path = os.path.join(os.path.dirname(os.path.abspath(sys.modules[Agent.__module__].__file__)),
                         'library', 'data', 'cats', 'stream_of_words.csv')
stream = TokensStream(tokens_file_csv=data_path, max_tokens=998)
voc_size = len(stream.get_props().proc_to_stream_transforms)
voc = stream.get_props().proc_to_stream_transforms

# agent "Bob" (student 1)
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

# node hosting agent "Bob"
node = Node(node_id="27ec668f13e644c782659a6ac1370a4a",
            password="password", hosted=agent, clock_delta=1. / 10.)

# telling "Bob" to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
