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
import copy
import random
import numpy as np
from torch.utils.data import Subset
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from torchvision import datasets, transforms
from unaiverse.streams import Stream, Dataset
from unaiverse.utils.misc import prepare_app_dir
from unaiverse.interaction import Interaction, CompletionReason


class WAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rounds = 2
        self._eval_per_class = 20
        self._teach_per_class = 50
        self._unlabeled_per_class = 100
        self._batch_size = 32
        self._round_datasets = []  # All dataset streams that get shuffled per round (eval + teach_n + unlabeled)
        self._seed = 1234
        self._agent_folder_name = os.path.join(prepare_app_dir(), "social_learning")

        # Peers asked by social_round still owing a completion (callback driven by on_asked_done;
        # gated by all_asks_done). teach_round and exam_round are gone — the HSM uses
        # `send(..., wait_completion=True)` directly in the teach-eval-playlist.json template.
        self._pending_asks = set()

        os.makedirs(self._agent_folder_name, exist_ok=True)

    def get_num_rounds(self):
        return self._rounds

    def get_teach_steps(self):
        return math.ceil(float(self._teach_per_class * 10.) / float(self._batch_size))

    def get_eval_steps(self):
        return math.ceil(float(self._eval_per_class * 10.) / float(self._batch_size))

    def get_unlabeled_steps(self):
        return math.ceil(float(self._unlabeled_per_class * 10.) / float(self._batch_size))

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

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
                end = start + n_per_class
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
        s = self.add_streams([Stream.create(group="eval", name="images", public=False,
                                            stream=Dataset(eval_set, shape=(None, 1, 28, 28), index=0,
                                                           batch_size=self._batch_size)),
                              Stream.create(group="eval", name="labels", public=False,
                                            stream=Dataset(eval_set, shape=(None,), index=1,
                                                           batch_size=self._batch_size))])
        self._round_datasets += s

        for n in range(0, self._rounds):
            s = self.add_streams([Stream.create(group=f"teach_{n}", name="images", public=False,
                                                stream=Dataset(teach_sets[n], shape=(None, 1, 28, 28), index=0,
                                                               batch_size=self._batch_size)),
                                  Stream.create(group=f"teach_{n}", name="labels", public=False,
                                                stream=Dataset(teach_sets[n], shape=(None,), index=1,
                                                               batch_size=self._batch_size))])
            self._round_datasets += s

        s = self.add_streams([Stream.create(group="unlabeled", name="images", public=False, pubsub=False,
                                            stream=Dataset(unlabeled_set, shape=(None, 1, 28, 28), index=0,
                                                           batch_size=self._batch_size))])
        self._round_datasets += s

        # The added streams must appear in the profile
        self.update_streams_in_profile()

    @action
    async def social_round(self) -> bool:
        """The best student labels the teacher's unlabeled data while the other (non-isolated) students learn
        from it. The other students learn via the dedicated 'learn_from_student' action. The best student labels
        the unlabeled data via 'teach' and publishes under the other students' learn UUID (relay_uuid).
        """
        if self._valid_cmp_agents is None or len(self._valid_cmp_agents) == 0:
            log.error("There is no best student to ask for the next lecture")
            return False

        await self.find_agents("student", handshake_completed=True)
        all_students = copy.deepcopy(self._engaged_agents)
        not_isolated_students = copy.deepcopy(self._found_agents)
        teacher = self.get_peer_id()
        best_student = next(iter(self._valid_cmp_agents))  # This set has only 1 element
        other_not_isolated_students = not_isolated_students - {best_student}

        log.user("===================== Best student and Other Not Isolated Students =========================")
        log.user(f"- Best Student: {best_student}")
        log.user(f"- Other Not Isolated Students: {other_not_isolated_students}")
        log.user("============================================================================================")

        if other_not_isolated_students is None or len(other_not_isolated_students) == 0:
            return False

        self._pending_asks = set()

        # Asking the other (non-isolated) students to learn from the best student's stream (passed as a kwarg
        # net hash, bound at action time -> no registration-time stream resolution/rejection; a dedicated
        # action name so the next lecture's 'learn' cannot fire this transition).
        learn_interaction = await self._send(action_name="learn_from_student",
                                             target=list(other_not_isolated_students),
                                             from_state="listening_to_best_student",
                                             streams={"stdin": [f"{best_student}:images"],
                                                      "stdtar": [f"{best_student}:labels"]},
                                             num_steps=self.get_unlabeled_steps(), callback="on_asked_done")
        if learn_interaction is None:
            log.error("Unable to ask the other not-isolated students to learn from the best student")
            self._engaged_agents = all_students
            return False

        self._pending_asks.update(learn_interaction.target)

        # The UUID under which the other students will read the best student's pubsub samples
        relay_uuid = learn_interaction.uuid

        # Asking the best student to label the teacher's unlabeled data, publishing its predictions into its
        # best_student_stream under 'relay_uuid' (an independent interaction, so no UUID collision).
        gen_interaction = await self._send(action_name="teach", target=best_student,
                                           action_kwargs={"relay_uuid": relay_uuid},
                                           from_state="teacher_engaged",
                                           streams={"stdin": [f"{teacher}:images@unlabeled"]},
                                           num_steps=self.get_unlabeled_steps(), callback="on_asked_done")
        if gen_interaction is None:
            log.error("Unable to ask the best student to label the unlabeled data")
            self._engaged_agents = all_students
            return False

        self._pending_asks.update(gen_interaction.target)
        self._engaged_agents = all_students
        return True

    @action
    async def on_asked_done(self, interaction: Interaction | None = None) -> bool:
        """Completion callback for social_round (the only remaining action that fans out two interactions
        and tracks them via _pending_asks; teach_round / exam_round are collapsed into the modern
        `send(..., wait_completion=True)` transit in teach-eval-playlist.json). The IM fires this
        callback exactly once per interaction (when all its targets have reported, regardless of
        OK / TIMEOUT / DISCONNECTED), so a single difference_update is enough."""
        if interaction is not None:
            self._pending_asks.difference_update(interaction.target)
        return True

    @action
    async def all_asks_done(self) -> bool:
        """True when every peer asked in the current round has reported completion (or been dropped).
        Used by the HSM transit out of `best_teaching` to wait for the social_round's two sends to
        finish before moving on."""
        return len(self._pending_asks) == 0

    @action
    async def clear_pending_requests(self, preserve: str | None = None):
        all_inters = list(self.im.received.values()) + list(self.im.sent.values()) + list(self.im.lazy.values())
        for interaction in all_inters:
            if preserve is None or interaction.action_name != preserve:
                await self.im.complete(interaction, CompletionReason.DISCARDED)
        await self.set_engaged_partner(None, clear_found=False)
        return True

    @action
    async def shuffle_round_datasets(self):
        """Re-shuffle every dataset stream's buffer at the start of each lecture round so the new
        round serves data in a fresh order. Fresh `_send` uuids already make `BufferedStream.get` start
        from cursor 0 for every new interaction (see `add_interaction` → buffered_data_index_by_uuid=-1),
        so no explicit enable/disable or restart hook is needed here."""
        self._seed += 1
        for stream_dict in self._round_datasets:
            for stream_obj in stream_dict.values():
                stream_obj.shuffle_buffer(seed=self._seed)
        return True

    @action
    async def evaluate(self, stream_hash: str, how: str, steps: int = 100, re_offset: bool = False):
        # We try to evaluate all the engaged agents
        if not (await super().evaluate(stream_hash, how, steps, re_offset, self._engaged_agents)):
            return False

        _t = self.clock.get_time_ms()
        assert self.stats is not None
        for _peer_id, _eval_result in self._eval_results.items():
            self.stats.store_stat("exam_err", _eval_result, group_key=_peer_id, timestamp=_t)
        return True

    @action
    async def manage_best_of_class(self):
        assert self.stats is not None
        log.user(f"Managing the best of this class...")

        if len(self._valid_cmp_agents) > 0:

            # self.evaluate() populates self._eval_results[peer_id] = eval_result
            # self._valid_cmp_agents is a set of peer_ids
            best_student = next(iter(self._valid_cmp_agents))  # This has length 1
            badge_type = "intermediate"
            badge_description = "Best student of a class, MNIST classification #ImageClassification #MNIST"
            best_student_result = self._eval_results[best_student]

            if best_student_result >= 0:
                _t = self.clock.get_time_ms()
                log.user(f"The best student is {best_student} with this result: {best_student_result})")

                # The agent stores and then sends the stat to the world with the peer_id of the best student
                self.stats.store_stat("best_exam_err_history", best_student_result, group_key=best_student,
                                      timestamp=_t)
                await super().suggest_badges_to_world(agent=best_student,
                                                      score=best_student_result,
                                                      badge_type=badge_type,
                                                      badge_description=badge_description)

                if self._valid_cmp_agents is None or len(self._valid_cmp_agents) == 0:
                    log.error("There is no best student to ask for the next lecture")
                    return False

                await self.find_agents("student", handshake_completed=True)
                all_students = copy.deepcopy(self._engaged_agents)
                not_isolated_students = copy.deepcopy(self._found_agents)
                other_not_isolated_students = not_isolated_students - {best_student}

                log.user("===================== Best student and Other Not Isolated Students =========================")
                log.user(f"- Best Student: {best_student}")
                log.user(f"- Other Not Isolated Students: {other_not_isolated_students}")
                log.user("============================================================================================")

                if other_not_isolated_students is None or len(other_not_isolated_students) == 0:
                    return False

                # Locating the pubsub stream that the best student will fill (its full net hash is unambiguous)
                net_hash_to_stream_dict = self.find_streams(best_student, "best_student_stream")
                best_stream_hash = next(iter(net_hash_to_stream_dict.keys()), None)

                # Telling the other students to subscribe to that pubsub stream (still-current action)
                if best_stream_hash is None or not (await self.send_subscribe(other_not_isolated_students,
                                                                              stream_hashes=[best_stream_hash])):
                    log.error("Unable to tell students to listen to what the best student is going to say")
                    return False
                return True
            else:
                return True
        else:
            return True
