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
import sys
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
                return "dispatcher"
            else:
                return "team_member"
        else:
            if 'tmp_role_preference' in profile.get_dynamic_profile():
                role_preference = profile.get_dynamic_profile()['tmp_role_preference']
                if role_preference in {"team_member", "team_manager", "brain", "expert"}:
                    return role_preference
                else:
                    return "team_member"
            else:
                return "team_member"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""
        sys.path.append(self.world_folder)

        # Creating a dummy agent to check actions
        from .brain import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)

        # ROLE (1,2,3,4)/5: brain, team_manager, team_member, expert
        behav.set_welcome_message("🗯️ This world implements a team-work chatroom where you can talk to humans and AIs. "
                                  "AI-based agents, when joining this world, inherit skills in function of their "
                                  "role.")

        behav.add_state("init", blocking=True)
        behav.add_state("waiting_handshake", blocking=False)
        behav.add_state("self_generated", blocking=False)
        behav.add_state("message_sent", blocking=False)

        behav.add_transit("init", "waiting_handshake",
                          action="connect_to_dispatcher", args={"role": "dispatcher"},
                          msg="🔗 Connecting to the room...")
        behav.add_transit("waiting_handshake", "ready",
                          action="connected", args={"handshake_completed": True})
        behav.add_transit("waiting_handshake", "init", action="disconnected", args={"delay": 5.0})
        behav.add_state("ready", action="check_messages",
                        args={"max_silence_seconds": 25.0, "talk_probability": 0.01, "history_len": 3},
                        msg="👍 Ready!")
        behav.add_transit("message_sent", "ready", action="nop")
        behav.add_transit("ready", "init", action="disconnected", args={"delay": 5.0})
        behav.add_transit("ready", "self_generated",
                          action="do_gen", args={"u_hashes": ["<agent>:processor_in"], "samples": 1},
                          ready=True, avoid_changing_ready=True)
        behav.add_transit("self_generated", "message_sent",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1, "ignore_uuid": True})

        # Saving to file
        behav.set_role("brain")
        behav.save(os.path.join(self.world_folder, behav.role + '.json'), only_if_changed=dummy_agent)
        behav.set_role("team_member")
        behav.save(os.path.join(self.world_folder, behav.role + '.json'), only_if_changed=dummy_agent)
        behav.set_role("team_manager")
        behav.save(os.path.join(self.world_folder, behav.role + '.json'), only_if_changed=dummy_agent)
        behav.set_role("expert")
        behav.save(os.path.join(self.world_folder, behav.role + '.json'), only_if_changed=dummy_agent)

        # ROLE 5/5: dispatcher
        from .dispatcher import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("dispatcher")

        behav.add_transit("ready", "ready", action="do_gen", args={}, ready=False)

        # Saving to file
        behav.save(os.path.join(self.world_folder, behav.role + '.json'), only_if_changed=dummy_agent)
