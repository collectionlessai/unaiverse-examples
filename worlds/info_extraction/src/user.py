"""
       █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
      ░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
       ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░
       ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████
       ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█
       ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
       ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
        ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░  ░░░░░░░░░░
                 A Collectionless AI Project (https://collectionless.ai)
                 Registration/Login: https://unaiverse.io
                 Code Repositories:  https://github.com/collectionlessai/
                 Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""
import os
import json
import torch
from PIL.Image import Image
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.streams.dataprops import DataProps


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Bookkeeping for the connect_by_role(filter_fcn=...) call: do not re-pick the same extractor twice in
        # a row. Double-underscore name avoids automatic clearing on agent (extractor) removal.
        # Notice, here we are talking about OTHER agents possibly leaving the world and rejoining, and NOT this
        # agent we are modeling here.
        self.__exploited_extractors = set()

        # Information accumulated by handle_received_data() (called by 'received_some_asked_data').
        # Fine if they get cleared on world leave.
        self._extracted_info = {}
        self._first_check = True
        self._got_new_info = False

    @action
    async def check_status(self) -> bool:
        """At the start of every cycle: drop stale engagements/connections and either initialize, load or
        persist 'extracted_info.json'."""
        await self.disengage_all()
        await self.disconnect_by_role("extractor")

        if not os.path.exists("extracted_info.json"):
            self._first_check = False

            # If the JSON file was removed, we assume we want to start over -> re-enable all the extractors
            log.user("Clearing all the information extracted so far and restarting")
            self.__exploited_extractors = set()
            self._extracted_info = {}

            # Create an "empty" file (required to mark the start of the process)
            with open("extracted_info.json", "w") as f:
                json.dump(self._extracted_info, f, indent=4)

        elif self._first_check:
            self._first_check = False
            log.user("Loading data from extracted_info.json...")
            with open("extracted_info.json") as f:
                self._extracted_info = json.load(f)
            log.user(f"Loaded {len(self._extracted_info)} entries.")
        else:

            # Save the extracted information
            if self._got_new_info:
                self._got_new_info = False
                log.user("Saving data to extracted_info.json...")
                with open("extracted_info.json", "w") as f:
                    json.dump(self._extracted_info, f, indent=4)
                log.user(f"Saved {len(self._extracted_info)} entries.")
        return True

    def filter_addresses(self, addrs: list[list[str]], peer_ids: list[str]):
        """This is a connect_by_role filter: drop extractors we have already exploited in a previous round."""
        filtered_addrs = []
        filtered_peer_ids = []
        for addr, peer_id in zip(addrs, peer_ids):
            if peer_id not in self.__exploited_extractors:
                filtered_addrs.append(addr)
                filtered_peer_ids.append(peer_id)
        return filtered_addrs, filtered_peer_ids

    def handle_received_data(self, agent: str, props: DataProps, data: torch.Tensor | str | Image, data_tag: int):
        """This part of action received_some_asked_data: record one piece of extracted information from 'agent'."""

        # Guard
        if agent not in self.all_agents:
            return

        info = props.to_text(data, ignore_raw_tensors=True)
        profile = self.all_agents[agent]
        static_profile = profile.get_static_profile()
        node_id = static_profile['node_id']

        log.user(f"Got new information from {agent} (node id: {node_id}) on data tagged with {data_tag}: {info}")
        self.__exploited_extractors.add(agent)  # We early blacklist, even if info is None

        if info is not None:
            self._got_new_info = True
            data_tag_str = str(data_tag)  # Keep it as string, more JSON dump/load friendly
            extractor_str = (f"{static_profile['node_name']}: {static_profile['node_description']} "
                             f"({len(profile.get_cv())} badges)")

            if data_tag_str not in self._extracted_info:
                self._extracted_info[data_tag_str] = {node_id: {"info": [], "extractor": extractor_str}}
            else:
                if node_id not in self._extracted_info[data_tag_str]:
                    self._extracted_info[data_tag_str][node_id] = {"info": [], "extractor": extractor_str}

            self._extracted_info[data_tag_str][node_id]["info"].append(info)
