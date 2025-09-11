import os
from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.utils.misc import check_json_start
from unaiverse.streams import ImageFileStream, DataStream

# Monitoring file
check_json_start(file='extracted_info.json',
                 delete_existing=True,
                 msg="\nStarted monitoring file extracted_info.json...")

# Agent
agent = Agent(proc=None)

data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'animals')

stream = DataStream.create(group="animal_stream", public=False,
                           stream=ImageFileStream(image_dir=data_path, show_images=True,
                                                  list_of_image_files=data_path + "/first3c_1i.csv"))
agent.add_stream(stream)
agent.add_behav_wildcard("<stream_name>", "animal_stream")
agent.add_behav_wildcard("<stream_len>", len(stream))

# Node hosting agent
node = Node(node_name="Test0", hosted=agent, hidden=True, clock_delta=1. / 10.)

# Telling agent to join world
node.ask_to_join_world(node_name="InfoExtraction")

# Running node
node.run()
