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
from agent import WAgent, ChatRoles
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World, ChatRoles):

    # feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **ChatRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):

        # dynamically re-create the behaviour files (not formally needed, just for easier develop)
        WWorld.__create_behav_files()

        # guess the name of the folder containing this world
        world_folder_name = os.path.basename(os.path.dirname(__file__))

        # building world
        super().__init__(*args,
                         agent_actions=os.path.join(world_folder_name, 'agent.py'),
                         role_to_behav={self.ROLE_BITS_TO_STR[self.ROLE_USER]: os.path.join(world_folder_name, 'behav_user.json'),
                                        self.ROLE_BITS_TO_STR[self.ROLE_BROADCASTER]: os.path.join(world_folder_name, 'behav_broadcaster.json')},
                         **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return self.ROLE_BROADCASTER
            else:
                return self.ROLE_USER
        else:
            return self.ROLE_USER

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: user
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_USER])

        behav.add_transit("init", "ready",
                          action="connect_to_broadcaster",
                          args={"role": WWorld.ROLE_BITS_TO_STR[WAgent.ROLE_BROADCASTER]})
        behav.add_state("ready", action="check_messages",
                        args={"max_silence_seconds": 20.0, "talk_probability": 0.33, "history_len": 3})
        behav.add_transit("ready", "message_sent",
                          action="ask_gen", args={"u_hashes": ["<agent>:processor"], "samples": 1, "ignore_uuid": True},
                          ready=False)
        behav.add_transit("message_sent", "ready", action="nop")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_user.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_user.pdf'))

        # ROLE 2/2: broadcaster
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_BROADCASTER])

        behav.add_transit("ready", "ready", action="do_gen", args={"timeout": 3.0}, ready=False)

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_broadcaster.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_broadcaster.pdf'))
