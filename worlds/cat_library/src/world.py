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
from unaiverse.streams import DataStream, TokensStream
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        super().__init__(world_folder=os.path.dirname(os.path.abspath(__file__)), **kwargs)

        # Adding streams
        data_path = os.path.join(self.world_folder, '..', '..', '..', 'data', 'cats', 'stream_of_words.csv')

        self.add_stream(DataStream.create(name="cats", public=False,
                                          stream=TokensStream(tokens_file_csv=data_path, max_tokens=998)))

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return "teacher"
            else:
                return "student"
        else:
            return "student"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)
        from agent import WAgent
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: teacher
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("teacher")
        num_samples = 998

        # Preparing book
        behav.add_transit("init", "book_prepared", action="record",
                          args={"net_hash": "<world>:cats", "samples": num_samples, "timeout": 10.0})

        # Engaging students, teaching and, afterward, evaluating students
        behav.add_transit("book_prepared",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors",
                                       "teach-playlist_eval-recorded1.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<agent>:recorded1"], "repeat": 50})

        # Wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": "student",
                             "<learn_steps>": num_samples, "<eval_steps>": num_samples, "<cmp_thres>": 0.2})

        # Data tags are not reliable at evaluation time: forcing the tag of the first compared pair to be the same
        behav.states["eval_time"].action.args['re_offset'] = True
        behav.states["eval_time"].action.args_with_wildcards['re_offset'] = True

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: student
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("student")

        # Generic behaviour of a student who listens to the requests from the teacher
        behav.add_transit("init",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors", "listening_to_teacher.json"),
                          action="get_engagement",
                          args={"acceptable_role": "teacher"})

        # When the teacher will send the student back home
        behav.add_transit("teacher_engaged", "init", action="get_disengagement")

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)
