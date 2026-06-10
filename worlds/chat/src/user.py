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
from collections.abc import Iterable
from unaiverse.utils.logger import log
from unaiverse.streams import DataProps
from unaiverse.agent import Agent, action
from unaiverse.modules.utils import MultiIdentity


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._broadcaster_peer_id = None
        self._broadcaster_stream = None
        self._user_stream = None  # Own processor output stream (read by check_messages to log self-gens)
        self._last_msg_time = None
        self._last_turns = []

    @action
    async def connect_to_broadcaster(self, role: str) -> bool:
        """Locate the local processor output stream (used by check_messages to read back our own
        self-generated messages, and forwarded to the broadcaster by generate_and_send), then connect to
        the broadcaster (async)."""
        self._user_stream = self.get_stream("processor", data_type="text")
        if self._user_stream is None:
            log.error("Cannot find own processor output stream")
            return False

        if await self.connect_by_role(role):
            self._broadcaster_peer_id = next(iter(self._found_agents))  # Takes the first broadcaster
            self._last_msg_time = tm.time()
            return True
        return False

    @action
    async def check_messages(self, max_silence_seconds: float = 10.0, talk_probability: float = 0.333,
                             history_len: int = 3) -> bool:
        """Poll the broadcaster's stream and own self-generated messages, decide whether to reply or to
        promote the conversation after a silence, and stage the prompt in stdin so that the next HSM transit
        (`generate_and_send`) can run the proc and forward the reply to the broadcaster."""

        # Avoid printing this message multiple times
        assert self.behav is not None
        self.behav.get_state().msg = None

        if self._broadcaster_stream is None and self._broadcaster_peer_id is not None:
            self._broadcaster_stream = self.get_stream("processor",
                                                       peer_id=self._broadcaster_peer_id,
                                                       data_type="text")

        # Collecting my own self-generated messages (so they show in the local history)
        msgs = self._user_stream.get("check_messages", all_uuids=True)
        if msgs is not None and len(msgs) > 0:
            for msg, _, _ in msgs:
                self._last_msg_time = tm.time()
                self._last_turns.append(msg)
                self._last_turns = self._last_turns[-history_len:]

        # Collecting/handling messages broadcast by the broadcaster
        if self._broadcaster_stream is None:
            log.error("Cannot find the processor stream of the broadcaster")
            return False

        msgs = self._broadcaster_stream.get("check_messages", all_uuids=True)
        if msgs is not None and isinstance(msgs, Iterable) and len(msgs) > 0:
            replied = False
            for msg, _, _ in msgs:
                self._last_msg_time = tm.time()
                self._last_turns.append(msg)
                self._last_turns = self._last_turns[-history_len:]

                my_rand = random.random()

                if (not replied and
                        ((not self.is_human()) and
                         (self.proc is not None and not isinstance(self.proc.module, MultiIdentity))) and
                        ((self.get_name().lower() in msg.lower().strip()) or
                         (self.node_conn.count_by_role(Agent.ROLE_WORLD_AGENT |
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

                    self.stdin.set("proc_input_0", augmented_msg)
                    replied = True
        else:
            if ((not self.is_human()) and
                    (self.proc is not None and not isinstance(self.proc.module, MultiIdentity)) and
                    ((tm.time() - self._last_msg_time) > max_silence_seconds) and
                    self.node_conn.count_by_role(Agent.ROLE_WORLD_AGENT | self.ROLE_STR_TO_BITS["user"]) > 1):

                promote_prompt = (f"The conversation in a chatroom is simply silent, nobody is talking. "
                                  f"Generate a nice message to trigger the conversation of a topic that is "
                                  f"expected to be pretty popular and known (select among: sport, weather, "
                                  f"technology, fun, movies, songs). "
                                  f"Please generate only the message to be sent in the chatroom,"
                                  f"no other texts or preambles.\n")

                self.stdin.set("proc_input_0", promote_prompt)
        return True

    @action
    async def generate_and_send(self, samples: int = 1) -> bool:
        """Run the local proc on whatever check_messages just staged in stdin, then forward the resulting
        message to the broadcaster via a `broadcast_message` interaction whose stdin points to our own
        processor output stream."""
        if self.proc is None or self._broadcaster_peer_id is None:
            return False

        # Local self-generation: stdin -> stdout (under Custom.SYSTEM_INTERACTION_UUID)
        ok = await self.process()
        if not ok:
            return False

        # Notice:
        # `copy_sys=True` lifts the just-produced output (currently bound to the system uuid) into the new interaction
        # uuid so send_stream_samples ships it to the broadcaster.
        my_processor_user_hash = DataProps.build_user_hash(self.get_peer_id(), self._user_stream.props.get_name())
        return await self.send(action_name="broadcast_message",
                               target=[self._broadcaster_peer_id],
                               streams=[my_processor_user_hash],
                               num_steps=samples, copy_sys=True)
