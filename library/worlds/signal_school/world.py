import os
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.library.worlds.signal_school.agent import WAgent, SignalSchoolRoles


class WWorld(World, SignalSchoolRoles):
    
    # feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **SignalSchoolRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):

        # dynamically re-create the behaviour files (not formally needed, just for easier develop)
        WWorld.__create_behav_files()

        # guess the name of the folder containing this world
        world_folder_name = os.path.basename(os.path.dirname(__file__))

        # building world
        super().__init__(*args,
                         agent_actions=os.path.join(world_folder_name, 'agent.py'),
                         role_to_behav={WAgent.ROLE_BITS_TO_STR[WAgent.ROLE_TEACHER]: os.path.join(world_folder_name, 'behav_teacher.json'),
                                        WAgent.ROLE_BITS_TO_STR[WAgent.ROLE_STUDENT]: os.path.join(world_folder_name, 'behav_student.json')},
                         **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            if len(self.world_masters) <= 1:
                return WAgent.ROLE_TEACHER
            else:
                return WAgent.ROLE_STUDENT
        else:
            return WAgent.ROLE_STUDENT

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: teacher
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_TEACHER])

        # engaging students, teaching and, afterward, evaluating students
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors",
                                       "teach-playlist_eval-playlist-lastrep_looped.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<agent>:smoHfHa", "<agent>:smoHfLa", "<agent>:smoLfHa",
                                               "<agent>:smoLfLa", "<agent>:squHfHa", "<agent>:squHfLa",
                                               "<agent>:squLfHa"], "repeat": 3 + 1})

        # testing generalization
        behav.add_transit("finished_work", "hard_exam_in_progress", action="ask_gen",
                          args={"u_hashes": ["<agent>:squLfLa"], "samples": 1000, "timeout": 5.0})
        behav.add_transit("hard_exam_in_progress", "eval_time_again", action="done_gen")
        behav.add_state("eval_time_again", action="evaluate",
                        args={"stream_hash": "<agent>:squLfLa", "how": "mse", "steps": 1000})
        behav.add_transit("eval_time_again", "very_good",
                          action="compare_eval", args={"cmp": "<=", "thres": 0.2})
        behav.add_transit("eval_time_again", "not_good", action="nop")

        # wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_STUDENT],
                             "<learn_steps>": 1000, "<eval_steps>": 1000, "<cmp_thres>": 0.2})

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_teacher.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_teacher.pdf'))

        # ROLE 2/2: student
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(dummy_agent.ROLE_BITS_TO_STR[WAgent.ROLE_STUDENT])

        # generic behaviour of a student who listens to the requests from the teacher
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "listening_to_teacher.json"),
                          action="get_engagement",
                          args={"acceptable_role": dummy_agent.ROLE_BITS_TO_STR[dummy_agent.ROLE_TEACHER]})

        # when the teacher will send the student back home
        behav.add_transit("teacher_engaged", "init", action="get_disengagement")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_student.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_student.pdf'))
