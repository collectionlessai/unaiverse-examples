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

        # Engaging students, teaching and, afterward, evaluating students
        behav.add_transit("init",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors",
                                       "teach-playlist_eval-playlist-lastrep_looped.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<agent>:smoHfHa", "<agent>:smoHfLa", "<agent>:smoLfHa",
                                               "<agent>:smoLfLa", "<agent>:squHfHa", "<agent>:squHfLa",
                                               "<agent>:squLfHa"], "repeat": 3 + 1})

        # Testing generalization
        behav.add_transit("finished_work", "hard_exam_in_progress", action="ask_gen",
                          args={"u_hashes": ["<agent>:squLfLa"], "samples": 1000, "timeout": 5.0})
        behav.add_transit("hard_exam_in_progress", "eval_time_again", action="done_gen")
        behav.add_state("eval_time_again", action="evaluate",
                        args={"stream_hash": "<agent>:squLfLa", "how": "mse", "steps": 1000})
        behav.add_transit("eval_time_again", "very_good",
                          action="compare_eval", args={"cmp": "<=", "thres": 0.2})
        behav.add_transit("eval_time_again", "not_good", action="nop")

        # Wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": "student",
                             "<learn_steps>": 1000, "<eval_steps>": 1000, "<cmp_thres>": 0.2})

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
