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
from unaiverse.custom import Custom
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        """This method implements the criterion the world uses to assign a role to every joining agent."""
        return "teacher" if is_world_master else "student"  # Simple criterion: if world master, then 'teacher'

    def create_behav_files(self):
        """Create role-behavior JSON files."""
        assert self.world_folder is not None
        sys.path.append(self.world_folder)

        # [Teacher] Creating a dummy teacher agent and an empty Hybrid State Machine (HSM)
        from .teacher import WAgent as WAgentTeacher
        dummy_agent = WAgentTeacher(proc=None)
        behav = HybridStateMachine(dummy_agent)

        # [Teacher] Marking the HSM with the role and with the welcome message displayed when joining the world
        behav.set_role("teacher")
        behav.set_welcome_message("🎓 Welcome to our tutorial at CoLLAs 2026! Your role: teacher")

        # [Teacher] States
        behav.add_state("init", action="reset_status", blocking=False,
                        msg="🕐 Waiting for students to join the class...")  # Each state can be paired with a msg
        behav.add_state("in_class", waiting_time=3.0, blocking=False,  # Let's wait a little bit (waiting_time)
                        msg="🏫 In class, deciding what to do next...")
        behav.add_state("ready_for_lecture", waiting_time=8.0, blocking=False,
                        msg="📚 Lecture about to start...")
        behav.add_state("lecture_in_progress", blocking=True,  # Blocking: so it will allow to send data
                        msg="📚 Lecture in progress: streaming pictures and labels...")
        behav.add_state("ready_for_exam", waiting_time=8.0, blocking=False,
                        msg="📝 Exam session about to start...")
        behav.add_state("exam_in_progress", blocking=True, msg="📝 Exam in progress...")
        behav.add_state("ready_for_feedback", waiting_time=8.0, blocking=False,
                        msg="🙋 About to ask students for help...")
        behav.add_state("feedback_time", blocking=True,
                        msg="🙋 Waiting for feedback on unlabeled pictures...")

        # [Teacher] Transitions
        behav.add_transit("init", "in_class",
                          action="find_agents",  # This ('find_agents') is a method of the WAgent class in teacher.py
                          args={"role": "student", "handshake_completed": True})
        behav.add_transit("in_class", "ready_for_lecture",
                          action="give_next_lecture")
        behav.add_transit("ready_for_lecture", "lecture_in_progress",
                          action="teach")
        behav.add_transit("lecture_in_progress", "in_class",
                          action="lecture_finished")
        behav.add_transit("in_class", "ready_for_exam",
                          action="start_exam_session")
        behav.add_transit("ready_for_exam", "exam_in_progress",
                          action="hand_out_exam")
        behav.add_transit("exam_in_progress", "exam_in_progress",
                          action="on_data", args={"stream_group": "exam"})
        behav.add_transit("exam_in_progress", "in_class",
                          action="evaluate_results")
        behav.add_transit("in_class", "ready_for_feedback",
                          action="ask_for_feedback")
        behav.add_transit("ready_for_feedback", "feedback_time",
                          action="send_requests")
        behav.add_transit("feedback_time", "feedback_time",
                          action="on_data", args={"stream_group": "feedback"})
        behav.add_transit("feedback_time", "init",
                          action="augment_lectures")

        # [Teacher] Saving the just created HSM to a JSON file with the same name of the one hosting the class
        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # [Student] Creating a dummy teacher agent and an empty Hybrid State Machine (HSM)
        from .student import WAgent as WAgentStudent
        dummy_agent = WAgentStudent(proc=None)
        behav = HybridStateMachine(dummy_agent)

        # [Student] Marking the HSM with the role and with the welcome message displayed when joining the world
        behav.set_role("student")
        behav.set_welcome_message('🎓 **Lifelong Learning in Peer-to-Peer Communities of Human and AI Agents**\n\n'
                                  'Tutorial by Stefano Melacci, Tommaso Guidi, Christian Di Maio\n\n'
                                  '```uai\n\n'
                                  '{"v": 1, "type": "media", "src": "https://lifelong-ml.cc/images/logo.png", '
                                  '"mime": "image/png", '
                                  '"alt": "(Conference Logo: https://lifelong-ml.cc/images/logo.png)"}\n\n```')

        # [Student] States
        behav.add_state("init", waiting_time=3.0, blocking=False)
        behav.add_state("teacher_found", blocking=True, msg="🔎 *Connected, waiting for teacher's approval...*")
        behav.add_state("in_class", blocking=False)
        behav.add_state("done_learning", blocking=False)
        behav.add_state("done_exam_or_feedback", blocking=False)
        behav.add_state("wait_to_recover", blocking=False, msg="🔄 *Lost the teacher... trying again in a minute*")

        # [Teacher] Transitions
        behav.add_transit("init", "teacher_found",
                          action="connect_by_role",
                          args={"role": "teacher", "filter_fcn": "one_at_random"})
        behav.add_transit("teacher_found", "in_class",
                          action="connected",
                          args={"handshake_completed": True})
        behav.add_transit("teacher_found", "wait_to_recover", action="disconnected",
                          delay=5.0, teleport=True)   # Delay: the action will be available in this state after a while
        behav.add_transit("wait_to_recover", "init", action="nop", delay=60, teleport=True)
        behav.add_transit("in_class", "in_class", action="print", args={}, ready=False)
        behav.add_transit("in_class", "done_learning",
                          action="learn", args={},  # The 'learn' action is multistep (multi clock cycles)
                          timeout=max(WAgentTeacher.LECTURE_DELTA*1.5, Custom.DEFAULT_TIMEOUT),
                          ready=False)  # It is not ready: it is triggered by an interaction from another agent
        behav.add_transit("in_class", "done_exam_or_feedback", action="process", args={},
                          timeout=int(max(WAgentTeacher.EXAM_DELTA*1.5, WAgentTeacher.FEEDBACK_DELTA*1.5,
                                          Custom.DEFAULT_TIMEOUT)),
                          ready=False)
        behav.add_transit("in_class", "wait_to_recover", action="disconnected", teleport=True)
        behav.add_transit("done_learning", "in_class", action="nop", args={})
        behav.add_transit("done_exam_or_feedback", "in_class", action="nop", args={})

        # [Student] Saving the just created HSM to a JSON file with the same name of the one hosting the class
        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)
