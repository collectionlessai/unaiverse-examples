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
from .brain import WAgent as Agent
from unaiverse.utils.logger import log


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        self.final_message = "Event logged. Resolution path stored in the Company World. I will surface this case automatically if a similar pattern reappears."
        super().__init__(*args, **kwargs)

    def hook_on_received_msgs(self, msg_tuples: list[tuple[any, int, float]], history_len: int):
        for msg, _, _ in msg_tuples:
            if not isinstance(msg, str):
                continue

            # If this message is from the HUMAN player, advance past HUMAN entries
            raw_message = self.get_raw_message(msg)
            if raw_message and raw_message == self.final_message:
                log.user("\U0001f4cb Knowledge Base updated: Type-B thermal event — Area B-3 — resolution stored.")


    def hook_on_zero_received_msgs(self, max_silence_seconds: float):
        return

    async def on_tick(self):
        agents_in_world = self.get_connection_pool_manager().world_agents_set
        for _agent in agents_in_world:
            if _agent in self._contacted or _agent == self.get_peer_id():
                continue
            if (not self.get_connection_pool_manager().is_connected(_agent) and
                    _agent not in self._node_agents_waiting and _agent not in self.world_agents):
                await self.connect_to(_agent)
                self._contacted.add(_agent)
