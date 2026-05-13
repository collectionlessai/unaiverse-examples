from demo_script_a import SCRIPT, INDEX_FILE
from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node

agent = DemoAgent(proc=ScriptedModule(
    SCRIPT, INDEX_FILE, agent_name="Elena Human Expert"))

node = Node(agent, node_name="Elena Human Expert", hidden=False, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
