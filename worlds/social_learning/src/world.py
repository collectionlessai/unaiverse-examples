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
        stats = WStats(is_world=True, db_path=f"{world_folder}/stats/world_stats.db", cache_window_hours=1.0)
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return "teacher"
            else:
                return "student"
        else:
            if 'tmp_role_preference' in profile.get_dynamic_profile():
                role_preference = profile.get_dynamic_profile()['tmp_role_preference']
                if role_preference == "student":
                    return "student"
                elif role_preference == "student_isolated":
                    return "student_isolated"
                else:
                    return "student"
            else:
                return "student"

    def create_behav_files(self):
        """Create role-behavior JSON files: if you manually create the JSON files, no need to implement this method."""

        # Creating a dummy agent to check actions
        import sys
        sys.path.append(self.world_folder)

        # Configuration
        student_learn_time = 30.0
        student_exam_time = 30.0

        # ROLE 1/3: teacher
        from .teacher import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_welcome_message("🍎 Welcome to the world of Social Learning, you joined as a teacher")
        behav.set_role("teacher")

        # Connecting to students and isolated students, ensuring that at least a student is found
        behav.add_transit("init",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors", "engage_by_role.json"),
                          action="nop", args={})
        behav.states['init'].set_blocking(False)
        behav.add_wildcards({"<roles_to_engage>": ["student", "student_isolated"]})

        # Setting up lectures; teaching and, afterward, evaluating students (repeated 3 times)
        behav.add_transit("engagement_complete",
                          os.path.join(self.world_folder, "..", "..", "..", "behaviors", "teach-eval-playlist.json"),
                          action="set_pref_streams",
                          args={"net_hashes": [f"<agent>:teach_{i}" for i in range(0, dummy_agent.get_num_rounds())]})
        behav.add_wildcards({"<learn_steps>": dummy_agent.get_teach_steps(),
                             "<eval_steps>": dummy_agent.get_eval_steps(),
                             "<cmp_thres>": 1.0})  # TODO put it to 0.5

        # Counting
        behav.add_state("engagement_complete", msg="🔔 Ready for the lecture")

        # Forcing shuffle of all the round-related datasets and unlabeled data
        behav.add_state("begin_teaching", action="shuffle_and_stop_streaming", msg="📗 Starting to teach")

        # Providing a badge to all the agents that were the best ones in a lecture
        behav.add_state("best_found", action="manage_best_of_class", msg="🏆 Found the best of class")

        # Stop streams at the end of the lecture/exam
        behav.add_state("student_finished_following", action="stop_streaming",
                        msg="📗 End of the lecture")
        behav.add_state("student_finished_exam", action="stop_streaming", msg="✏️ End of the exam")
        behav.add_state("compare_time", msg="✏️ Correcting exams")

        behav.add_state("searching", msg="🔍 Searching for students...")
        behav.add_state("connected", msg="🤝 Started to connect to one or more students",
                        action="clear_pending_requests")
        behav.add_state("can_engage", msg="✅ Connection confirmed by one or more students, ready to engage")
        behav.add_state("exam_in_progress", msg="✏️ Exam in progress")
        behav.add_state("best_not_found", msg="❌ The best of class was not found")
        behav.add_state("best_teaching", msg="📕 The best of class is now teaching")
        behav.add_state("wait_for_disengagement", msg="🔚 Waiting while students leave...")
        behav.add_state("connection_timeout", msg="⏰ Timeout!")

        # Telling the best student to teach and the other to listen to the best student
        behav.transitions["best_found"] = {}  # Clearing existing transitions, loaded from the template
        behav.add_transit("best_found", "best_teaching",
                          action="ask_best_to_gen_ask_others_to_learn")
        behav.add_transit("best_found", "change_lecture",  action="nop", args={})
        behav.add_transit("best_teaching", "best_teaching", action="done_gen")
        behav.add_transit("best_teaching", "best_teaching", action="done_learn")
        behav.add_transit("best_teaching", "change_lecture", action="all_asked_finished")
        behav.add_teleport("best_teaching", "change_lecture", action="nop",
                           args={"delay": "<others_learn_exam_timeout>"}, msg="⏰ Timeout!")
        behav.transitions["lecture_in_progress"]['student_finished_following'][1].set_msg("⏰ Timeout!")
        behav.transitions["exam_in_progress"]['student_finished_exam'][1].set_msg("⏰ Timeout!")
        behav.states["best_teaching"].set_blocking(False)

        # Last wildcard from the loaded machine
        behav.add_wildcards({"<learn_time>": student_learn_time})
        behav.add_wildcards({"<learn_timeout>": student_learn_time / 3.0})
        behav.add_wildcards({"<exam_time>": student_exam_time})
        behav.add_wildcards({"<exam_timeout>": student_exam_time / 2.0})
        behav.add_wildcards({"<others_learn_exam_timeout>": min(student_learn_time,
                                                                student_exam_time) * 0.33})

        # Providing a badge to all the agents that were the best of the world
        behav.add_state("finished_teaching")

        # Send disengagement and wait a bit before going ahead (where it will disconnect, making others remove this
        # agent from their pools and possibly discard the disengagement message)
        behav.add_transit("finished_teaching", "wait_for_disengagement",
                          action="send_disengagement", args={"send_disconnection_too": True})
        behav.add_state("wait_for_disengagement", waiting_time=3.0, blocking=True)

        # Back to the beginning
        behav.add_transit("wait_for_disengagement", "init", action="nop")

        # Applying wildcards
        behav.apply_wildcards()

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # ROLE 2/3: student
        from .student import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_welcome_message("🎓 Welcome to the world of Social Learning, you joined as a student")
        behav.set_role("student")

        # Getting engagement
        behav.add_transit("init", "teacher_engaged",
                          action="get_engagement",
                          args={"acceptable_role": "teacher"})
        behav.add_state("init", blocking=False,
                        action="clear_pending_requests", args={"preserve": "get_engagement"},
                        msg="⏳ Waiting for the next set of lectures to start")

        # Requests from the teacher
        behav.add_transit("teacher_engaged", "finished_learning", action="do_learn",
                          msg="📗 Following a lecture, learning...", total_time=student_learn_time,
                          timeout=student_learn_time / 3.0)
        behav.add_transit("teacher_engaged", "listening_to_best_student", action="do_subscribe")
        behav.add_transit("teacher_engaged", "teacher_engaged", action="do_gen")
        behav.add_state("teacher_engaged", blocking=False, msg="🔔 Ready for the lecture")
        behav.add_transit("finished_learning", "teacher_engaged", action="do_gen",
                          msg="✏️ Taking the exam...", total_time=student_exam_time,
                          timeout=student_exam_time / 2.0)
        behav.add_transit("listening_to_best_student", "teacher_engaged", action="do_learn",
                          msg="📕 Learning from the best student’s feedback...", total_time=student_learn_time,
                          timeout=min(student_learn_time, student_exam_time) * 0.33)
        behav.add_state("listening_to_best_student", blocking=False,
                        msg="👍 Ready to listen to the best student of the class")
        behav.add_global_teleport("init", action="get_disengagement")
        behav.add_global_teleport("init", action="disconnected")
        behav.add_global_teleport("init", action="nop", args={"delay": 30.0})

        # Saving to file
        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)

        # ROLE 3/3: student isolated (reusing the machine for role student)
        from .student_isolated import WAgent
        dummy_agent = WAgent(proc=None)
        behav.set_actionable(dummy_agent)
        behav.set_welcome_message("🎓 Welcome to the world of Social Learning, you joined as a student (isolated)")
        behav.set_role("student_isolated")
        behav.save(os.path.join(self.world_folder, 'student_isolated.json'), only_if_changed=dummy_agent)

    def _process_custom_stat(self, stat_name, value, peer_id, timestamp):
        # handle the special case of best_exam_err_history
        if stat_name == 'best_exam_err_history':
            # the world will store this stat as an ungrouped one, substituting its own peer_id
            # store the new value (this stat will be ungrouped in the world)
            world_peer_id = self.get_peer_ids()[1]
            self.stats.store_stat('best_exam_err_history', value, peer_id=world_peer_id, timestamp=timestamp)
            # retrieve peer role and node_id from the profile
            # _role = self.all_agents[peer_id].get_dynamic_profile()['connections']['role']
            # _role_without_flag = self.ROLE_STR_TO_BITS[_role] & ~(self.ROLE_WORLD_MASTER | self.ROLE_WORLD_AGENT)
            # _role_without_flag_str = self.ROLE_BITS_TO_STR[_role_without_flag]
            _role = self.all_agents[peer_id].get_dynamic_profile()['connections']['role'].split('~')[-1]
            self.stats.store_stat('best_student_role_history', _role, peer_id=world_peer_id, timestamp=timestamp)
            self.stats.store_stat('best_student_history', peer_id, peer_id=world_peer_id, timestamp=timestamp)
            
            # check if this is the new overall best and update it
            overall_best_err = self.stats.get_last_value('overall_best_exam_err')
            if overall_best_err == -1.0 or value < overall_best_err:
                # New overall best found
                self.stats.store_stat('overall_best_exam_err', value, peer_id=world_peer_id, timestamp=timestamp)
                self.stats.store_stat('overall_best_student', peer_id, peer_id=world_peer_id, timestamp=timestamp)
                self.stats.store_stat('overall_best_student_role', _role, peer_id=world_peer_id, timestamp=timestamp)
                self.deb(f"[WStats] New overall best exam error: {value} by {peer_id} ({_role})")
                
                # add the badge for the bast overall
                badge = {
                    'peer_id': peer_id,
                    'score': value,
                    'badge_type': "completed",
                    'badge_description': "World champion, MNIST classification #ImageClassification #MNIST",
                    'agent_token': self._node_conn.get_last_token(peer_id)
                    }
                self.add_badge(**badge)
            
            # the custom stat was successfully handled
            return True
        return False
