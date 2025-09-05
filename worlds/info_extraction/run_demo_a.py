import os
import sys
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.streams import ImageFileStream, DataStream
from unaiverse.utils.misc import get_node_addresses_from_file, check_json_start, Silent

# monitoring file
check_json_start(file=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extracted_info.json'),
                 delete_existing=True,
                 msg="\nStarted monitoring file extracted_info.json...")

# agent (Image Streamer)
agent = Agent(proc=None)

data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', '..', 'unaiverse', 'library', 'data', 'animals')

stream = DataStream.create(group="animal_stream", public=False,
                           stream=ImageFileStream(image_dir=data_path, show_images=True,
                                                  list_of_image_files=data_path + "/first3c_1i.csv"))
agent.add_stream(stream)
agent.add_behav_wildcard("<stream_name>", "animal_stream")
agent.add_behav_wildcard("<stream_len>", len(stream))

# node hosting agent
node = Node(node_id="e027812a81a94401a94c8e43526f66d1",
            unaiverse_key="password", hosted=agent, clock_delta=1. / 10.)

# telling agent to join world
node.ask_to_join_world(addresses=get_node_addresses_from_file(os.path.dirname(__file__)))

# running node
node.run()
