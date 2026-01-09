"""
       █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
      ░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
       ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░ 
       ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████   
       ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█   
       ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
       ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
        ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░ 
                 A Collectionless AI Project (https://collectionless.ai)
                 Registration/Login: https://unaiverse.io
                 Code Repositories:  https://github.com/collectionlessai/
                 Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""
import os
from .stats import WStats
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=f"{world_folder}/stats/world_stats.db")
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return "broadcaster"
            else:
                return "user"
        else:
            return "user"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)
        from agent import WAgent
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: user
        behav = HybridStateMachine(dummy_agent)
        behav.set_welcome_message("🗯️ This world implements a simple chatroom where you can talk to humans and AIs. "
                                  "AI-based agents, when joining this world, inherit the skill of promoting the "
                                  "conversation if there is too much 'silence' in the chat.")
        behav.set_role("user")

        behav.add_state("init", blocking=True)
        behav.add_state("waiting_handshake", blocking=False)
        behav.add_state("self_generated", blocking=False)
        behav.add_state("message_sent", blocking=False)

        behav.add_transit("init", "waiting_handshake",
                          action="connect_to_broadcaster", args={"role": "broadcaster"},
                          msg="🔗 Connecting to the room...")
        behav.add_transit("waiting_handshake", "ready",
                          action="connected", args={"handshake_completed": True})
        behav.add_state("ready", action="check_messages",
                        args={"max_silence_seconds": 25.0, "talk_probability": 0.01, "history_len": 3},
                        msg="👍 Ready!")
        behav.add_transit("ready", "message_sent",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1, "ignore_uuid": True},
                          ready=False)
        behav.add_transit("message_sent", "ready", action="nop")
        behav.add_transit("ready", "init", action="disconnected", args={"delay": 5.0})
        behav.add_transit("ready", "self_generated",
                          action="do_gen", args={"u_hashes": ["<agent>:processor_in"], "samples": 1},
                          ready=True, avoid_changing_ready=True)
        behav.add_transit("self_generated", "message_sent",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1, "ignore_uuid": True})

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'user.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: broadcaster
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("broadcaster")

        behav.add_transit("ready", "ready", action="do_gen", args={"timeout": 5.0}, ready=False)

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'broadcaster.json'), only_if_changed=dummy_agent)
