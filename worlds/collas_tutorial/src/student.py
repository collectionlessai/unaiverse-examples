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
import json
import random
from unaiverse.utils.logger import log
from unaiverse.agent import Agent, action
from unaiverse.interaction import Interaction


class WAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @action
    async def init(self):
        block = {
            "v": 1,
            "type": "media",
            "src": "https://lifelong-ml.cc/images/logo.png",
            "mime": "image/png",
            "alt": "(Conference Logo: https://lifelong-ml.cc/images/logo.png)"
        }
        title = ("**Lifelong Learning in Peer-to-Peer Communities of Human and AI Agents**\n\n"
                 "Stefano Melacci, Tommaso Guidi, Christian Di Maio")
        log.user(f"{title}\n\n```uai\n{json.dumps(block, ensure_ascii=False)}\n```")
        return True

    @action
    async def print(self, msg: str, interaction: Interaction | None = None):
        if interaction is None:
            return False
        log.user(msg)
        return True

    @staticmethod
    def one_at_random(addresses: list[list[str]], peer_ids: list[str]):
        if addresses is None or len(addresses) == 0:
            return addresses, peer_ids
        assert len(peer_ids) == len(addresses)
        p = random.randrange(len(peer_ids))
        return [addresses[p]], [peer_ids[p]]
