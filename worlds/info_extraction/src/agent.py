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


class IERoles:
    # Role bitmasks
    ROLE_USER = 1 << 2
    ROLE_EXTRACTOR = 1 << 3

    # Feasible roles
    ROLE_BITS_TO_STR = {
        # The base roles will be inherited from AgentBasics later
        ROLE_USER: "user",
        ROLE_EXTRACTOR: "extractor"
    }


class WAgent(Agent, IERoles):
    # feasible roles
    ROLE_BITS_TO_STR = {**Agent.ROLE_BITS_TO_STR, **IERoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._exploited_extractors = set()
        self._extracted_info = {}
        self._first_check = True
        self._got_new_info = False

    def check_status(self):
        self.disengage_all()

        if self.get_current_role(return_int=True) == self.ROLE_EXTRACTOR:
            self.disconnect_by_role(self.ROLE_BITS_TO_STR[self.ROLE_USER])

        elif self.get_current_role(return_int=True) == self.ROLE_USER:
            for agent in self._agents_who_completed_what_they_were_asked:
                self._exploited_extractors.add(agent)  # do this before disconnecting!

            self.disconnect_by_role(self.ROLE_BITS_TO_STR[self.ROLE_EXTRACTOR])

            if not os.path.exists("extracted_info.json"):
                self._first_check = False

                # if we removed the JSON file, we assume we want to start over, so we re-enable all the extractors
                self.out("Clearing all the information extracted so far and restarting")
                self._exploited_extractors = set()
                self._extracted_info = {}

                # creating an "empty" file (required to mark the start of the process)
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
            if peer_id not in self._exploited_extractors:
                filtered_addrs.append(addr)
                filtered_peer_ids.append(peer_id)
        return filtered_addrs, filtered_peer_ids

    def handle_received_data(self, agent: str, props: DataProps, data: torch.Tensor | str | Image, data_tag: int):
        info = props.to_text(data)
        profile = self.all_agents[agent]
        static_profile = profile.get_static_profile()
        node_id = static_profile['node_id']

        self.out(f"Got new information from {agent} (node id: {node_id}) on data tagged with {data_tag}: {info}")

        if info is not None:
            self._got_new_info = True
            data_tag_str = str(data_tag)  # keep it as string, more JSON dump/load friendly
            extractor_str = (f"{static_profile['node_name']}: {static_profile['node_description']} "
                             f"({len(profile.get_cv())} badges)")

            if data_tag_str not in self._extracted_info:
                self._extracted_info[data_tag_str] = {node_id: {"info": [], "extractor": extractor_str}}
            else:
                if node_id not in self._extracted_info[data_tag_str]:
                    self._extracted_info[data_tag_str][node_id] = {"info": [], "extractor": extractor_str}

            self._extracted_info[data_tag_str][node_id]["info"].append(info)
            self.out(f"Stored new information from {agent} (node id: {node_id}) on data tagged with {data_tag}: {info}")
