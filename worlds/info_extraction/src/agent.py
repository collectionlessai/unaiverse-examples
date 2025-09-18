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
import json
import torch
from PIL.Image import Image
from unaiverse.agent import Agent
from unaiverse.dataprops import DataProps


class WAgent(Agent):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__exploited_extractors = set()  # it must start with "__" to avoid automatic agent clearing at removal
        self._extracted_info = {}
        self._first_check = True
        self._got_new_info = False

    def check_status(self):
        self.disengage_all()

        if self.get_current_role() == "extractor":
            self.disconnect_by_role("user")

        elif self.get_current_role() == "user":
            self.disconnect_by_role("extractor")

            if not os.path.exists("extracted_info.json"):
                self._first_check = False

                # If we removed the JSON file, we assume we want to start over, so we re-enable all the extractors
                self.out("Clearing all the information extracted so far and restarting")
                self.__exploited_extractors = set()
                self._extracted_info = {}

                # Creating an "empty" file (required to mark the start of the process)
                with open("extracted_info.json", "w") as f:
                    json.dump(self._extracted_info, f, indent=4)

            elif self._first_check:
                self._first_check = False
                self.out("Loading data from extracted_info.json...")
                with open("extracted_info.json") as f:
                    self._extracted_info = json.load(f)
                self.out(f"Loaded {len(self._extracted_info)} entries.")
            else:

                # Saving the extracted information
                self.out("*** Information extracted so far ***")
                self.out(str(self._extracted_info) + "\n")
                if self._got_new_info:
                    self._got_new_info = False
                    self.out("Saving data to extracted_info.json...")
                    with open("extracted_info.json", "w") as f:
                        json.dump(self._extracted_info, f, indent=4)
                    self.out(f"Saved {len(self._extracted_info)} entries.")

        return True

    def filter_addresses(self, addrs: list[list[str]], peer_ids: list[str]):
        filtered_addrs = []
        filtered_peer_ids = []
        for addr, peer_id in zip(addrs, peer_ids):
            if peer_id not in self.__exploited_extractors:
                filtered_addrs.append(addr)
                filtered_peer_ids.append(peer_id)
        return filtered_addrs, filtered_peer_ids

    def handle_received_data(self, agent: str, props: DataProps, data: torch.Tensor | str | Image, data_tag: int):
        info = props.to_text(data)
        profile = self.all_agents[agent]
        static_profile = profile.get_static_profile()
        node_id = static_profile['node_id']

        self.out(f"Got new information from {agent} (node id: {node_id}) on data tagged with {data_tag}: {info}")
        self.__exploited_extractors.add(agent)

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
            self.out(f"Stored new information from {agent} (node id: {node_id}) on data tagged with {data_tag}: {info}")
