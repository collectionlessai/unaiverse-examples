from demo_script_b import SCRIPT, INDEX_FILE
from src.demo import DemoAgent, ScriptedModule
from unaiverse.networking.node.node import Node

agent = DemoAgent(proc=ScriptedModule(
    SCRIPT, INDEX_FILE, agent_name="Luca Human Member"))

node = Node(agent, node_name="Luca Human Member", hidden=True, clock_delta=1. / 20.)
node.run(join_world="ACMECorp", role_preference="team_manager")
