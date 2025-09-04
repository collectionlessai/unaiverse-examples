"""
 █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
 ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░ 
 ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████   
 ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█   
 ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
 ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
  ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░ 

~ Registration/Login: https://unaiverse.io
~ Code Repositories:  https://github.com/collectionlessai/
~ Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi

A Collectionless AI Project (https://collectionless.ai)
"""
import os
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from agent import WAgent, SocialLearningRoles
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World, SocialLearningRoles):

    # feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **SocialLearningRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):

        # dynamically re-create the behaviour files (not formally needed, just for easier develop)
        WWorld.__create_behav_files()

        # guess the name of the folder containing this world
        world_folder_name = os.path.basename(os.path.dirname(__file__))

        # building world
        super().__init__(*args,
                         agent_actions=os.path.join(world_folder_name, 'agent.py'),
                         role_to_behav={self.ROLE_BITS_TO_STR[self.ROLE_TEACHER]: os.path.join(world_folder_name, 'behav_teacher.json'),
                                        self.ROLE_BITS_TO_STR[self.ROLE_STUDENT]: os.path.join(world_folder_name, 'behav_student.json'),
                                        self.ROLE_BITS_TO_STR[self.ROLE_STUDENT_ISOLATED]: os.path.join(world_folder_name, 'behav_student_isolated.json')},
                         **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return self.ROLE_TEACHER
            else:
                return self.ROLE_STUDENT
        else:
            if 'tmp_role_preference' in profile.get_dynamic_profile():
                role_preference = profile.get_dynamic_profile()['tmp_role_preference']
                if role_preference == self.ROLE_STUDENT:
                    return self.ROLE_STUDENT
                elif role_preference == self.ROLE_STUDENT_ISOLATED:
                    return self.ROLE_STUDENT_ISOLATED
                else:
                    return self.ROLE_STUDENT
            else:
                return self.ROLE_STUDENT

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/3: teacher
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_TEACHER])

        # connecting to students and isolated students, ensuring that at least a student is found
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "engage_by_role.json"),
                          action="nop", args={})
        behav.states['init'].set_blocking(False)
        behav.add_wildcards({"<roles_to_engage>": [WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_STUDENT],
                                                   WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_STUDENT_ISOLATED]]})

        # setting up lectures; teaching and, afterward, evaluating students (repeated 3 times)
        behav.add_transit("engagement_complete",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "teach-eval-playlist.json"),
                          action="set_pref_streams",
                          args={"net_hashes": [f"<agent>:teach_{i}" for i in range(0, dummy_agent.get_num_rounds())]})
        behav.add_wildcards({"<learn_steps>": dummy_agent.get_teach_steps(),
                             "<eval_steps>": dummy_agent.get_eval_steps(),
                             "<cmp_thres>": 0.5})

        # counting
        behav.add_state("engagement_complete", action="count_students")

        # forcing shuffle of all the round-related datasets and unlabeled data
        behav.add_state("begin_teaching", action="shuffle_and_stop_streaming")

        # providing a badge to all the agents that were the best ones in a lecture
        behav.add_state("best_found", action="manage_best_of_class")

        # stop streams at the end of the lecture/exam
        behav.add_state("student_finished_following", action="stop_streaming")
        behav.add_state("student_finished_exam", action="stop_streaming")

        # telling the best student to teach and the other to listen to the best student
        behav.transitions["best_found"] = {}  # clearing existing transitions, loaded from the template
        behav.add_transit("best_found", "best_teaching",
                          action="ask_best_to_gen_ask_others_to_learn")
        behav.add_transit("best_found", "change_lecture",  action="nop", args={})
        behav.add_transit("best_teaching", "best_teaching", action="done_gen")
        behav.add_transit("best_teaching", "best_teaching", action="done_learn")
        behav.add_transit("best_teaching", "change_lecture", action="all_asked_finished")
        behav.add_transit("best_teaching", "change_lecture", action="nop",
                          args={"delay": "<learn_exam_timeout>"})
        behav.states["best_teaching"].set_blocking(False)

        # last wildcard from the loaded machine
        behav.add_wildcards({"<learn_exam_timeout>": 15.0})

        # providing a badge to all the agents that were the best of the world
        behav.add_state("finished_teaching", action="manage_best_of_the_bests")

        # send disengagement and wait a bit before going ahead (where it will disconnect, making others remove this
        # agent from their pools and possibly discard the disengagement message)
        behav.add_transit("finished_teaching", "wait_for_disengagement",
                          action="send_disengagement", args={"send_disconnection_too": True})
        behav.add_state("wait_for_disengagement", waiting_time=3.0, blocking=True)

        # back to the beginning
        behav.add_transit("wait_for_disengagement", "init", action="nop")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_teacher.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_teacher.pdf'))

        # ROLE 2/3 and 3/3 (same): student and student isolated
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_STUDENT])

        # getting engagement
        behav.add_transit("init", "teacher_engaged",
                          action="get_engagement",
                          args={"acceptable_role": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_TEACHER]})
        behav.add_state("init", blocking=False,
                        msg="⏳ Waiting for the next set of lectures to start")

        # requests from the teacher
        behav.add_transit("teacher_engaged", "finished_learning", action="do_learn",
                          msg="📗 Following a lecture, learning...")
        behav.add_transit("teacher_engaged", "listening_to_best_student", action="do_subscribe")
        behav.add_transit("teacher_engaged", "teacher_engaged", action="do_gen")
        behav.add_transit("teacher_engaged", "init", action="disconnected")
        behav.add_transit("teacher_engaged", "init", action="get_disengagement")
        behav.add_transit("teacher_engaged", "init", action="nop", args={"delay": 30.0})
        behav.add_state("teacher_engaged", blocking=False, msg="🔔 Ready for the lecture")
        behav.add_transit("finished_learning", "teacher_engaged", action="do_gen",
                          msg="✏️ Taking the exam...")
        behav.add_transit("finished_learning", "init", action="disconnected")
        behav.add_transit("finished_learning", "init", action="get_disengagement")
        behav.add_transit("finished_learning", "init", action="nop", args={"delay": 30.0})
        behav.add_transit("listening_to_best_student", "teacher_engaged", action="do_learn",
                          msg="📕 Learning from the best student’s feedback...")
        behav.add_transit("listening_to_best_student", "init", action="disconnected")
        behav.add_transit("listening_to_best_student", "init", action="get_disengagement")
        behav.add_transit("listening_to_best_student", "init", action="nop", args={"delay": 30.0})
        behav.add_state("listening_to_best_student", blocking=False,
                        msg="👍 Ready to listen to the best student of the class")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_student.json'), only_if_changed=dummy_agent):
            behav.save(os.path.join(path_of_this_file, 'behav_student_isolated.json'))
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_student.pdf'))
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_student_isolated.pdf'))
