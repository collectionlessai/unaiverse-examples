import os
import asyncio
from src.world import WWorld
from unaiverse.utils.logger import log
from unaiverse.utils.misc import build_unaid
from unaiverse.networking.node.node import Node

# World
world = WWorld()

# CHALLENGE RESET: touching the sentinel file below (touch src/RESET_STATS on the world machine) wipes
# ALL the stats — dynamic (votes, conversations, ops history) AND static — like starting from scratch,
# WHILE the world keeps running: nobody has to leave. The wipe runs on the node main loop (same loop of
# the stats saver, no writer race).
RESET_SENTINEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "RESET_STATS")

# BAN LIST: src/banned.txt holds the UNaIDs ("<nickname>/<node_name>") of the banned agents, one per
# line (a missing file means nobody is banned). New joins of banned agents are refused by
# WWorld.assign_role; the check below completes the picture for the agents ALREADY in the world: when
# the file changes it is reloaded (WWorld.refresh_banned_list, tracked like managers.txt), and every
# known agent found in the list is disconnected (scheduled on the node loop, where this hook runs)


def run_hook(node):  # noqa (the Node passes itself)
    world.refresh_banned_list()
    if world.banned_sweep_needed and world.node_purge_fcn is not None:
        world.banned_sweep_needed = False
        for peer_id, profile in {**world.world_masters, **world.world_agents}.items():
            unaid = build_unaid(profile)
            if unaid in world.banned_agents:
                log.user(f"Disconnecting banned agent: {unaid}")
                asyncio.get_running_loop().create_task(world.node_purge_fcn(peer_id))
    if os.path.exists(RESET_SENTINEL):
        try:
            os.remove(RESET_SENTINEL)  # Removed FIRST: even a failed reset must not loop forever
            world.stats.reset_stats()
            log.user("[stats] RESET_STATS done: local stats wiped")
        except Exception as e:
            log.error(f"[stats] RESET_STATS failed: {e}")


# Node hosting world
node = Node(node_name="TuringHotel", hosted=world, hidden=True, clock_delta=1./50.,
            run_hook=run_hook)

# Running node
node.run(show_senders=False)
