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
from .stats import WStats
from unaiverse.world import World
from unaiverse.utils.logger import log
from unaiverse.utils.misc import build_unaid
from unaiverse.hsm import HybridStateMachine
from unaiverse.networking.node.profile import NodeProfile


class WWorld(World):

    def __init__(self, **kwargs):
        world_folder = os.path.dirname(os.path.abspath(__file__))
        stats = WStats(is_world=True, db_path=os.path.join(world_folder, "stats", "world_stats.db"))
        super().__init__(world_folder=world_folder, stats=stats, **kwargs)

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
            return False  # per-class stats etc.: let the framework store them normally

        assert self.stats is not None
        world_peer_id = self.get_peer_ids()[1]

        # 1. Read the previous best BEFORE storing anything (ungrouped world-level key)
        prev_best = self.stats.get_last_value('overall_best_accuracy')  # None or float (schema default -1.0)

        # 2. Store the per-student accuracy under the student's own group key
        #    (we returned True, so default processing is skipped — this is on us)
        self.stats.store_stat('accuracy', value, group_key=peer_id, timestamp=timestamp)

        # 3. New champion?
        value: float
        if (prev_best is None or (isinstance(prev_best, (int, float)) and (prev_best < 0.0 or value > prev_best)) and
                peer_id in self.all_agents):
            unaid = build_unaid(self.all_agents[peer_id])
            self.stats.store_stat('overall_best_accuracy', float(value), group_key=world_peer_id, timestamp=timestamp)
            self.stats.store_stat('overall_best_student', unaid, group_key=world_peer_id, timestamp=timestamp)
            log.user(f"[WStats] New overall best exam accuracy: {value} by {unaid}")
            self.add_badge(peer_id=peer_id, score=value, badge_type="completed",
                           badge_description="LOT2.0 champion!",
                           agent_token=self.node_conn.get_last_token(peer_id))
        return True
