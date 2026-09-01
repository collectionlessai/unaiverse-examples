import os
import asyncio
from src.world import WWorld
from unaiverse.utils.logger import log
from unaiverse.utils.misc import build_unaid
from unaiverse.networking.node.node import Node
from src.mirror import make_mirror_hook, MirrorMySQLTarget

# World
world = WWorld()

# Stats mirroring
MIRROR_PERIOD = 30.
mirror_hook = None
if MIRROR_PERIOD > 0:
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "config.mirror")
    if os.path.exists(config_file):
        assert world.stats is not None
        mirror_hook = make_mirror_hook(str(world.stats.db_path), MirrorMySQLTarget(config_file),  # noqa
                                       period=MIRROR_PERIOD)
        log.user(f"[stats-mirror] Active: pushing stats to MySQL every {MIRROR_PERIOD:.0f}s "
                 f"(config: {config_file})")
    else:
        log.user(f"[stats-mirror] OFF: no {config_file} (copy src/config.mirror.example and fill it in)")

# CHALLENGE RESET: touching the sentinel file below (touch src/RESET_STATS on the world machine) wipes
# ALL the stats — dynamic (votes, conversations, ops history) AND static — like starting from scratch,
# WHILE the world keeps running: nobody has to leave. The wipe runs on the node main loop (same loop of
# the stats saver, no writer race) and the mirror is re-armed right after: its next cycle finds the
# remote AHEAD of the wiped local DB, so it truncates the remote tables too (local + mirrored DB reset
# in one gesture)
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
            if mirror_hook is not None:
                mirror_hook.reset()
            log.user("[stats] RESET_STATS done: local stats wiped"
                     + (", the mirror will now clear the remote" if mirror_hook is not None else ""))
        except Exception as e:
            log.error(f"[stats] RESET_STATS failed: {e}")
    if mirror_hook is not None:
        mirror_hook(node)  # noqa


# Node hosting world
node = Node(node_name="TuringHotelItaly", hosted=world, hidden=True, clock_delta=1./50.,
            run_hook=run_hook)

# Running node
node.run(show_senders=False)
