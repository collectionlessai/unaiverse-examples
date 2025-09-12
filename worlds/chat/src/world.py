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
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        super().__init__(world_folder=os.path.dirname(os.path.abspath(__file__)), **kwargs)

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
        behav.set_role("user")

        behav.add_transit("init", "ready",
                          action="connect_to_broadcaster", args={"role": "broadcaster"})
        behav.add_state("ready", action="check_messages",
                        args={"max_silence_seconds": 20.0, "talk_probability": 0.33, "history_len": 3})
        behav.add_transit("ready", "message_sent",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1, "ignore_uuid": True},
                          ready=False)
        behav.add_transit("message_sent", "ready", action="nop")
        behav.add_transit("ready", "init", action="disconnected")

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'user.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: broadcaster
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("broadcaster")

        behav.add_transit("ready", "ready", action="do_gen", args={"timeout": 3.0}, ready=False)

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'broadcaster.json'), only_if_changed=dummy_agent)
