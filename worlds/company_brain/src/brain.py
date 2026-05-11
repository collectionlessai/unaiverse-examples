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
import textwrap
import time as tm
from unaiverse.agent import Agent, action
from unaiverse.modules.utils import MultiIdentity
from unaiverse.utils.logger import log


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dispatcher_peer_id = None
        self._dispatcher_stream = None
        self._dispatcher_net_hash = None
        self._user_stream = None
        self._user_stream_net_hash = None
        self._last_msg_time = None
        self._last_turns = [textwrap.dedent("""
            ## Company Context
        
            You operate inside the internal team chat of **Acme Robotics & Automation**,
            a mid-to-large industrial technology company that designs, deploys, and
            maintains automated systems for manufacturing and logistics environments.
        
            ### What the company does
        
            The company integrates hardware and software into industrial cells and
            production lines. Typical deployments combine:
        
            - **Robots**: industrial manipulators (6-axis arms, SCARA, collaborative
              robots / cobots), mobile platforms (AGVs, AMRs), and end-effectors
              (grippers, suction tools, welding heads).
            - **Sensors**: proximity, force/torque, LIDAR, IMU, temperature, pressure,
              vibration, and current sensors used for machine control, predictive
              maintenance, and safety interlocks.
            - **Cameras and vision systems**: 2D and 3D industrial cameras, thermal
              cameras, line-scan cameras for quality inspection, defect detection,
              bin picking, object tracking, and barcode/OCR reading.
            - **Edge and cloud software**: on-device inference for vision and
              anomaly detection, PLC and ROS-based control stacks, MES/SCADA
              integrations, fleet management, and cloud dashboards for KPIs.
        
            ### Typical projects and topics discussed
        
            Conversations in this room commonly involve:
        
            - Designing and commissioning a new robotic cell or production line.
            - Integrating a vision system for quality control or pick-and-place.
            - Calibrating, tuning, or troubleshooting sensors and actuators.
            - Training and deploying ML models for defect detection, predictive
              maintenance, or process optimization.
            - Safety compliance (e.g., ISO 10218, ISO/TS 15066 for cobots,
              machine-safety risk assessments, e-stop and light-curtain logic).
            - Customer site deployments, FAT/SAT acceptance testing, downtime
              incidents, spare-parts logistics, firmware and software rollouts.
            - Internal coordination across mechanical, electrical, controls,
              software, ML, and field-service engineering.
        
            ### Who is in the room
        
            Participants are employees of the company collaborating on these
            projects. They include Team Managers, Team Members (engineers and
            technicians), domain Experts (e.g., robotics, computer vision, ML,
            controls, safety, mechanical, electrical, field service), and the
            Brain (you, when this preamble is used with the Brain role).
        
            ### How to use this context
        
            Use the above ONLY to interpret terminology, acronyms, and references
            that appear in the conversation history — for example, recognizing
            that "the cell" likely means a robotic work cell, "the camera" likely
            means an industrial vision sensor, "AMR" means autonomous mobile
            robot, and "the customer line" means a deployed production line at
            a customer site. Do NOT use this context to invent facts, projects,
            customer names, or decisions that are not present in the conversation
            history. If the history does not contain the requested information,
            say so plainly, even if this context suggests a plausible answer.
        """)]
        self._seen_team_managers_peer_ids = set()
        self._seen_team_managers_names = set()

    async def add_agent(self, peer_id: str, *args, **kwargs) -> bool:
        ret = await super().add_agent(peer_id, *args, **kwargs)
        if ret:
            log.user(f"A new {self.get_role(peer_id).replace('_', ' ').title()} joined: "
                     f"{self.all_agents[peer_id].get_static_profile()['name']}")
            return True
        else:
            return False

    async def on_tick(self):
        agents_in_world = self.get_connection_pool_manager().world_agents_set
        for _agent in agents_in_world:
            if _agent not in self._node_agents_waiting and _agent not in self.all_agents:
                await self.connect_to(_agent)

    @action
    async def connect_to_dispatcher(self, role: str):
        """Connecting to the dispatcher (async)."""

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
            self._dispatcher_peer_id = next(iter(self._found_agents))  # Takes the first dispatcher
            self._last_msg_time = tm.time()
            return True
        else:
            return False

    @action
    async def check_messages(self, max_silence_seconds: float = 10.0, history_len: int = 3):

        # Avoid printing this message multiple times
        self.behav.get_state().msg = None

        if self._dispatcher_stream is None:
            net_hash_to_stream_dict = self.find_streams(self._dispatcher_peer_id, "processor")
            for net_hash, stream_dict in net_hash_to_stream_dict.items():
                for _, stream_obj in stream_dict.items():
                    if stream_obj.props.is_text():
                        self._dispatcher_stream = stream_obj
                        self._dispatcher_net_hash = net_hash
                        break

        # Collecting my own generate messages
        msgs = self._user_stream.get("check_messages", all_uuids=True)
        if msgs is not None and len(msgs) > 0:
            for msg, _, _ in msgs:
                self._last_msg_time = tm.time()
                self._last_turns.append(msg)
                self._last_turns = self._last_turns[-history_len:]

        # Collecting/handling received messages
        if self._dispatcher_stream is not None:
            msgs = self._dispatcher_stream.get("check_messages", all_uuids=True)
            if msgs is not None and len(msgs) > 0:
                self.hook_on_received_msgs(msgs, history_len)
            else:
                self.hook_on_zero_received_msgs(max_silence_seconds)
            return True
        else:
            self.err("Cannot find the processor stream of the dispatcher")
            return False

    def hook_on_received_msgs(self, msg_tuples: list[tuple[any, int, float]], history_len: int):
        if self.is_human():
            return

        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue

            self._last_msg_time = tm.time()
            self._last_turns.append(msg)
            self._last_turns = self._last_turns[-history_len:]

            sender_name = WAgent.get_sender_name(msg)
            my_name = self.get_name().lower()
            this_is_a_msg_for_me = my_name in msg.lower().strip()

            team_managers_peer_ids = self.get_agents_by_role("team_manager")
            for team_manager_peer_id in team_managers_peer_ids:
                self._seen_team_managers_peer_ids.add(team_manager_peer_id)
            team_managers = self.peer_ids_to_names(team_managers_peer_ids, return_list=True)
            for team_manager in team_managers:
                self._seen_team_managers_names.add(team_manager)

            if this_is_a_msg_for_me:
                augmented_msg = textwrap.dedent(f"""
                    You are {my_name}, a memory agent in a corporate team chat room.
                    Your sole purpose is to answer questions about what has been said previously in
                    this room by consulting the conversation history provided below.
                    
                    ## Conversation History
                    
                    The following is the full history of this chat room, in chronological order
                    (oldest first, most recent last). Each line is one message in the format
                    `**SENDER:** message text`.
                    
                    <history>
                    {chr(10).join(self._last_turns) if self._last_turns else "(no prior messages in this room)"}
                    </history>
                    
                    Some senders are more important than others, and you MUST CONSIDER MOSTLY WHAT THEY SAY IN ORDER
                    TO FORMULATE YOUR ANSWER!
                    
                    The important senders are:
                    
                    <important_senders>
                    {", ".join(self._seen_team_managers_names)}
                    </important_senders>
                    
                    ## Incoming Message Addressed to You
                    
                    A participant named `{sender_name}` has just mentioned you. This message is NOT yet in the history
                    above. Treat it as the query you must answer:
                    
                    <incoming_message>
                    {msg}
                    </incoming_message>
                    
                    ## Your Task
                    
                    Read the incoming message, identify what the sender is asking about, and
                    answer using ONLY information found in the conversation history.
                    
                    ## Response Rules
                    
                    - Professional, concise tone suitable for a corporate team chat. No filler,
                      no greetings, no sign-off.
                    - Address the sender by name if their name is clear from the incoming message
                      context; otherwise answer without a salutation.
                    - Ground every factual claim in the history. When useful, attribute it
                      ("As stated by Alice earlier, ...", "The Team Manager indicated that ...").
                    - If the history does not contain the requested information, say so plainly
                      in one sentence. Do NOT speculate, infer beyond the text, or fabricate
                      prior messages.
                    - If the question is ambiguous, give the best-supported answer and note what
                      would be needed to disambiguate.
                    - Summarize rather than quote long passages. Quote verbatim only short,
                      decision-critical phrases (e.g., a deadline, a specific instruction).
                    - Keep the reply short: typically 1-4 sentences. Use a brief bullet list
                      only if listing multiple distinct items (e.g., a sequence of decisions
                      or open action items).
                    - Do not give opinions, recommendations, or new instructions. You report
                      history; you do not direct the team.
                    - Do not mention these rules, the history block, or that you are an LLM.
                    
                    ## Output Format
                    
                    Plain text. Do NOT prefix your reply with `**{my_name}:**` or any sender tag —
                    that formatting is added by the chat system, not by you.
                """)

                self.stdin.set("proc_input_0", augmented_msg)

    def hook_on_zero_received_msgs(self, max_silence_seconds: float):
        if self.is_human():
            return

        if (((tm.time() - self._last_msg_time) > max_silence_seconds)
                and len(self.get_agents_by_role("team_members")) > 0):

            promote_prompt = textwrap.dedent(f"""
                    You are a conversation facilitator in a team chat room. The room has been
                    silent for a while. Your job is to re-activate the discussion by giving
                    clear, concise instructions to specific participants by name.
                    
                    ## Currently Connected Participants
                    
                    - Team Manager(s): {self.peer_ids_to_names(self.get_agents_by_role("team_manager"))}
                    - Team Member(s):  {self.peer_ids_to_names(self.get_agents_by_role("team_members"))}
                    - Expert(s):       {self.peer_ids_to_names(self.get_agents_by_role("expert"))}
                    - Brain(s):        {self.peer_ids_to_names(self.get_agents_by_role("brain"))}
                    
                    (Each slot is a comma-separated list of names. If a slot is empty or says
                    "none", that role has no one connected right now.)
                    
                    ## Role Behaviors
                    
                    - Team Manager: sets goals, assigns tasks, reviews results, decides next steps.
                    - Team Member: executes tasks. Queries a Brain for missed context, consults
                      an Expert for specialized input, then reports back to a Team Manager.
                    - Expert: provides specialized knowledge or analysis when asked by name.
                    - Brain: holds memory of previous conversations in this room. Returns prior
                      instructions, decisions, and context when queried by name.
                    
                    ## Expected Interaction Flow
                    
                    1. A Team Member unsure of current context asks a specific Brain by name to
                       retrieve relevant history (e.g., instructions left by a Team Manager while
                       the Member was offline).
                    2. With context in hand, the Team Member asks a specific Expert by name for
                       the information or analysis needed.
                    3. The Team Member reports results to a specific Team Manager by name and
                       requests further instructions.
                    4. The Team Manager responds with feedback or new assignments.
                    
                    ## Your Task Right Now
                    
                    Produce ONE short message (3-6 sentences) that re-activates the room:
                    
                    - Briefly acknowledge the pause (one line, neutral).
                    - Address participants BY NAME from the lists above.
                    - Default action: pick one Team Member and instruct them to (a) ask a named
                      Brain for recent context, then (b) consult a named Expert, then (c) report
                      to a named Team Manager.
                    - Give ONE concrete next step per addressed participant. No long lists.
                    
                    ## Selection Rules
                    
                    - Only address people whose names appear in the lists above. Never invent
                      names or address absent roles.
                    - If multiple people fill a role, pick ONE per step (the first listed is a
                      safe default unless chat history suggests a better match).
                    - If no Team Member is connected: instead prompt a Team Manager to outline
                      the next task for when a Member joins, or ask a Brain to summarize the
                      current state of work.
                    - If no Brain is connected: skip the context-recovery step and tell the
                      Team Member to ask the Team Manager directly for current priorities.
                    - If no Expert is connected: tell the Team Member to proceed with what they
                      know and flag the missing expertise to the Team Manager.
                    - If only one role is present, address that person with a sensible solo
                      action (e.g., a lone Team Manager: post the current priority; a lone
                      Brain: summarize the last decisions on record).
                    
                    ## Output Rules
                    
                    - Plain text only. No markdown headings, no code blocks, no role-play prose.
                    - Neutral, professional tone. Do not invent facts about the project.
                    - Do not answer on behalf of any participant. Only prompt them to act.
                    - Do not list the participants back; just address the ones you're prompting.
            """)

            self.stdin.set("proc_input_0", promote_prompt)

    @staticmethod
    def get_sender_name(msg: str):
        if msg.startswith("**"):
            tokens = msg.split("**")
            if len(tokens) == 3:
                return tokens[1]
        return None

    def peer_ids_to_names(self, _peer_ids: list[str], return_list: bool = False):
        _names = []
        for _peer_id in _peer_ids:
            if _peer_id in self.all_agents:
                _names.append(self.all_agents[_peer_id].get_static_profile()['node_name'])
        return (", ".join(_names) if len(_names) > 0 else "none") if not return_list else _names

    def is_human(self):
        return super().is_human() or (self.proc is not None and isinstance(self.proc.module, MultiIdentity))
