import os
import sys
from unaiverse.agent import Agent
from unaiverse.utils.logger import log
from unaiverse.networking.node.node import Node

# Agent
agent = Agent(proc=None, proc_inputs=["text"], proc_outputs=["text"])

# LIVE SWITCH (same sentinel-file pattern of RESET_STATS in run_w.py): touching src/BROADCAST_WHEN_NO_HUMANS
# on this machine forces Config.broadcast_when_no_humans to True, touching src/BROADCAST_WHEN_HUMANS brings
# it back to False — WHILE the floor manager keeps running. The sentinel is deleted once applied (and a
# message confirms it). NOTE: the manager runs the WORLD-SHIPPED code, loaded in a dynamic module namespace
# at role-acceptance time, so the live Config class is resolved from the hosted agent's own module (a local
# "from src.config import Config" here would flip a different, unused copy). Before the role is accepted
# there is no Config yet: the sentinel is simply left in place and applied on a later cycle.
SENTINELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
SENTINELS = (("BROADCAST_WHEN_NO_HUMANS", True), ("BROADCAST_WHEN_HUMANS", False))


def run_hook(node):  # noqa (the Node passes itself)
    for sentinel, value in SENTINELS:
        path = os.path.join(SENTINELS_DIR, sentinel)
        if os.path.exists(path):
            config = getattr(sys.modules.get(type(node.hosted).__module__, None), "Config", None)
            if config is None:
                return  # Not a floor manager yet (role not accepted): keep the sentinel for a later cycle
            try:
                os.remove(path)  # Removed FIRST: even a failed switch must not loop forever
                config.broadcast_when_no_humans = value
                log.user(f"[config] Sentinel {sentinel} detected (and deleted): "
                         f"Config.broadcast_when_no_humans is now {value}")
            except Exception as e:
                log.error(f"[config] Sentinel {sentinel} could not be applied: {e}")


# Node hosting agent
node = Node(node_name="FloorManager-TuringHotelItaly", hosted=agent, hidden=True, clock_delta=1. / 50.,
            run_hook=run_hook)

# Running node
node.run(join_world="TuringHotelItaly")
