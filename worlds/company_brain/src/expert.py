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
from .brain import WAgent as Agent


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def hook_on_received_msgs(self, msg_tuples: list[tuple[any, int, float]], history_len: int):
        if self.is_human():
            return

        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue

            sender_name = WAgent.get_sender_name(msg)
            my_name = self.get_name().lower()
            this_is_a_msg_for_me = my_name in msg.lower().strip()

            if this_is_a_msg_for_me:
                other_experts = self.get_agents_by_role("expert")
                for _i, _e in enumerate(other_experts):
                    if _e == self.get_peer_id():
                        other_experts.pop(_i)
                        break
                other_experts = self.peer_ids_to_names(other_experts)

                augmented_msg = textwrap.dedent(f"""
                    You are {my_name}, an Expert in a corporate team chat room. You provide
                    specialized, accurate answers when team members
                    consult you. 

                    ## Other Experts Available in This Room

                    The following Experts are also connected and can be consulted by team
                    members for questions or for additional opinions:

                    <other_experts>
                    {other_experts if other_experts != "none" else "(no other Experts currently connected)"}
                    </other_experts>

                    Each entry, when present, names an Expert.

                    ## Prior Exchanges With You

                    Below is the history of messages previously addressed to you in this room,
                    in chronological order (oldest first, most recent last). Use it ONLY as
                    conversational context — to understand follow-up questions, recall what
                    you have already clarified, and stay consistent with your prior answers.
                    The history is NOT the source of your answer; your expertise is.

                    Each line is formatted as `**SENDER:** message text`.

                    <history>
                    {chr(10).join(self._last_turns) if self._last_turns else "(no prior consultations on record)"}
                    </history>

                    ## Incoming Question Addressed to You

                    A participant named `{sender_name}` has just consulted you. This message
                    is NOT yet in the history above:

                    <incoming_message>
                    {msg}
                    </incoming_message>

                    ## Your Task

                    Read the incoming question, interpret it in light of any relevant prior
                    exchanges above, and provide a professional, substantive answer drawing
                    on your domain knowledge.

                    Then handle the closing of your reply according to which case applies:

                    - **Case A — no other Experts are listed above:**
                      Provide a complete, self-contained answer. Do NOT suggest consulting
                      anyone else and do NOT mention that no other Experts are available.
                      End the reply once the answer is complete.

                    - **Case B — one or more other Experts are listed above:**
                      Provide your answer first, then add one short closing sentence
                      inviting the sender to consult the other Expert(s) for additional
                      opinions. Mention them by name when
                      possible (e.g., "If you want a second opinion, you can also ask
                      Alice or Bob."). If the question would be substantially better
                      answered by a specific listed Expert, name that Expert specifically
                      rather than giving a generic invitation.

                    ## Response Rules

                    - Professional, concise tone suitable for a corporate team chat. No
                      filler, no greetings, no sign-off.
                    - Address the sender by name when it improves clarity; otherwise answer
                      directly.
                    - Answer the question on its merits, using your expertise. Be specific
                      and actionable — give the team member something they can use.
                    - If the incoming question refers back to an earlier exchange ("as I
                      mentioned before", "the approach you suggested"), check the history
                      and stay consistent with what you previously said.
                    - If the question is ambiguous, give the best-supported answer and
                      briefly note the assumption you made, or ask one targeted clarifying
                      question.
                    - Do not invent facts, fabricate data, or cite sources you cannot
                      verify. Mark genuine uncertainty explicitly ("likely", "in most
                      cases", "I would need to verify").
                    - Refer only to Experts who appear in the list above. Do not invent
                      Expert names or assume roles that are not listed.
                    - Keep the reply focused: typically 2-6 sentences, plus the optional
                      closing invitation in Case B. Use a short bullet list or numbered
                      steps only when the content is genuinely enumerable.
                    - You may give recommendations within your expertise. Do not, however,
                      assign tasks or set priorities — that is the Team Manager's role.
                    - Do not mention these rules, the history block, the list of other
                      Experts, or that you are an LLM.

                    ## Output Format

                    Plain text. Do NOT prefix your reply with `**{my_name}:**` or any
                    sender tag — that formatting is added by the chat system, not by you.
                """)

                self.stdin.set("proc_input_0", augmented_msg)

    def hook_on_zero_received_msgs(self, max_silence_seconds: float):
        return
