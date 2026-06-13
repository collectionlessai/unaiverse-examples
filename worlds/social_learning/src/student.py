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
import torch
from unaiverse.agent import Agent, action
from unaiverse.streams import Stream, DataProps
from unaiverse.utils.misc import prepare_app_dir
from unaiverse.interaction import Interaction, CompletionReason
from unaiverse.modules.utils import error_rate_mnist_test_set, ModuleWrapper


class WAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_folder_name = os.path.join(prepare_app_dir(), "social_learning")
        os.makedirs(self._agent_folder_name, exist_ok=True)

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        # The stream where this student will possibly stream his lecture, if nominated "best student"
        self.add_streams([Stream(props=DataProps(group="best_student_stream", name="images",
                                                 public=False, pubsub=True,
                                                 data_type="tensor",
                                                 data_desc="Batched images if this is the best student",
                                                 tensor_shape=(None, 1, 28, 28),
                                                 tensor_dtype=torch.float32)),
                          Stream(props=DataProps(group="best_student_stream", name="labels", public=False,
                                                 data_type="tensor", pubsub=True,
                                                 data_desc="Batched class-indices if this is the best student",
                                                 tensor_shape=(None,),
                                                 tensor_dtype=torch.long))])

        # The newly added stream must appear in the profile of this agent
        self.update_streams_in_profile()

    @action
    async def clear_pending_requests(self, preserve: str | None = None):
        all_inters = list(self.im.received.values()) + list(self.im.sent.values()) + list(self.im.lazy.values())
        for interaction in all_inters:
            if preserve is None or interaction.action_name != preserve:
                await self.im.complete(interaction, CompletionReason.DISCARDED)
        await self.set_engaged_partner(None, clear_found=False)
        return True

    @action
    async def learn_from_student(self, interaction: Interaction | None = None) -> bool:
        """Learn from a peer's (the best student's) pubsub stream, just a renaming of action 'learn'."""
        return await super().learn(interaction)

    @action
    async def teach(self, relay_uuid: str | None = None, interaction: Interaction | None = None) -> bool:
        """Best-student social-teaching step: run one inference on the teacher's unlabeled data (built-in
        'process' behavior) and relay the input image + our predicted label into our pubsub best_student_stream,
        published under 'relay_uuid' (the UUID the other students read while learning).

        The ordinary exam uses the built-in 'process' action (no relaying); only this dedicated action feeds
        the best_student_stream, under the teacher-provided relay_uuid (NOT this interaction's own UUID), so
        the relay interaction can stay independent of the other students' learn interaction.
        """

        # Base inference: reads stdin (unlabeled image), runs the processor, writes the prediction to stdout
        if not (await super().process(interaction)):
            return False
        if interaction is None or relay_uuid is None:
            return True

        # Read what process just consumed/produced: the teacher's image (from stdin) and our prediction (from
        # stdout), under THIS interaction's UUID. Then re-publish them on our own best_student_stream under
        # the relay UUID the other students read with.
        image = self.stdin.get(0, requested_by="teach")
        prediction = self.stdout.get(0, requested_by="teach")

        me = self.get_peer_id()
        images_stream = self.get_stream("images", peer_id=me)
        labels_stream = self.get_stream("labels", peer_id=me)

        assert images_stream is not None and labels_stream is not None
        images_stream.set(image, uuid=relay_uuid)
        labels_stream.set(prediction, uuid=relay_uuid)
        return True

    @action
    async def disengage(self, disconnect_too: bool = False, interaction: Interaction | None = None) -> bool:
        if not (await super().disengage(disconnect_too, interaction)):
            return False

        # We overload this so that each student, after class, takes the full mnist test set and evaluates itself
        assert self.proc is not None
        assert isinstance(self.proc, ModuleWrapper)
        assert isinstance(self.proc.module, torch.nn.Module)
        error_rate = error_rate_mnist_test_set(network=self.proc.module,
                                               mnist_data_save_path=os.path.join(self._agent_folder_name, "mnist_data"))
        _t = self.clock.get_time_ms()
        _, _peer_id = self.get_peer_ids()
        assert self.stats is not None
        self.stats.store_stat("full_test_err", error_rate, group_key=_peer_id, timestamp=_t)
        return True
