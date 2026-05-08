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
import random
import time as tm
from unaiverse.agent import Agent
from unaiverse.utils.logger import log
from unaiverse.interaction import CompletionReason
from unaiverse.modules.utils import MultiIdentity


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._broadcaster_peer_id = None
        self._broadcaster_stream = None
        self._broadcaster_net_hash = None
        self._broadcaster_sender = None
        self._user_stream = None
        self._user_stream_net_hash = None
        self._last_msg_time = None
        self._last_turns = []

    async def connect_to_broadcaster(self, role: str):
        """Connecting to the broadcaster (async)."""

        for net_hash, stream_dict in self.proc_streams.items():
            for stream_obj in stream_dict.values():
                if stream_obj.props.is_text() and not stream_obj.props.is_public():
                    self._user_stream = stream_obj
                    self._user_stream_net_hash = net_hash
                    break

        if self._user_stream is None:
            self.err("Cannot find the processor stream for the current user")
            return False

        if await self.connect_by_role(role):
            self._engaged_agents = self._found_agents
            self._broadcaster_peer_id = next(iter(self._found_agents))  # Takes the first broadcaster
            self._last_msg_time = tm.time()
            return True
        else:
            return False

    async def check_messages(self, max_silence_seconds: float = 10.0, talk_probability: float = 0.333,
                             history_len: int = 3):
        if self.get_current_role() != "user":
            return False

        # Avoid printing this message multiple times
        self.behav.get_state().msg = None

        if self._broadcaster_stream is None:
            net_hash_to_stream_dict = self.find_streams(self._broadcaster_peer_id, "processor")
            for net_hash, stream_dict in net_hash_to_stream_dict.items():
                for _, stream_obj in stream_dict.items():
                    if stream_obj.props.is_text():
                        self._broadcaster_stream = stream_obj
                        self._broadcaster_net_hash = net_hash
                        break

        if self._broadcaster_stream is not None:
            msgs = self._broadcaster_stream.get("check_messages", all_uuids=True)
            if msgs is not None and len(msgs) > 0:
                replied = False
                for msg, _, _ in msgs:
                    log.error(f"[{self.clock.get_cycle()}], msg={msg}")
                    my_rand = random.random()
                    self._last_msg_time = tm.time()
                    self._last_turns.append(msg)
                    self._last_turns = self._last_turns[-history_len:]

                    if not replied and (((not self.is_human()) and (self.proc is not None and
                                                                    not isinstance(self.proc.module,
                                                                                   MultiIdentity))) and
                                        ((self.get_name().lower() in msg.lower().strip()) or
                                         (self._node_conn.count_by_role(Agent.ROLE_WORLD_AGENT |
                                                                        self.ROLE_STR_TO_BITS["user"]) == 2) or
                                         (my_rand < talk_probability))):

                        augmented_msg = (
                            f"Generate a meaningful reply to the following conversation going on in chatroom "
                            f"(just to let you know, your name is {self.get_name()}). "
                            f"Please generate only the message to be sent in the chatroom,"
                            f"no other texts or preambles. DO NOT INCLUDE YOUR NAME IN THE GENERATED MESSAGE. "
                            f"DO NOT USE MARKDOWN. "
                            f"The last turns of the conversation are:\n")
                        for i, prev_msg in enumerate(self._last_turns):
                            augmented_msg += f"({i}) {prev_msg}\n"
                        augmented_msg += "The current message of the conversation is:\n"
                        augmented_msg += msg

                        log.error(f"A my_rand={my_rand}, talk_probability={talk_probability}, name-found={self.get_name().lower() in msg.lower().strip()}")

                        self.stdin.set("proc_input_0", augmented_msg)
                        #await self.process()
                        #log.error(f"A process done!")
                        #await self.send(action_name="do_gen",
                        #                action_kwargs={"u_hashes": [self.get_peer_id() + ":processor"],
                        #                               "samples": 1},
                        #                streams=["processor"],
                        #                num_steps=1,
                        #                copy_sys=True,
                        #                target=self._broadcaster_peer_id)
                        replied = True
                        #log.error(f"A send done!")
                        #msg = self.stdout.get("proc_output_0")
                        #log.error(f"A msg was={msg}")
                        self._last_msg_time = tm.time()
            else:
                if ((not self.is_human()) and (self.proc is not None and
                                               not isinstance(self.proc.module, MultiIdentity)) and
                        ((tm.time() - self._last_msg_time) > max_silence_seconds) and
                        self._node_conn.count_by_role(Agent.ROLE_WORLD_AGENT | self.ROLE_STR_TO_BITS["user"]) > 1):

                    promote_prompt = (f"The conversation in a chatroom is simply silent, nobody is talking. "
                                      f"Generate a nice message to trigger the conversation of a topic that is "
                                      f"expected to be pretty popular and known (select among: sport, weather, "
                                      f"technology, fun, movies, songs). "
                                      f"Please generate only the message to be sent in the chatroom,"
                                      f"no other texts or preambles.\n")

                    self.stdin.set("proc_input_0", promote_prompt)
                    #log.error(f"B (tm.time() - self._last_msg_time)={tm.time() - self._last_msg_time}")
                    #if await self.process():
                    #    log.error(f"B process done!")
                    #    await self.send(action_name="do_gen",
                    #                    action_kwargs={"u_hashes": [self.get_peer_id() + ":processor"],
                    #                                   "samples": 1},
                    #                    streams=["processor"],
                    #                    num_steps=1,
                    #                    copy_sys=True,
                    #                    target=self._broadcaster_peer_id)
                    #    log.error(f"B send done!")
                    #    msg = self.stdout.get("proc_output_0")
                    #    log.error(f"B msg was={msg}")

                    self._last_msg_time = tm.time()
                    #self._last_turns.append(msg)
                    self._last_turns = self._last_turns[-history_len:]
            return True
        else:
            self.err("Cannot find the processor stream of the broadcaster")
            return False

    async def do_gen(self, u_hashes: list[str] | None = None, extra_hashes: list[str] | None = None,
                     samples: int = 100, time: float = -1., timeout: float = -1.,
                     _requester: str | list | None = None, _request_time: float = -1., _request_uuid: str | None = None,
                     _completed: bool = False) -> bool:
        """Broadcast the result of the generation to all the agents in this world (excluding the sender)."""

        if self.get_current_role() == "broadcaster":
            if self.behaving_in_world():

                # If the requester disconnected, we treat this action as correctly completed, to destroy the request
                if _requester not in self.all_agents:
                    return True

                _, _my_peer_id = self.get_peer_ids()
                self._broadcaster_sender = self.all_agents[_requester].get_static_profile()['node_name']

                log.misc(f"Broadcaster received a request from {_requester}, agent named {self._broadcaster_sender}, "
                         f"where the current agent list is:\n{list(self.world_agents.keys())}\n"
                         f"and the broadcaster peer ID is {_my_peer_id}")

                _requester = list(set(self.world_agents.keys()) - {_requester, _my_peer_id})

                log.misc(f"Broadcaster decided the list of peers to send the message from "
                         f"agent {self._broadcaster_sender} is then {_requester}")

                if len(_requester) == 0:
                    log.error("Broadcaster is skipping the generation procedure, since no recipients would be there")
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

        return await super().do_gen(u_hashes, extra_hashes, samples, time, timeout,
                                    _requester=_requester, _request_time=_request_time, _request_uuid=_request_uuid,
                                    _completed=False)

    def proc_callback_inputs(self, inputs):
        inputs = super().proc_callback_inputs(inputs)

        # Broadcaster will add usernames at the beginning of the message
        if self.get_current_role() == "broadcaster":
            if self.behaving_in_world():
                for i, _input in enumerate(inputs):
                    if isinstance(_input, str):
                        inputs[i] = "**" + self._broadcaster_sender + ":** " + _input
        return inputs
