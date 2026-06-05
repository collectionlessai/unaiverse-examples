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
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

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
        teach_eval_json = os.path.join(behaviors_dir, "teach-playlist_eval-playlist.json")
        listening_json = os.path.join(behaviors_dir, "listening_to_teacher.json")

        # ROLE 1/2: teacher
        from .teacher import WAgent as TeacherAgent
        dummy_agent = TeacherAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("teacher")

        # Engage students via the modern engage_by_role template (chained at 'init')
        behav.add_transit("init", engage_by_role_json, action="nop", args={})
        behav.add_wildcards({"<roles_to_engage>": "student"})

        # Teach the 7-stream playlist (held-out squLfLa is reserved for the generalization test below),
        # 4 repetitions. The template uses `check_pref_stream("not_last_round" / "last_round")` to
        # restrict examinations to the LAST round only: cur 0-20 (rounds 1-3) are pure teaching iterations,
        # cur 21-27 (round 4 = last round) are per-entry exams. Net effect: each unique stream is taught
        # 3 times and exam-ed once.
        behav.add_transit("engagement_complete", teach_eval_json,
                          action="set_pref_streams",
                          args={"net_hashes": ["<agent>:smoHfHa", "<agent>:smoHfLa", "<agent>:smoLfHa",
                                               "<agent>:smoLfLa", "<agent>:squHfHa", "<agent>:squHfLa",
                                               "<agent>:squLfHa"], "repeat": 4})

        # Generalization test on the held-out `squLfLa` stream: ask each student to `process` 1000 steps
        # of it, then evaluate the produced output against the same stream's targets.
        behav.add_transit("finished_work", "hard_exam_in_progress", action="send",
                          args={"action_name": "process",
                                "streams": ["<agent>:squLfLa"],
                                "num_steps": 1000,
                                "wait_completion": True})
        behav.add_transit("hard_exam_in_progress", "eval_time_again", action="nop")
        behav.add_state("eval_time_again", action="evaluate",
                        args={"stream_hash": "<agent>:squLfLa", "how": "mse", "steps": 1000, "re_offset": True})
        behav.add_transit("eval_time_again", "very_good",
                          action="compare_eval", args={"cmp": "<=", "thres": 0.2})
        behav.add_transit("eval_time_again", "not_good", action="nop")

        # Wildcards used by the template
        behav.add_wildcards({"<learn_steps>": 1000, "<eval_steps>": 1000, "<cmp_thres>": 0.2})
        behav.apply_wildcards()

        assert behav.states["eval_time"].action is not None
        behav.states["eval_time"].action.args['re_offset'] = True
        behav.states["eval_time"].action.args_with_wildcards['re_offset'] = True

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
