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
from unaiverse.world import World
from unaiverse.utils.logger import log
from unaiverse.utils.misc import build_unaid
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        super().__init__(world_folder=world_folder, **kwargs)

    def assign_role(self, profile: NodeProfile, is_world_master: bool):
        if is_world_master:
            return "teacher" if len(self.world_masters) <= 1 else "student"
        return "student"

    def create_behav_files(self):
        """Render the role-behavior PDFs from the pre-authored JSON files."""
        from .student import WAgent as StudentAgent
        from .teacher import WAgent as TeacherAgent

        # Teacher
        behav = HybridStateMachine(TeacherAgent(proc=None))
        behav.load(os.path.join(str(self.world_folder), 'teacher.json'))
        behav.save_pdf(os.path.join(str(self.world_folder), 'pdf/teacher.pdf'))

        # Student
        behav = HybridStateMachine(StudentAgent(proc=None))
        behav.load(os.path.join(str(self.world_folder), 'student.json'))
        behav.save_pdf(os.path.join(str(self.world_folder), 'pdf/student.pdf'))

    def _process_custom_stat(self, stat_name, value, peer_id, timestamp):
        """Track the best overall student accuracy across all agents."""
        if stat_name != 'accuracy':
            return False

        world_peer_id = self.get_peer_ids()[1]
        assert self.stats is not None
        self.stats.store_stat('accuracy', value, group_key=world_peer_id, timestamp=timestamp)

        overall_best_accuracy = self.stats.get_last_value('accuracy')
        assert overall_best_accuracy is not None
        overall_best_accuracy: float
        value: float
        if overall_best_accuracy == -1.0 or (value > overall_best_accuracy and peer_id in self.all_agents):
            unaid = build_unaid(self.all_agents[peer_id])
            self.stats.store_stat('overall_best_student', unaid, group_key=world_peer_id, timestamp=timestamp)
            log.user(f"[WStats] New overall best exam error: {value} by {peer_id}")

            badge = {
                'peer_id': peer_id,
                'score': value,
                'badge_type': "completed",
                'badge_description': "LOT2.0 champion!",
                'agent_token': self.node_conn.get_last_token(peer_id)
            }
            self.add_badge(**badge)
        return True
