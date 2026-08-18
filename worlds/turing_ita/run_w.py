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

# Node hosting world
node = Node(node_name="TuringHotelItaly", hosted=world, hidden=True, clock_delta=1./50.,
            run_hook=mirror_hook)

# Running node
node.run(show_senders=False)
