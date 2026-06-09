from unaiverse.agent import Agent
from unaiverse.streams import StreamType
from unaiverse.networking.node.node import Node
from unaiverse.modules.networks import FasterRCNN

# Agent
agent = Agent(proc=FasterRCNN(),
              proc_inputs=[StreamType(data_type="img", private_only=True)],
              proc_outputs=[StreamType(data_type="tensor", tensor_dtype="torch.long", tensor_shape=(None,),
                                       private_only=True),
                            StreamType(data_type="tensor", tensor_dtype="torch.float32", tensor_shape=(None,),
                                       private_only=True),
                            StreamType(data_type="tensor", tensor_dtype="torch.float32", tensor_shape=(None, 4),
                                       private_only=True),
                            StreamType(data_type="text", private_only=True)],
              proc_opts={})

# Node hosting agent
node = Node(agent, node_name="Test2", hidden=True, clock_delta=1. / 15.)

# Running node
node.run(join_world="InfoExtraction")
