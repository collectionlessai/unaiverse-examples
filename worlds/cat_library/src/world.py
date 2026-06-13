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
from unaiverse.custom import Custom
from unaiverse.hsm import HybridStateMachine
from unaiverse.streams import Stream, TokensStream
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

        # Adding streams (same as the original cat_library world)
        data_path = os.path.join(str(self.world_folder), '..', '..', '..', 'data', 'cats', 'stream_of_words.csv')
        self.add_stream(Stream.create(name="cats", public=False,
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
        """Create role-behavior JSON files."""
        import sys
        assert self.world_folder
        sys.path.append(self.world_folder)

        # Behavior templates
        behaviors_dir = os.path.join(self.world_folder, "..", "..", "..", "behaviors")
        engage_by_role_json = os.path.join(behaviors_dir, "engage_by_role.json")
        teach_eval_json = os.path.join(behaviors_dir, "teach-playlist_eval-recorded1.json")
        listening_json = os.path.join(behaviors_dir, "listening_to_teacher.json")

        # ROLE 1/2: teacher
        from .teacher import WAgent as TeacherAgent
        dummy_agent = TeacherAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("teacher")

        # Snapshot the world's `cats` token stream into a teacher-owned BufferedStream
        # (`recorded1`).
        behav.add_transit("init", "book_prepared", action="record",
                          args={"streams": ["<world>:cats"],
                                "num_steps": "<eval_steps>",
                                "record_uuid": None}, avoid_changing_ready=True)

        # Engage students via the modern engage_by_role template (chained at 'book_prepared')
        behav.add_transit("book_prepared", engage_by_role_json, action="nop", args={})
        behav.add_wildcards({"<roles_to_engage>": "student"})

        # The exam dataset is the same recorded1 (single-class library setup)
        behav.add_wildcards({"<exam_data_ref>": Custom.AGENT_WILDCARD + ":recorded1"})

        # Teach `recorded1` repeated 50 times (the cat-library playlist), then exam against it.
        behav.add_transit("engagement_complete", teach_eval_json,
                          action="set_pref_streams",
                          args={"net_hashes": [Custom.AGENT_WILDCARD + ":recorded1"], "repeat": 50})

        # Wildcards used by the template (single-class: learn_steps == eval_steps == 998)
        behav.add_wildcards({"<learn_steps>": 998, "<eval_steps>": 998, "<cmp_thres>": 0.2})
        behav.add_wildcards({"<learn_time>": 120})
        behav.add_wildcards({"<exam_time>": 120})
        behav.apply_wildcards()

        # Data tags are not reliable at evaluation time for the text stream: force the tag of the
        # first compared pair to be the same (same trick as the original cat_library).
        assert behav.states["eval_time"].action is not None
        behav.states["eval_time"].action.args['re_offset'] = True
        behav.states["eval_time"].action.args_with_wildcards['re_offset'] = True
        behav.states["eval_time"].waiting_time = 3  # Wait to ensure all the data is received

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
