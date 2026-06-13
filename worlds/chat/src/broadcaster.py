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
from unaiverse.interaction import Interaction


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @action
    async def broadcast_message(self, interaction: Interaction | None = None) -> bool:
        """Custom 'process'-like action for the broadcaster.
        Reads the requester's text from stdin (which is bound, for this interaction's uuid, to the user's
        processor output stream), prepends the requester's display name, and direct-messages the prefixed
        text to every other user in the world by setting their local copy of the broadcaster's own processor
        output stream slot ('proc_output_0').

        The broadcaster keeps `proc=None` (no model) - the relay is fully manual, no super().process call."""
        if interaction is None:
            return False

        # If the requester disconnected mid-flight, drop the interaction silently (framework completes it).
        if interaction.requester not in self.all_agents:
            return True

        requester = interaction.requester
        assert requester is not None
        my_peer_id = self.get_peer_id()
        broadcaster_sender = self.all_agents[requester].get_static_profile()['node_name']

        log.misc(f"Broadcaster received a message from {requester} "
                 f"(agent named {broadcaster_sender}); "
                 f"world agents: {list(self.world_agents.keys())}, broadcaster peer ID: {my_peer_id}")

        # Fan out to every other user (excluding the original requester and self)
        other_users = list(set(self.world_agents.keys()) - {requester, my_peer_id})
        log.misc(f"Broadcaster relays the message of {broadcaster_sender} to {other_users}")

        if len(other_users) == 0:
            log.error("Broadcaster is skipping the relay: no recipients available")
            return True

        # Read the text written by the requester (the user's processor output forwarded under interaction.uuid)
        input_data = self.stdin.get(uuid=interaction.uuid, requested_by="broadcast_message")
        if input_data is None:
            return False
        msg = input_data[0] if isinstance(input_data, (tuple, list)) else input_data
        if not isinstance(msg, str):
            log.error(f"Broadcaster expected a string in stdin, got {type(msg).__name__}")
            return True

        prefixed_msg = f"**{broadcaster_sender}:** {msg}"

        # action_name=None: this is a pure data push, the recipient just stores 'proc_output_0' in its
        # known copy of our processor output stream — no HSM transition required on the receiver.
        return await self.send(target=other_users,
                               data_samples={"proc_output_0": prefixed_msg},
                               num_steps=1)
