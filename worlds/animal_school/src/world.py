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
from unaiverse.streams import DataStream, ImageFileStream, LabelStream


class WWorld(World):

    def __init__(self, **kwargs):
        super().__init__(world_folder=os.path.dirname(os.path.abspath(__file__)), **kwargs)

        # Adding streams
        data_path = os.path.join(self.world_folder, '..', '..', '..', 'data', 'animals')

        self.add_streams([DataStream.create(group="albatross", public=False,
                                            stream=ImageFileStream(image_dir=data_path,
                                                                   list_of_image_files=data_path + "/c1_skip_10i.csv")),
                          DataStream.create(group="albatross", public=False,
                                            stream=LabelStream(label_dir=data_path, single_class=True, line_header=True,
                                                               label_file_csv=data_path + "/c1_skip_10i.csv"))])
        self.add_streams([DataStream.create(group="cheetah", public=False,
                                            stream=ImageFileStream(image_dir=data_path,
                                                                   list_of_image_files=data_path + "/c2_skip_10i.csv")),
                          DataStream.create(group="cheetah", public=False,
                                            stream=LabelStream(label_dir=data_path, single_class=True, line_header=True,
                                                               label_file_csv=data_path + "/c2_skip_10i.csv"))])
        self.add_streams([DataStream.create(group="giraffe", public=False,
                                            stream=ImageFileStream(image_dir=data_path,
                                                                   list_of_image_files=data_path + "/c3_skip_10i.csv")),
                          DataStream.create(group="giraffe", public=False,
                                            stream=LabelStream(label_dir=data_path, single_class=True, line_header=True,
                                                               label_file_csv=data_path + "/c3_skip_10i.csv"))])
        self.add_streams([DataStream.create(group="all", public=False,
                                            stream=ImageFileStream(image_dir=data_path,
                                                                   list_of_image_files=data_path + "/first3c_10i.csv")),
                          DataStream.create(group="all", public=False,
                                            stream=LabelStream(label_dir=data_path, single_class=True, line_header=True,
                                                               label_file_csv=data_path + "/first3c_10i.csv"))])

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

        # Preparing exam
        behav.add_transit("init", "exam_prepared", action="record",
                          args={"net_hash": "<world>:all", "samples": "<eval_steps>"})

        # Engaging students, teaching and, afterward, evaluating students
        behav.add_transit("exam_prepared",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors",
                                       "teach-playlist_eval-recorded1.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<world>:albatross", "<world>:cheetah", "<world>:giraffe"]})

        # Promoting students that were positively evaluated
        behav.add_transit("good", "promote", action="suggest_role_to_world",
                          args={"agent": "<valid_cmp>",
                                "role": "teacher"})

        # Providing a badge to all the agents that finished the school with a positive mark
        behav.add_state("good", action="suggest_badges_to_world",
                        args={"agent": "<valid_cmp>", "score": 1.0, "badge_type": "completed",
                              "badge_description": "Completed the Animal School #ImageClassification #AnimalPictures"})

        # Freeing students
        behav.add_transit("promote", "habilitate", action="send_disengagement")

        # Wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": "student",
                             "<learn_steps>": 40, "<eval_steps>": 30, "<cmp_thres>": 0.45})

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
