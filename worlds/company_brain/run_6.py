from unaiverse.agent import Agent
from unaiverse.networking.node.node import Node
from unaiverse.streams.dataprops import StreamType
from unaiverse.streams import DataStream, TokensStream

# Agent
agent = Agent(proc=None,
              proc_inputs=[StreamType(data_type="text", pubsub=False, private_only=True)],
              proc_outputs=[StreamType(data_type="text", pubsub=False, private_only=True)])

# Robot stream
stream = DataStream.create(TokensStream("src/sensor.dat"),
                           "sensor", "sensor_group", public=False, pubsub=True)
stream.props.delta = 10.0
agent.add_stream(stream)

# Node hosting agent
node = Node(agent, node_name="Drone", hidden=True, clock_delta=1. / 20.)

# Running node
node.run(join_world="CompanyBrain", role_preference="team_member")
