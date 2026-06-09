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

from unaiverse.custom import Custom
from .stats import WStats
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.streams import Stream, ImageFileStream, LabelStream


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

        # Adding streams (same as the original animal_school world)
        data_path = os.path.join(str(self.world_folder), '..', '..', '..', 'data', 'animals')

        self.add_streams([Stream.create(group="albatross", public=False, delta=-1,
                                        stream=ImageFileStream(image_dir=data_path,
                                                               list_of_image_files=data_path + "/c1_skip_10i.csv")),
                          Stream.create(group="albatross", public=False, delta=-1,
                                        stream=LabelStream(label_dir=data_path, single_class=True,
                                                           line_header=True,
                                                           label_file_csv=data_path + "/c1_skip_10i.csv"))])
        self.add_streams([Stream.create(group="cheetah", public=False, delta=-1,
                                        stream=ImageFileStream(image_dir=data_path,
                                                               list_of_image_files=data_path + "/c2_skip_10i.csv")),
                          Stream.create(group="cheetah", public=False, delta=-1,
                                        stream=LabelStream(label_dir=data_path, single_class=True,
                                                           line_header=True,
                                                           label_file_csv=data_path + "/c2_skip_10i.csv"))])
        self.add_streams([Stream.create(group="giraffe", public=False, delta=-1,
                                        stream=ImageFileStream(image_dir=data_path,
                                                               list_of_image_files=data_path + "/c3_skip_10i.csv")),
                          Stream.create(group="giraffe", public=False, delta=-1,
                                        stream=LabelStream(label_dir=data_path, single_class=True,
                                                           line_header=True,
                                                           label_file_csv=data_path + "/c3_skip_10i.csv"))])
        self.add_streams([Stream.create(group="all", public=False, delta=-1,
                                        stream=ImageFileStream(image_dir=data_path,
                                                               list_of_image_files=data_path + "/first3c_10i.csv")),
                          Stream.create(group="all", public=False, delta=-1,
                                        stream=LabelStream(label_dir=data_path, single_class=True,
                                                           line_header=True,
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
        """Create role-behavior JSON files."""
        import sys
        assert self.world_folder
        sys.path.append(self.world_folder)

        # Behavior template
        behaviors_dir = os.path.join(self.world_folder, "..", "..", "..", "behaviors")
        engage_by_role_json = os.path.join(behaviors_dir, "engage_by_role.json")
        teach_eval_json = os.path.join(behaviors_dir, "teach-playlist_eval-recorded1.json")
        listening_json = os.path.join(behaviors_dir, "listening_to_teacher.json")

        # ROLE 1/2: teacher
        from .teacher import WAgent as TeacherAgent
        dummy_agent = TeacherAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("teacher")

        behav.add_transit("init", "snapshotting_albatross", action="record",
                          args={"streams": ["<world>:all"],
                                "num_steps": "<eval_steps>",
                                "record_uuid": None}, avoid_changing_ready=True, timeout=30.0)
        behav.add_transit("snapshotting_albatross", "snapshotting_cheetah", action="record",
                          args={"streams": ["<world>:albatross"],
                                "num_steps": "<learn_steps>",
                                "record_uuid": None}, avoid_changing_ready=True)
        behav.add_transit("snapshotting_cheetah", "snapshotting_giraffe", action="record",
                          args={"streams": ["<world>:cheetah"],
                                "num_steps": "<learn_steps>",
                                "record_uuid": None}, avoid_changing_ready=True)
        behav.add_transit("snapshotting_giraffe", "exam_prepared", action="record",
                          args={"streams": ["<world>:giraffe"],
                                "num_steps": "<learn_steps>",
                                "record_uuid": None}, avoid_changing_ready=True)

        # Engage students via the modern engage_by_role template (chained at 'exam_prepared')
        behav.add_transit("exam_prepared", engage_by_role_json, action="nop", args={})
        behav.add_wildcards({"<roles_to_engage>": "student"})

        # Wire the exam dataset reference into the teach-eval template's `evaluate` state.
        behav.add_wildcards({"<exam_data_ref>": Custom.AGENT_WILDCARD + ":recorded1"})

        # Teach each class in the playlist (auto-named `recorded2` / `recorded3` / `recorded4` from
        # the snapshotting transits above), then exam against `recorded1` (the mixed shared set).
        behav.add_transit("engagement_complete", teach_eval_json,
                          action="set_pref_streams",
                          args={"net_hashes": [Custom.AGENT_WILDCARD + ":recorded2",
                                               Custom.AGENT_WILDCARD + ":recorded3",
                                               Custom.AGENT_WILDCARD + ":recorded4"]})

        # Badging successfully-evaluated students
        behav.add_state("good", action="suggest_badges_to_world",
                        args={"agent": "<valid_cmp>", "score": 1.0, "badge_type": "completed",
                              "badge_description": "Completed the Animal School #ImageClassification #AnimalPictures"})

        # Promoting students that passed to teacher role
        behav.add_transit("good", "promote", action="suggest_role_to_world",
                          args={"agent": "<valid_cmp>", "role": "teacher"})

        # Freeing students
        behav.add_transit("promote", "habilitate", action="send_disengage")

        # Wildcards used by the templates above
        behav.add_wildcards({"<learn_steps>": 40, "<eval_steps>": 30, "<cmp_thres>": 0.65})
        behav.apply_wildcards()

        # Adding default messages
        behav.generate_auto_messages()
        behav.show_marks_in_blocking_state_messages(True)
        behav.show_ticks_in_action_messages(True)
        behav.show_request_info_in_action_messages(True)

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: student
        from .student import WAgent as StudentAgent
        dummy_agent = StudentAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("student")

        # Plug the modern listening_to_teacher_new template at 'init' (its initial state is 'teacher_engaged')
        behav.add_transit("init", listening_json, action="engage",
                          args={"acceptable_role": "teacher"})

        # When the teacher will send the student back home
        behav.add_transit("teacher_engaged", "init", action="disengage")

        # Adding default messages
        behav.generate_auto_messages()
        behav.show_marks_in_blocking_state_messages(True)
        behav.show_ticks_in_action_messages(True)
        behav.show_request_info_in_action_messages(True)

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)
