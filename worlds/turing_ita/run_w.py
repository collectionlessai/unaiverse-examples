import os
from src.world import WWorld
from unaiverse.utils.logger import log
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


def run_hook(node):  # noqa (the Node passes itself)
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
