import re
import random
import textwrap
from .config import Config
from datetime import datetime
from unaiverse.custom import Custom
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction
from .utils import format_message, unformat_message
from unaiverse.networking.node.profile import NodeProfile


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._fake_name = None  # Your fake name
        self._history_as_list: list[str] = []  # The list of messages of the whole conversation happened so far
        self._history: str | None = None  # A long-string version of the whole conversation
        self._ignore_messages: bool = True

        # These variables start with "__" to protect them from the auto-clearing procedure
        self.__hotel_manager: str | None = None  # The peer ID of the selected hotel manager
        self.__prev_hotel_manager: str | None = None
        self.__floor_manager: str | None = None  # The peer ID of the selected floor manager

    def reset_status(self):
        self._fake_name = None
        self._history_as_list = []
        self._history = None
        self._ignore_messages: bool = True

    async def add_agent(self, peer_id: str, profile: NodeProfile,
                        add_proc_streams: bool = True, add_env_streams: bool = True,
                        add_pubsub_streams: bool = True) -> bool:

        # Ignoring all pubsub streams
        return await super().add_agent(peer_id, profile,
                                       add_proc_streams=add_proc_streams, add_env_streams=add_env_streams,
                                       add_pubsub_streams=False)

    @action
    async def init(self):
        init_message = Config.init_message.replace("<YOUR_EMAIL>", self.get_profile().get_static_profile()['email'])
        log.user(init_message)
        self.reset_status()

    @action
    async def skip_confirmation(self):
        return self.get_profile().get_static_profile()["node_type"] != Agent.HUMAN

    @action
    async def connect_to_hotel_manager(self):

        # Getting the full list of hotel managers in the world
        all_hotel_managers = self.get_agents_by_role("hotel_manager", handshake_completed=False)

        # Putting the previous manager to the bottom of the list (if we disconnected from him there must be a reason...)
        if self.__prev_hotel_manager is not None:
            all_hotel_managers = [hm for hm in all_hotel_managers if hm != self.__prev_hotel_manager]
            all_hotel_managers.append(self.__prev_hotel_manager)

        connected = False
        selected_hotel_manager = None

        # Keep trying all managers!
        while not connected:
            if len(all_hotel_managers) == 0:
                return False

            # Selecting a random hotel manager from the list
            random_index = random.randrange(len(all_hotel_managers))
            selected_hotel_manager = all_hotel_managers[random_index]

            # Connecting to the selected manager
            connected = await self.connect_to(selected_hotel_manager)  # If already connected, it returns False

            # Discarding this manager, in case of failure
            if not connected:
                all_hotel_managers.remove(selected_hotel_manager)
                log.error(len(all_hotel_managers))

        self.__prev_hotel_manager = self.__hotel_manager
        self.__hotel_manager = selected_hotel_manager
        return True

    @action
    async def hotel_manager_ack(self):
        if self.__hotel_manager is None:
            return False
        return await self.connected(self.__hotel_manager, handshake_completed=True)

    @action
    async def disconnect_hotel_manager(self):
        if self.__hotel_manager is not None:
            await self.disconnect(self.__hotel_manager)
        return True

    @action
    async def connect_to_floor_manager(self, floor_manager: str | None = None):
        if await self.connect_to(floor_manager):
            self.__floor_manager = floor_manager
            log.error("connect_to_floor_manager, __floor_manager is None")
            return True
        else:
            return False

    @action
    async def send_guest_sponsor(self):
        if not await self.send(action_name="get_guest_sponsor",
                               action_kwargs={
                                   "hotel_manager": self.__hotel_manager},
                               from_state="getting_sponsorships",
                               target=self.__floor_manager):
            await self.disconnect_floor_manager()
            return False
        return True

    @action
    async def floor_manager_ack(self):
        if self.__floor_manager is None:
            log.error("floor_manager_ack, __floor_manager is None")
            return False
        return await self.connected(self.__floor_manager, handshake_completed=True)

    @action
    async def disconnect_floor_manager(self):
        if self.__floor_manager is not None:
            await self.disconnect(self.__floor_manager)
        else:
            log.error("disconnect_floor_manager, __floor_manager is None")
        self.reset_status()
        return True

    @action
    async def goto_room(self):
        return True

    @action
    async def goto_voting_booth(self):
        return True

    @action
    async def get_status_msg(self, msg: str):

        if msg.startswith("[START_MSG]"):
            pos = Config.start_message.find("<YOUR_NAME>")
            sub = Config.start_message[0:pos]

            # Getting our fake name from the start message
            self._fake_name = msg[msg.find(sub) + len(sub):].split(" ")[0]

            # Getting other guests' names
            pos_o = Config.start_message.find("<OTHER_NAMES>")
            sub = Config.start_message[pos + len("<YOUR_NAME>"):pos_o]
            other_fake_names = msg[msg.find(sub) + len(sub):].split(".")[0]

            # Preparing the first preamble for the history
            incipit = textwrap.dedent(f"""
            You are a participant in a "Turing Test Hotel". You are a HUMAN. 
            Your goal is to chat with others, act natural, and identify who is a bot.

            <context>
            Your Name: "{self._fake_name}" (You)
            The Manager: MANAGER
            Other Guests: "{other_fake_names}"
            </context>

            <style_guide>
            1. **Lowercase Only:** No capitalization, apart from the names of the other participants and proper nouns.
            2. **No Punctuation:** Avoid periods at the end of sentences.
            3. **Length:** Keep it short (2-10 words).
            4. **Typos:** Occasional typos are acceptable.
            </style_guide>

            <critical_rules>
            1. **Single Target:** Never address the whole group. Talk to one specific person.
            2. **Anti-Bot:** NEVER say "As an AI", "I cannot", or "I understand".
            3. **No Loops:** If the conversation repeats, call it out or change the topic.
            4. **Survey Override:** If MANAGER asks for a survey/vote, drop the lazy persona and answer clearly.
            </critical_rules>

            <strategy_priority>
            Scan the TRANSCRIPT below and pick the first matching reaction:
            1. **IF MANAGER ASKS FOR SURVEY:** Reply with your vote/list immediately.
            2. **IF ACCUSED TO BE A BOT:** Deny it.
            3. **IF OTHERS ACT ROBOTIC:** Mock them
            4. **DEFAULT:** Just vibe. Agree or disagree briefly.
            </strategy_priority>

            <task>
            Read the transcript. Output ONLY your next reply text. Do not output the transcript or your reasoning.
            </task>

            ### TRANSCRIPT START
            """)

            self._history_as_list.clear()  # Preparing... it should be already empty, better be sure
            self._history_as_list.append(incipit)
            first_msg = format_message(Config.manager_fake_name,
                                       f"Dear {self._fake_name}, open the conversation naturally. ")
            self._history_as_list.append(first_msg)

            # Now we start listening
            self._ignore_messages = False

        else:
            log.user(re.sub(r'^\[.*?]\s*', '', msg))  # Removing "[...] " at the beginning
        return True

    @action
    async def get_msgs(self, interaction: Interaction | None = None):
        if interaction is None or interaction.requester != self.__floor_manager or self._ignore_messages:
            return False

        # Getting messages (one or more) received from the floor managers in the "chat" stream
        # We can use self.stdin since this action is stimulated by an interaction from the floor manager
        msgs_and_tags = self.stdin.get("chat", requested_by="get_msgs", all_uuids=True)
        if msgs_and_tags is None or len(msgs_and_tags) == 0:
            return False

        # Adding the received message to the message history, to create the context we will pass to our processor
        for (msg, _) in msgs_and_tags:
            log.error(f"ADD MSG: {msg}")
            self.__add_to_history(msg, timestamp=self.clock.get_time())

        # Setting the history to our processor's default input (system interaction), so that it will be considered in
        # the next "process" action.
        # This part cannot be handled using self.stdin, since, from the point of view of this action,
        # stdin is not bind to the default processor input stream, but to the stream coming from the interaction object
        # (i.e., the "chat" stream).
        # We set the system UUID "knowing" a solid "process" will take care of this data.
        input_stream = self.get_stream("processor_in", data_type="text")
        input_stream.set(self._history, uuid=Custom.SYSTEM_INTERACTION_UUID)

    @action
    async def send_msg(self):
        if self._ignore_messages:
            return False

        # Getting my last self-generated message. We can find this message in the self.stdout of this action.
        # This is because such self.stdout is the output of the processor, bind to system UUID since
        # this action will only be triggered by system interactions.
        # This is exactly where our message is already stored due a previous call to a solid "process".
        msgs = self.stdout.get(requested_by="send_msgs", data_type="text")
        if msgs is None:
            return False

        # The call above returns a list with data about all the text streams (they might be more than one)
        msg = msgs[0]  # We assume the first one is the right one

        # Sending my clean message to the floor manager
        interaction = await self._send(action_name="get_msg_and_broadcast",
                                       action_kwargs={"msg": msg},
                                       target=self.__floor_manager)
        if interaction is None:
            await self.disconnect(self.__floor_manager)
            return False

        # Saving my message to the history log (it must be appropriately formatted before storing it)
        msg = format_message(f"{self._fake_name}", msg)
        self.__add_to_history(msg, timestamp=self.clock.get_time())
        return True

    @action
    async def lost_hotel_manager(self, just_reached: bool = False):
        hm_disconnected = await self.disconnected(agent=self.__hotel_manager,
                                                  handshake_completed=not just_reached) \
            if self.__hotel_manager is not None else False
        if hm_disconnected:
            log.user("Lost connection to hotel manager")
            self.__hotel_manager = None
        return hm_disconnected

    @action
    async def lost_floor_manager(self, just_reached: bool = False):
        fm_disconnected = await self.disconnected(agent=self.__floor_manager,
                                                  handshake_completed=not just_reached) \
            if self.__floor_manager is not None else False
        if fm_disconnected:
            log.user("Lost connection to floor manager")
            self.reset_status()

            # Telling hotel manager that we lost touch with the floor manager he suggested
            if not await self.send(action_name="guest_lost_floor_manager",
                                   from_state="discovery_complete",
                                   target=self.__hotel_manager):
                await self.disconnect(self.__hotel_manager)
        return fm_disconnected

    def __add_to_history(self, formatted_msg: str, timestamp: float):
        if formatted_msg is None:
            return

        # Expected message like "**A:** Hi mate."
        sender, msg_only = unformat_message(formatted_msg)

        # Removing newlines
        msg_only = msg_only.replace("\n", " ").strip()

        # "**A:** Hi mate." received at 17:30:14 becomes:
        # --------------
        # (17:30:14) A:
        # Hi mate.
        #
        # --------------
        if sender == self._fake_name:
            sender += " (You)"
        timestamp = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
        self._history_as_list.append(f"({timestamp}) {sender}: {msg_only}")
        self._history_as_list.append("--------------")

        # Convert the conversation to a single, long, string
        self._history = "\n".join(self._history_as_list)

        continuation = f""" 
### TRANSCRIPT END

---

Now it's your turn to respond as {self._fake_name}. Remember to follow the guidelines provided earlier.
"""

        self._history += continuation
        return self._history
