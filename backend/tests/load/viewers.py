"""
Simulated Viewers and Viewer Pools for Multi-Stream Load Testing.

Maintains deterministic viewer entities, isolated per stream, with distinct roles and behaviors.
"""

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional


@dataclass
class SimulatedViewer:
    """Represents a deterministic simulated YouTube live viewer."""
    viewer_id: str
    name: str
    stream_id: str
    role: str = "VIEWER"  # VIEWER, MODERATOR, OWNER
    is_vip: bool = False
    join_time_s: float = 0.0
    message_count: int = 0
    last_message_time_s: float = 0.0

    @property
    def is_mod(self) -> bool:
        return self.role in ("MODERATOR", "OWNER")

    @property
    def is_owner(self) -> bool:
        return self.role == "OWNER"


class ViewerPool:
    """Manages a pool of simulated viewers for a specific stream."""

    def __init__(self, stream_id: str, count: int = 200, seed: int = 42):
        self.stream_id = stream_id
        self.count = count
        self.rng = random.Random(seed)
        self.viewers: List[SimulatedViewer] = []
        self._generate_pool()

    def _generate_pool(self) -> None:
        """Create deterministic viewers with a realistic role breakdown."""
        # 1 Owner, ~4 Mods, ~10 VIPs, remaining standard Viewers
        for idx in range(self.count):
            v_id = f"user_{self.stream_id}_{idx:04d}"
            name = f"Viewer_{self.stream_id}_{idx}"
            
            if idx == 0:
                role = "OWNER"
                is_vip = True
            elif idx <= 4:
                role = "MODERATOR"
                is_vip = True
            elif idx <= 14:
                role = "VIEWER"
                is_vip = True
            else:
                role = "VIEWER"
                is_vip = False

            viewer = SimulatedViewer(
                viewer_id=v_id,
                name=name,
                stream_id=self.stream_id,
                role=role,
                is_vip=is_vip,
            )
            self.viewers.append(viewer)

    def get_random_viewer(self) -> SimulatedViewer:
        """Pick a viewer deterministically."""
        return self.rng.choice(self.viewers)

    def get_viewers_by_role(self, role: str) -> List[SimulatedViewer]:
        return [v for v in self.viewers if v.role == role]
