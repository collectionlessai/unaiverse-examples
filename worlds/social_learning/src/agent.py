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
import math
import json
import copy
import torch
import random
import numpy as np
import importlib.util
from unaiverse.agent import Agent
from torch.utils.data import Subset
from unaiverse.dataprops import DataProps
from torchvision import datasets, transforms
from unaiverse.streams import DataStream, Dataset


class SocialLearningRoles:

    # Role bitmasks
    ROLE_TEACHER = 1 << 2
    ROLE_STUDENT = 1 << 3
    ROLE_STUDENT_ISOLATED = 1 << 4

    # Feasible roles
    ROLE_BITS_TO_STR = {

        # The base roles will be inherited from AgentBasics later
        ROLE_TEACHER: "teacher",
        ROLE_STUDENT: "student",
        ROLE_STUDENT_ISOLATED: "student_isolated",
    }


class WAgent(Agent, SocialLearningRoles):

    # Feasible roles
    ROLE_BITS_TO_STR = {**Agent.ROLE_BITS_TO_STR, **SocialLearningRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rounds = 4
        self._eval_per_class = 20
        self._teach_per_class = 50
        self._unlabeled_per_class = 100
        self._batch_size = 32
        self._test_teach_and_unlabeled_data_streams = []
        self._seed = 1234
        self._agent_folder_name = None
        self._stats = {"cur_best_result": -1,
                       "tot_best_result": -1,
                       "cur_best_result_role": None,
                       "tot_best_result_role": None,
                       "cur_best_student": (None, None),
                       "tot_best_student": (None, None),
                       "cur_num_students": 0,
                       "cur_num_students_isolated": 0,
                       "tot_num_students": 0,
                       "tot_num_students_isolated": 0}

    def get_num_rounds(self):
        return self._rounds

    def get_teach_steps(self):
        return math.ceil(float(self._teach_per_class * 10.) / float(self._batch_size))

    def get_eval_steps(self):
        return math.ceil(float(self._eval_per_class * 10.) / float(self._batch_size))

    def get_unlabeled_steps(self):
        return math.ceil(float(self._unlabeled_per_class * 10.) / float(self._batch_size))

    def accept_new_role(self, role: int, default_behav: str | None):
        super().accept_new_role(role, default_behav)

        if self.get_current_role(return_int=True) == self.ROLE_TEACHER:

            # Guess the name of the folder containing this the agent file
            spec = importlib.util.find_spec("unaiverse.worlds.social_learning.agent")
            if spec is None or spec.origin is None:
                raise ImportError("Module unaiverse.worlds.social_learning.agent was not found")
            self._agent_folder_name = os.path.dirname(os.path.abspath(spec.origin))

            # Loading stats
            if not os.path.exists("stats.json"):
                self.out(f"Creating new stats file stats.json...")
                with open("stats.json", "w") as f:
                    json.dump(self._stats, f, indent=4)
            else:
                self.out("Loading stats from stats.json...")
                with open("stats.json") as f:
                    self._stats = json.load(f)
                    for k, v in self._stats.items():
                        if k.startswith("cur_") or k.startswith("tot_"):
                            try:
                                self._stats[k] = float(v)
                            except (ValueError, TypeError):
                                self._stats[k] = v
                self.out(f"Loaded stats:\n{self._stats}")

            # Getting MNIST data
            mnist_transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
            ])
            mnist_train = datasets.MNIST(root=os.path.join(self._agent_folder_name, "mnist_data"), train=True,
                                         download=True,
                                         transform=mnist_transform)
            mnist_test = datasets.MNIST(root=os.path.join(self._agent_folder_name, "mnist_data"), train=False,
                                        download=True,
                                        transform=mnist_transform)

            # Preparing dataset that will be streamed by the teacher
            def subsample(dataset, n_per_class, c, grp=0, offset=0):
                targets = dataset.targets.cpu().numpy()
                indices = []
                for cls in range(c):
                    cls_indices = np.where(targets == cls)[0]
                    start = offset + grp * n_per_class
                    end = offset + start + n_per_class
                    cls_indices = cls_indices[start:end]
                    indices.extend(cls_indices.tolist())
                random.shuffle(indices)
                return Subset(dataset, indices)

            eval_set = subsample(mnist_test, n_per_class=self._eval_per_class, c=10, grp=0)
            teach_sets = []

            for n in range(0, self._rounds):
                teach_sets.append(subsample(mnist_train, n_per_class=self._teach_per_class, c=10, grp=n))
            unlabeled_set = subsample(mnist_train, n_per_class=self._unlabeled_per_class, c=10,
                                      grp=0, offset=self._rounds * self._teach_per_class)

            # Adding streams
            s = self.add_streams([DataStream.create(group="eval", name="images", public=False,
                                                    stream=Dataset(eval_set, shape=(None, 1, 28, 28), index=0,
                                                                   batch_size=self._batch_size)),
                                  DataStream.create(group="eval", name="labels", public=False,
                                                    stream=Dataset(eval_set, shape=(None,), index=1,
                                                               batch_size=self._batch_size))])
            self._test_teach_and_unlabeled_data_streams += s

            for n in range(0, self._rounds):
                s = self.add_streams([DataStream.create(group=f"teach_{n}", name="images", public=False,
                                                        stream=Dataset(teach_sets[n], shape=(None, 1, 28, 28), index=0,
                                                                       batch_size=self._batch_size)),
                                      DataStream.create(group=f"teach_{n}", name="labels", public=False,
                                                        stream=Dataset(teach_sets[n], shape=(None,), index=1,
                                                                       batch_size=self._batch_size))])
                self._test_teach_and_unlabeled_data_streams += s

            s = self.add_streams([DataStream.create(group="unlabeled", name="images", public=False, pubsub=False,
                                                    stream=Dataset(unlabeled_set, shape=(None, 1, 28, 28), index=0,
                                                                   batch_size=10))])
            self._test_teach_and_unlabeled_data_streams += s

            # Initially de-activating pub-sub streams
            for stream_dict in self._test_teach_and_unlabeled_data_streams:
                for stream_obj in stream_dict.values():
                    stream_obj.disable()

        elif self.get_current_role(return_int=True) == self.ROLE_STUDENT:
            self.add_streams([DataStream(props=DataProps(group="best_student_stream", name="images", public=False,
                                                         data_type="tensor",
                                                         data_desc="Batched images if this is the best student",
                                                         tensor_shape=(None, 1, 28, 28),
                                                         tensor_dtype=torch.float32)),
                              DataStream(props=DataProps(group="best_student_stream", name="labels", public=False,
                                                         data_type="tensor",
                                                         data_desc="Batched class-indices if this is the best student",
                                                         tensor_shape=(None,),
                                                         tensor_dtype=torch.long))])

        elif self.get_current_role(return_int=True) == self.ROLE_STUDENT_ISOLATED:
            pass

        self.update_streams_in_profile()

    def ask_best_to_gen_ask_others_to_learn(self):
        if self._valid_cmp_agents is None or len(self._valid_cmp_agents) == 0:
            self.err("There is no best student to ask for the next lecture")
            return False

        self.find_agents(self.ROLE_BITS_TO_STR[self.ROLE_STUDENT])
        all_students = copy.deepcopy(self._engaged_agents)
        not_isolated_students = copy.deepcopy(self._found_agents)
        _, teacher = self.get_peer_ids()
        best_student = next(iter(self._valid_cmp_agents))  # This set has only 1 element
        other_not_isolated_students = not_isolated_students - {best_student}

        # Considering not-isolated students (different from the best one)
        self._engaged_agents = other_not_isolated_students

        # Telling them to listen to what the best student streams
        net_hash_to_stream_dict = self.find_streams(best_student, "best_student_stream")
        best_student_stream_hash = None
        for net_hash in net_hash_to_stream_dict.keys():
            best_student_stream_hash = net_hash
            break

        # Storing the list of agents who were asked multiple things
        agents_who_were_asked = set()

        if not self.ask_subscribe(stream_hashes=[best_student_stream_hash]):
            self.err("Unable to tell students to listen to what the best student is going to say")
            self._engaged_agents = all_students
            return False

        # Remembering who we asked
        agents_who_were_asked |= self._agents_who_were_asked

        # Asking them to learn from the best student
        if self.ask_learn(u_hashes=[f"{best_student}:best_student_stream"],
                          yhat_hashes=[f"{best_student}:best_student_stream"],
                          samples=self.get_unlabeled_steps(),
                          timeout=30.0):

            # Remembering who we asked
            agents_who_were_asked |= self._agents_who_were_asked

            # Getting the UUID of the request
            ref_uuid = self._last_ref_uuid

            # Asking the best student to label the data
            if not self.ask_gen(best_student,
                                u_hashes=[f"{teacher}:unlabeled"],
                                samples=self.get_unlabeled_steps(),
                                timeout=30.0,
                                ask_uuid=ref_uuid):
                self.err("Unable to ask the best student to for the next lecture")
                self._engaged_agents = all_students
                return False
            else:

                # From the teacher's perspective: setting the UUID of the pubsub that the best student will send
                net_hash_to_stream_dict = self.find_streams(best_student, "best_student_stream")
                for _, stream_dict in net_hash_to_stream_dict.items():
                    for name, stream_obj in stream_dict.items():

                        # Forcing UUID
                        stream_obj.set_uuid(None, expected=True)
                        stream_obj.set_uuid(ref_uuid, expected=False)

                # Remembering who we asked
                agents_who_were_asked |= self._agents_who_were_asked

                # Overwriting the internal set of asked peers with the merged one
                self._agents_who_were_asked = agents_who_were_asked

                self._engaged_agents = all_students
                return True
        else:
            self.err("Unable to ask the other not-isolated student to learn from the best student")
            self._engaged_agents = all_students
            return False

    def do_gen(self, u_hashes: list[str] | None = None,
               samples: int = 100, time: float = -1., timeout: float = -1.,
               _requester: str | list | None = None, _request_time: float = -1., _request_uuid: str | None = None,
               _completed: bool = False):

        # Generic generation request
        if not super().do_gen(u_hashes, samples, time, timeout, _requester, _request_time, _request_uuid, _completed):
            return False

        # If the teacher asked to label its unlabeled data, then load the data and predictions in the apposite stream
        if len(u_hashes) == 1 and u_hashes[0].endswith(":unlabeled") and len(self.known_streams[u_hashes[0]]) == 1:

            # Getting the stream of the images coming from the teacher and of the labels predicted by my processor
            image_stream_obj = next(iter(self.known_streams[u_hashes[0]].values()))  # This has only one data stream
            prediction_stream_obj = None
            for net_hash, stream_dict in self.proc_streams.items():
                for name, stream_obj in stream_dict.items():
                    if stream_obj.props.is_tensor():
                        prediction_stream_obj = stream_obj
                        break

            # Loading data to the pubsub stream
            _, best_student = self.get_peer_ids()
            net_hash_to_stream_dict = self.find_streams(best_student, "best_student_stream")
            for _, stream_dict in net_hash_to_stream_dict.items():
                for name, stream_obj in stream_dict.items():

                    # Forcing UUID
                    stream_obj.set_uuid(None, expected=True)
                    stream_obj.set_uuid(_request_uuid, expected=False)

                    # Setting up the stream data
                    if name == "images":
                        stream_obj.set(image_stream_obj.get("do_gen"))  # Streaming image
                    elif name == "labels":
                        stream_obj.set(prediction_stream_obj.get("do_gen"))  # Streaming decision
                    else:
                        raise ValueError(f"Unexpected stream name in the best_student_stream group: {name}")
                break
        elif len(u_hashes) == 1 and u_hashes[0].endswith(":eval"):
            pass
        else:
            self.err("Expected only one stream hash to be provided as input, with name ending in 'eval' or "
                     "'unlabeled'")
            return False
        return True

    def shuffle_and_stop_streaming(self):
        self._seed += 1
        for stream_dict in self._test_teach_and_unlabeled_data_streams:
            for stream_obj in stream_dict.values():
                stream_obj.shuffle_buffer(seed=self._seed)

        self.stop_streaming()

    def stop_streaming(self):
        for stream_dict in self._test_teach_and_unlabeled_data_streams:
            for stream_obj in stream_dict.values():
                stream_obj.disable()

    def count_students(self):
        self.find_agents(self.ROLE_BITS_TO_STR[self.ROLE_STUDENT])
        self._stats["cur_num_students"] = len(self._found_agents)
        self._stats["tot_num_students"] += self._stats["cur_num_students"]
        self.find_agents(self.ROLE_BITS_TO_STR[self.ROLE_STUDENT_ISOLATED])
        self._stats["cur_num_students_isolated"] = len(self._found_agents)
        self._stats["tot_num_students_isolated"] += self._stats["cur_num_students_isolated"]

        self.out(f"Saving to stats.json...")
        with open("stats.json", "w") as f:
            json.dump(self._stats, f, indent=4)

    def manage_best_of_class(self):
        if self.get_current_role(return_int=True) == self.ROLE_TEACHER:
            self.out(f"Managing the best of this class...")
            if len(self._valid_cmp_agents) > 0:
                best_student = next(iter(self._valid_cmp_agents))  # This has length 1
                best_student_name = self.all_agents[best_student].get_static_profile()['node_name']
                best_student_role = self.ROLE_BITS_TO_STR[self._node_conn.get_role(best_student)]

                badge_type = "intermediate"
                badge_description = "Best student of a class, MNIST classification #ImageClassification #MNIST"
                best_student_result = self._eval_results[best_student]

                if best_student_result >= 0:
                    self.out(f"The best student is {best_student} with this result: {best_student_result})")

                    self._stats["cur_best_result"] = best_student_result
                    self._stats["cur_best_result_role"] = best_student_role
                    self._stats["cur_best_student"] = (best_student_name, best_student)

                    self.out(f"Saving to stats.json...")
                    with open("stats.json", "w") as f:
                        json.dump(self._stats, f, indent=4)
                    return super().suggest_badges_to_world(agent=best_student, score=best_student_result,
                                                           badge_type=badge_type,
                                                           badge_description=badge_description)
                else:
                    return True
            else:
                return True
        else:
            return True

    def manage_best_of_the_bests(self):
        if self.get_current_role(return_int=True) == self.ROLE_TEACHER:
            self.out(f"Managing the best of the bests, if any...")
            if len(self._valid_cmp_agents) > 0:
                best_student_name, best_student = self._stats["cur_best_student"]
                best_student_result = self._stats["cur_best_result"]
                best_student_role = self._stats["cur_best_result_role"]

                if (best_student_result < 0. or
                        (best_student_result > self._stats["tot_best_result"] >= 0)):
                    self.out("The best of best results was not improved")
                    return True
                else:
                    self.out(f"New best of best result by {best_student}, with role {best_student_role}! "
                             f"Result: {best_student_result}")

                    badge_type = "completed"
                    badge_description = "World champion, MNIST classification #ImageClassification #MNIST"

                    self._stats["tot_best_result"] = best_student_result
                    self._stats["tot_best_result_role"] = best_student_role
                    self._stats["tot_best_student"] = (best_student_name, best_student)

                    self.out(f"Saving to stats.json...")
                    with open("stats.json", "w") as f:
                        json.dump(self._stats, f, indent=4)
                    return super().suggest_badges_to_world(agent=best_student, score=best_student_result,
                                                           badge_type=badge_type,
                                                           badge_description=badge_description)
            else:
                return True
        else:
            return True
