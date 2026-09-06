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
        return "teacher" if is_world_master else "student"

    def create_behav_files(self):
        """Create role-behavior JSON files."""
        assert self.world_folder is not None
        sys.path.append(self.world_folder)

        # ROLE 1/2: teacher
        from .teacher import WAgent as WAgentTeacher
        dummy_agent = WAgentTeacher(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("teacher")
        behav.set_welcome_message("Welcome to our tutorial at **CoLLAs 2026**!\nYour role: **teacher**")

        behav.add_state("init", action="reset_status", blocking=False, msg="Waiting for students...")
        behav.add_state("in_class", blocking=False, msg="In class...")
        behav.add_state("ready_for_lecture", waiting_time=5.0, blocking=False, msg="Ready for lecture...")
        behav.add_state("lecture_in_progress", blocking=True, msg="Lecture in progress...")
        behav.add_state("ready_for_exam", waiting_time=5.0, blocking=False, msg="Ready for the exam session...")
        behav.add_state("exam_in_progress", blocking=True, msg="Exam in progress...")
        behav.add_state("ready_for_feedback", waiting_time=5.0, blocking=False, msg="Ready to send requests...")
        behav.add_state("feedback_time", blocking=True, msg="Waiting for feedback...")

        behav.add_transit("init", "in_class",
                          action="find_agents",
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

        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # ROLE 2/2: student
        from .student import WAgent as WAgentStudent
        dummy_agent = WAgentStudent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("student")
        behav.set_welcome_message("Welcome to our tutorial at CoLLAs 2026! Your role: **student**")

        behav.add_state("init", blocking=False, action="init")
        behav.add_state("teacher_found", blocking=True, msg="*Connected, waiting for teacher's approval...*")
        behav.add_state("in_class", blocking=False)
        behav.add_state("done_learning", blocking=False, msg="*Done following the lecture!*")
        behav.add_state("done_exam_or_feedback", blocking=False, msg="*Finished providing responses!*")
        behav.add_state("wait_to_recover", blocking=False, msg="*Recovering...*")

        behav.add_transit("init", "teacher_found",
                          action="connect_by_role",
                          args={"role": "teacher", "filter_fcn": "one_at_random"})
        behav.add_transit("teacher_found", "in_class",
                          action="connected",
                          args={"handshake_completed": True})
        behav.add_transit("teacher_found", "wait_to_recover", action="disconnected",
                          delay=3.0, teleport=True)
        behav.add_transit("wait_to_recover", "init", action="nop", delay=60, teleport=True)
        behav.add_transit("in_class", "in_class", action="print", args={}, ready=False)
        behav.add_transit("in_class", "done_learning", action="learn", args={},
                          timeout=max(WAgentTeacher.LECTURE_DELTA*1.5, Custom.DEFAULT_TIMEOUT),
                          ready=False)
        behav.add_transit("in_class", "done_exam_or_feedback", action="process", args={},
                          timeout=int(max(WAgentTeacher.EXAM_DELTA*1.5, WAgentTeacher.FEEDBACK_DELTA*1.5,
                                          Custom.DEFAULT_TIMEOUT)),
                          ready=False)
        behav.add_transit("in_class", "wait_to_recover", action="disconnected", teleport=True)
        behav.add_transit("done_learning", "in_class", action="nop", args={})
        behav.add_transit("done_exam_or_feedback", "in_class", action="nop", args={})

        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)
