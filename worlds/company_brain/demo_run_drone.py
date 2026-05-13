from demo_script_a import SCRIPT, INDEX_FILE
from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node

agent = DemoAgent(proc=ScriptedModule(
    SCRIPT, INDEX_FILE, agent_name="Drone-07"))

node = Node(agent, node_name="Drone-07", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
