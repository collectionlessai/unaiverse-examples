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
from unaiverse.world import World
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        super().__init__(world_folder=world_folder, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        """This method implements the criterion the world uses to assign a role to every joining agent."""
        return "teacher" if is_world_master else "student"  # Simple criterion: if world master, then 'teacher'

    def create_behav_files(self):
        """Create role-behavior JSON files (for now: welcome messages and a single idle state, nothing else)."""
        assert self.world_folder is not None
        sys.path.append(self.world_folder)

        # [Teacher] Creating a dummy teacher agent and an empty Hybrid State Machine (HSM)
        from .teacher import WAgent as WAgentTeacher
        dummy_agent = WAgentTeacher(proc=None)
        behav = HybridStateMachine(dummy_agent)

        # [Teacher] Marking the HSM with the role and with the welcome message displayed when joining the world
        behav.set_role("teacher")
        behav.set_welcome_message("🎓 Welcome to our tutorial at CoLLAs 2026! Your role: teacher")

        # [Teacher] A single (empty) state: the agent will simply idle there, after printing the welcome message
        behav.add_state("init", blocking=True)

        # [Teacher] Saving the just created HSM to a JSON file with the same name of the one hosting the class
        behav.save(os.path.join(self.world_folder, 'teacher.json'), only_if_changed=dummy_agent)

        # [Student] Same as above, for the student role
        from .student import WAgent as WAgentStudent
        dummy_agent = WAgentStudent(proc=None)
        behav = HybridStateMachine(dummy_agent)
        behav.set_role("student")
        behav.set_welcome_message("🎓 Welcome to our tutorial at CoLLAs 2026! Your role: student")
        behav.add_state("init", blocking=True)
        behav.save(os.path.join(self.world_folder, 'student.json'), only_if_changed=dummy_agent)
