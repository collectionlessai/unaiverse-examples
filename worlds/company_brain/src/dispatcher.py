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
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import CompletionReason


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._sender_name = None

    @action
    async def do_gen(self, u_hashes: list[str] | None = None, extra_hashes: list[str] | None = None,
                     samples: int = 100, time: float = -1., timeout: float = -1.,
                     _requester: str | list | None = None, _request_time: float = -1., _request_uuid: str | None = None,
                     _completed: bool = False) -> bool:
        """Dispatch the result of the generation to all the agents in this world (excluding the sender)."""

        if self.behaving_in_world():

            # If the requester disconnected, we treat this action as correctly completed, to destroy the request
            if _requester not in self.all_agents:
                return True

            _, _my_peer_id = self.get_peer_ids()
            self._sender_name = self.all_agents[_requester].get_static_profile()['node_name']

            log.misc(f"Dispatcher received a request from {_requester}, agent named {self._sender_name}, "
                     f"where the current agent list is:\n{list(self.world_agents.keys())}\n"
                     f"and the dispatcher peer ID is {_my_peer_id}")

            _requester = list(set(self.world_agents.keys()) - {_requester, _my_peer_id})

            log.misc(f"Dispatcher decided the list of peers to send the message from "
                     f"agent {self._sender_name} is then {_requester}")

            if len(_requester) == 0:
                log.error("Dispatcher is skipping the generation procedure, since no recipients would be there")
                return False

            generated_msg = await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                                 _requester=_requester, _request_time=_request_time,
                                                 _request_uuid=_request_uuid,
                                                 _completed=False)

            if generated_msg:
                await self.send(target=_requester,
                                data_samples={
                                    "proc_output_0": self.get_stream('processor').get(
                                        requested_by="do_gen_up", uuid=_request_uuid)},
                                num_steps=1)

                interaction = self.im.get_current()
                await self.im.complete(interaction, reason=CompletionReason.DISCARDED)
                self.im.clear_from_all_streams(interaction, clear_data=True)
            return generated_msg
        else:
            return await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                        _requester=_requester, _request_time=_request_time, _request_uuid=_request_uuid,
                                        _completed=False)

    def proc_callback_inputs(self, inputs):
        inputs = super().proc_callback_inputs(inputs)

        # Dispatcher will add usernames at the beginning of the message
        if self.behaving_in_world():
            for i, _input in enumerate(inputs):
                if isinstance(_input, str):
                    inputs[i] = "**" + self._sender_name + ":** " + _input
        return inputs
