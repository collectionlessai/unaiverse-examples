from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node
from unaiverse.streams import DataStream, TokensStream
from unaiverse.utils.misc import PolicyFilterDelayAction

messages = [
    "Anomaly detected, Area B-3. Thermal reading 18% above the rolling baseline."
]

agent = DemoAgent(proc=ScriptedModule(messages),
                  auto_start=True, silence_delay=30.0,
                  policy_filter=PolicyFilterDelayAction({"do_gen"}, wait=3., add_random_up_to=2.))

stream = DataStream.create(TokensStream("src/sensor.dat"),
                           "sensor", "sensor_group", public=False, pubsub=True)
stream.props.delta = 10.0
agent.add_stream(stream)

node = Node(agent, node_name="Drone-07", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
