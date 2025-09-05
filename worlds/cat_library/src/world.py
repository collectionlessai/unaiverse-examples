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
from agent import WAgent, CatLibraryRoles
from unaiverse.hsm import HybridStateMachine
from unaiverse.streams import DataStream, TokensStream
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World, CatLibraryRoles):

    # Feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **CatLibraryRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):

        # Dynamically re-create the behaviour files (not formally needed, just for easier develop)
        WWorld.__create_behav_files()

        # Guess the name of the folder containing this world
        world_folder_name = os.path.basename(os.path.dirname(__file__))

        # Building world
        super().__init__(*args,
                         agent_actions=os.path.join(world_folder_name, 'agent.py'),
                         role_to_behav={self.ROLE_BITS_TO_STR[self.ROLE_TEACHER]: os.path.join(world_folder_name, 'behav_teacher.json'),
                                        self.ROLE_BITS_TO_STR[self.ROLE_STUDENT]: os.path.join(world_folder_name, 'behav_student.json')},
                         **kwargs)

        # Adding streams
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data',
                                 'cats', 'stream_of_words.csv')

        self.add_stream(DataStream.create(name="cats", public=False,
                                          stream=TokensStream(tokens_file_csv=data_path, max_tokens=998)))

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return WAgent.ROLE_TEACHER
            else:
                return WAgent.ROLE_STUDENT
        else:
            return WAgent.ROLE_STUDENT

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: teacher
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_TEACHER])

        # Preparing book
        behav.add_transit("init", "book_prepared", action="record",
                          args={"net_hash": "<world>:cats", "samples": 998, "timeout": 10.0})

        # Engaging students, teaching and, afterward, evaluating students
        behav.add_transit("book_prepared",
                          os.path.join(path_of_this_file, '..', '..', "behaviors", "teach-playlist_eval-recorded1.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<agent>:recorded1"], "repeat": 50})

        # Wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_STUDENT],
                             "<learn_steps>": 998, "<eval_steps>": 998, "<cmp_thres>": 0.2})

        # Data tags are not reliable at evaluation time: forcing the tag of the first compared pair to be the same
        behav.states["eval_time"].action.args['re_offset'] = True
        behav.states["eval_time"].action.args_with_wildcards['re_offset'] = True

        # Saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_teacher.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_teacher.pdf'))

        # ROLE 2/2: student
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_STUDENT])

        # Generic behaviour of a student who listens to the requests from the teacher
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "listening_to_teacher.json"),
                          action="get_engagement",
                          args={"acceptable_role": dummy_agent.ROLE_BITS_TO_STR[dummy_agent.ROLE_TEACHER]})

        # When the teacher will send the student back home
        behav.add_transit("teacher_engaged", "init", action="get_disengagement")

        # Saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_student.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_student.pdf'))

