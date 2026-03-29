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
from unaiverse.agent import Agent
from unaiverse.utils.misc import prepare_app_dir
from unaiverse.interaction import CompletionReason
from unaiverse.streams import DataStream, DataProps
from unaiverse.modules.utils import error_rate_mnist_test_set


class WAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent_folder_name = os.path.join(prepare_app_dir(), "social_learning")
        os.makedirs(self._agent_folder_name, exist_ok=True)

    def accept_new_role(self, role: int):
        super().accept_new_role(role)

        self.add_streams([DataStream(props=DataProps(group="best_student_stream", name="images",
                                                     public=False, pubsub=True,
                                                     data_type="tensor",
                                                     data_desc="Batched images if this is the best student",
                                                     tensor_shape=(None, 1, 28, 28),
                                                     tensor_dtype=torch.float32)),
                          DataStream(props=DataProps(group="best_student_stream", name="labels", public=False,
                                                     data_type="tensor", pubsub=True,
                                                     data_desc="Batched class-indices if this is the best student",
                                                     tensor_shape=(None,),
                                                     tensor_dtype=torch.long))])

        self.update_streams_in_profile()

    async def clear_pending_requests(self, preserve: str | None = None):
        actions = self.behav.get_all_actions()
        for action in actions:
            if preserve is None or action.name != preserve:
                interactions = action.get_list_of_interactions()
                for interaction in interactions:
                    self.im.complete(interaction, CompletionReason.DISCARDED)
        await self.set_engaged_partner(None, clear_found=False)

    async def do_gen(self, u_hashes: list[str] | None = None, extra_hashes: list[str] | None = None,
                     samples: int = 100, time: float = -1., timeout: float = -1.,
                     _requester: str | list | None = None, _request_time: float = -1., _request_uuid: str | None = None,
                     _completed: bool = False):

        # Generic generation request
        if not (await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                     _requester, _request_time, _request_uuid, _completed)):
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
                    stream_obj.set_uuid(_request_uuid)

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

    async def get_disengagement(self, disconnect_too: bool = False, _requester: str | None = None):
        if not (await super().get_disengagement(disconnect_too, _requester)):
            return False
        
        # we overload this so that each student, after class, takes the full mnist test set and evaluates itself
        error_rate = error_rate_mnist_test_set(network=self.proc,
                                               mnist_data_save_path=os.path.join(self._agent_folder_name, "mnist_data"))
        _t = self.clock.get_time_ms()
        _, _peer_id = self.get_peer_ids()
        self.stats.store_stat("full_test_err", error_rate, peer_id=_peer_id, timestamp=_t)
        return True
