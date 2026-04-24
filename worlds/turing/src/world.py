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
import sys
from .stats import WStats
from .config import Config
from unaiverse.world import World
from unaiverse.utils.logger import log
from unaiverse.hsm import HybridStateMachine
from unaiverse.utils.misc import FileTracker, build_unaid
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

        # List of hotel and floor managers (they are dynamically updated from file "managers.txt")
        self.hotel_managers = set()
        self.floor_managers = set()

        # Loading lists of hotel and floor managers from "managers.txt"
        self.load_managers_from_file()

        # Tracking changes to file "managers".txt (to update the lists when the file changes)
        self.managers_file_tracker = FileTracker(folder=world_folder, ext=".txt", prefix="managers.txt")

    def assign_role(self, profile: NodeProfile, is_world_master: bool):

        # If "managers.txt" changed, reload file
        if self.managers_file_tracker.something_changed():
            self.load_managers_from_file()

        # Role is assigned in function of the contents of the lists of hotel and floor managers
        unaid = build_unaid(profile)
        if unaid in self.hotel_managers:
            log.user(f"Assigning role of hotel manager to: {unaid}")
            return "hotel_manager"
        if unaid in self.floor_managers:
            log.user(f"Assigning role of floor manager to: {unaid}")
            return "floor_manager"
        log.user(f"Assigning role of guest to: {unaid}")
        return "guest"

    def load_managers_from_file(self):
        """Load list of managers from file (CSV file, every line is: floor|manager,unaid)."""
        with open(os.path.join(self.world_folder, "managers.txt"), "r") as f:
            managers = {line.strip() for line in f}
            for manager in managers:
                manager = manager.strip()
                if not manager or "," not in manager:  # Skip blanks/malformed
                    log.user("Skipping line from managers.txt file: empty or malformed")
                    continue
                _type, _unaid = manager.split(",")
                if _type.lower().strip() == "floor":
                    log.user(f"Adding floor manager: {_unaid}")
                    self.floor_managers.add(_unaid.strip())
                elif _type.lower().strip() == "hotel":
                    log.user(f"Adding hotel manager: {_unaid}")
                    self.hotel_managers.add(_unaid.strip())
                else:
                    log.error(f"Invalid line in managers.txt file (skipping): {manager}")

    def create_behav_files(self):
        """Create role-behavior JSON files."""
        sys.path.append(self.world_folder)

        # ROLE 1/3: hotel manager
        from .hotel_manager import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("hotel_manager")
        behav.set_welcome_message("Welcome to the Turing Hotel 🏨, we always need more managers, "
                                  "happy to have you here!")

        behav.add_state("init", blocking=True)
        behav.add_state("discovery_complete", blocking=False)
        behav.add_state("checked_in", blocking=False)
        behav.add_state("ready_for_news", blocking=True)
        behav.add_state("hotel_updated", blocking=False)
        behav.add_state("votes_processed", blocking=False)

        behav.add_transit("init", "discovery_complete", action="discover_floor_managers")
        behav.add_transit("init", "discovery_complete", action="nop", teleport=True)
        behav.add_transit("discovery_complete", "discovery_complete",
                          action="guest_back_to_hall", ready=False)
        behav.add_transit("discovery_complete", "checked_in", action="check_in")
        behav.add_transit("discovery_complete", "ready_for_news", action="nop", teleport=True)
        behav.add_transit("checked_in", "ready_for_news", action="send_to_floor")
        behav.add_transit("checked_in", "ready_for_news", action="nop", teleport=True)
        behav.add_transit("ready_for_news", "hotel_updated", action="update_hotel")
        behav.add_transit("ready_for_news", "votes_processed", action="get_votes")
        behav.add_transit("ready_for_news", "init", action="nop", teleport=True)
        behav.add_transit("hotel_updated", "votes_processed", action="get_votes")
        behav.add_transit("hotel_updated", "votes_processed", action="nop", teleport=True)
        behav.add_transit("votes_processed", "init", action="send_violations")
        behav.add_transit("votes_processed", "init", action="nop", teleport=True)

        if behav.save(os.path.join(self.world_folder, 'hotel_manager.json'), only_if_changed=dummy_agent):
            behav.save_pdf(os.path.join(self.world_folder, 'pdf', 'hotel_manager.pdf'))

        # ROLE 2/3: floor manager
        from .floor_manager import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("floor_manager")
        behav.set_welcome_message("Welcome to the Turing Hotel 🏨, we always need more floors, "
                                  "happy to have you here!")

        behav.add_state("init", blocking=True)
        behav.add_state("getting_sponsorships", blocking=False)
        behav.add_state("checked_in", blocking=False)
        behav.add_state("ready_to_send_news", blocking=False)
        behav.add_state("guests_status_updated", blocking=False)
        behav.add_state("floor_updates_shared", blocking=False)
        behav.add_state("votes_sent", blocking=False)
        behav.add_state("collect_msgs", blocking=False)

        behav.add_transit("init", "getting_sponsorships", action="nop")
        behav.add_transit("getting_sponsorships", "getting_sponsorships", action="get_guest_sponsor",
                          ready=False)
        behav.add_transit("getting_sponsorships", "checked_in", action="check_in")
        behav.add_transit("getting_sponsorships", "ready_to_send_news", action="nop", teleport=True)
        behav.add_transit("checked_in", "ready_to_send_news", action="send_to_room")
        behav.add_transit("checked_in", "ready_to_send_news", action="nop", teleport=True)
        behav.add_transit("ready_to_send_news", "guests_status_updated",
                          action="handle_guests_by_status")
        behav.add_transit("ready_to_send_news", "guests_status_updated", action="nop", teleport=True)
        behav.add_transit("guests_status_updated", "floor_updates_shared",
                          action="pub_floor_updates")
        behav.add_transit("guests_status_updated", "floor_updates_shared",
                          action="nop", teleport=True)
        behav.add_transit("floor_updates_shared", "votes_sent", action="send_votes")
        behav.add_transit("floor_updates_shared", "votes_sent", action="nop", teleport=True)
        behav.add_transit("votes_sent", "collect_msgs", action="apply_violations", ready=False)
        behav.add_transit("votes_sent", "collect_msgs", action="nop", teleport=True)
        behav.add_transit("collect_msgs", "collect_msgs", action="get_msg_and_broadcast", ready=False)
        behav.add_transit("collect_msgs", "init", action="nop", teleport=True)

        if behav.save(os.path.join(self.world_folder, 'floor_manager.json'), only_if_changed=dummy_agent):
            behav.save_pdf(os.path.join(self.world_folder, 'pdf', 'floor_manager.pdf'))

        # ROLE 3/3: guest
        from .guest import WAgent
        dummy_agent = WAgent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("guest")
        behav.set_welcome_message("Welcome to the Turing Hotel 🏨, it's amazing to have a new guest!")

        behav.add_state("init", action="init", blocking=False)
        behav.add_state("ready", blocking=True, msg="🔗 Connecting to a randomly selected hotel manager")
        behav.add_state("wait_for_ready", blocking=False, msg="⏳ Waiting outside (decompression)")
        behav.add_state("reached_hotel_manager", blocking=False,
                        msg="🏢 Entered the hotel (hotel manager contacted)")
        behav.add_state("hall", blocking=False, msg="🏢 Walking though the hall (waiting to be sent to a floor)")
        behav.add_state("wait_for_hall", blocking=False, msg="⏳ Waiting in the hall (decompression)")
        behav.add_state("reached_floor_manager", blocking=False,
                        msg="🪜 Going upstairs (floor manager contacted)")
        behav.add_state("floor", blocking=False, msg="🪜 Reached the right floor (waiting to be sent to a room)")
        behav.add_state("ready_for_room", blocking=False)
        behav.add_state("room_round_table", blocking=True)
        behav.add_state("msg_prepared", blocking=False)
        behav.add_state("room_voting_booth", blocking=True,
                        msg="🗳 Entered the voting booth (waiting for vote request)")
        behav.add_state("vote_provided", blocking=True, msg="✅ Vote provided")

        behav.add_transit("init", "ready", action="process", args={},
                          avoid_changing_ready=True)
        behav.add_transit("init", "ready", action="skip_confirmation")
        behav.add_transit("ready", "reached_hotel_manager", action="connect_to_hotel_manager")
        behav.add_transit("reached_hotel_manager", "hall", action="hotel_manager_ack", args={})
        behav.add_transit("reached_hotel_manager", "wait_for_ready",
                          action="disconnect_hotel_manager",
                          args={}, delay=Config.disconnect_non_responsive_managers_after, teleport=True)
        behav.add_transit("wait_for_ready", "ready", action="nop",
                          args={}, delay=Config.decompression_time, teleport=True)
        behav.add_transit("hall", "reached_floor_manager", action="connect_to_floor_manager", args={},
                          ready=False)
        behav.add_transit("reached_floor_manager", "floor", action="floor_manager_ack", args={})
        behav.add_transit("reached_floor_manager", "wait_for_hall",
                          action="disconnect_floor_manager", args={},
                          delay=Config.disconnect_non_responsive_managers_after, teleport=True)
        behav.add_transit("wait_for_hall", "hall", action="nop",
                          args={}, delay=Config.decompression_time, teleport=True)
        behav.add_transit("floor", "ready_for_room", action="send_guest_sponsor", args={})
        behav.add_transit("ready_for_room", "room_round_table", action="goto_room", args={},
                          msg="💬 Entered the room, sitting at the chat table (waiting for the start message)",
                          ready=False)
        behav.add_transit("room_round_table", "msg_prepared", action="process", args={},
                          avoid_changing_ready=True, high_priority=True)
        behav.add_transit("room_round_table", "room_round_table", action="get_msgs", args={})
        behav.add_transit("room_round_table", "room_round_table", action="get_status_msg", args={},
                          ready=False)
        behav.add_transit("room_round_table", "room_voting_booth", action="goto_voting_booth",
                          args={}, ready=False)
        behav.add_transit("msg_prepared", "room_round_table", action="send_msg", args={})
        behav.add_transit("room_voting_booth", "room_voting_booth", action="get_status_msg", args={},
                          ready=False)
        behav.add_transit("room_voting_booth", "vote_provided", action="process", args={},
                          ready=False)
        behav.add_transit("room_voting_booth", "hall", action="goto_hall", args={}, ready=False)
        behav.add_transit("vote_provided", "hall", action="goto_hall", args={}, ready=False)

        if behav.save(os.path.join(self.world_folder, 'guest.json'), only_if_changed=dummy_agent):
            behav.save_pdf(os.path.join(self.world_folder, 'pdf', 'guest.pdf'))
