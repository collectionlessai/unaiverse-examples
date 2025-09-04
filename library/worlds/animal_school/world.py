import os
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile
from unaiverse.library.worlds.animal_school.agent import WAgent, AnimalSchoolRoles
from unaiverse.streams import DataStream, ImageFileStream, LabelStream


class WWorld(World, AnimalSchoolRoles):
    
    # feasible roles
    ROLE_BITS_TO_STR = {**World.ROLE_BITS_TO_STR, **AnimalSchoolRoles.ROLE_BITS_TO_STR}
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
                                        self.ROLE_BITS_TO_STR[self.ROLE_STUDENT]: os.path.join(world_folder_name, 'behav_student.json')},
                         **kwargs)

        # adding streams
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'animals')

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
                return self.ROLE_TEACHER
            else:
                return self.ROLE_STUDENT
        else:
            return self.ROLE_STUDENT

    @staticmethod
    def __create_behav_files():
        path_of_this_file = os.path.dirname(os.path.abspath(__file__))
        dummy_agent = WAgent(proc=None)

        # ROLE 1/2: teacher
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_TEACHER])
        
        # preparing exam
        behav.add_transit("init", "exam_prepared", action="record",
                          args={"net_hash": "<world>:all", "samples": "<eval_steps>"})

        # engaging students, teaching and, afterward, evaluating students
        behav.add_transit("exam_prepared",
                          os.path.join(path_of_this_file, "..", "..",
                                       "behaviors", "teach-playlist_eval-recorded1.json"),
                          action="set_pref_streams",
                          args={"net_hashes": ["<world>:albatross", "<world>:cheetah", "<world>:giraffe"]})

        # promoting students that were positively evaluated
        behav.add_transit("good", "promote", action="suggest_role_to_world",
                          args={"agent": "<valid_cmp>",
                                "role": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_TEACHER]})

        # providing a badge to all the agents that finished the school with a positive mark
        behav.add_state("good", action="suggest_badges_to_world",
                        args={"agent": "<valid_cmp>", "score": 1.0, "badge_type": "completed",
                              "badge_description": "Completed the Animal School #ImageClassification #AnimalPictures"})

        # freeing students
        behav.add_transit("promote", "habilitate", action="send_disengagement")

        # wildcards present in the template
        behav.add_wildcards({"<role_to_connect>": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_STUDENT],
                             "<learn_steps>": 40, "<eval_steps>": 30, "<cmp_thres>": 0.45})

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_teacher.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_teacher.pdf'))

        # ROLE 2/2: student
        behav = HybridStateMachine(dummy_agent)
        behav.set_role(WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_STUDENT])

        # generic behaviour of a student who listens to the requests from the teacher
        behav.add_transit("init",
                          os.path.join(path_of_this_file, "..", "..", "behaviors", "listening_to_teacher.json"),
                          action="get_engagement",
                          args={"acceptable_role": WWorld.ROLE_BITS_TO_STR[WWorld.ROLE_TEACHER]})

        # when the teacher will send the student back home
        behav.add_transit("teacher_engaged", "init", action="get_disengagement")

        # saving to file
        if behav.save(os.path.join(path_of_this_file, 'behav_student.json'), only_if_changed=dummy_agent):
            os.makedirs(os.path.join(path_of_this_file, 'pdf'), exist_ok=True)
            behav.save_pdf(os.path.join(path_of_this_file, 'pdf', 'behav_student.pdf'))
