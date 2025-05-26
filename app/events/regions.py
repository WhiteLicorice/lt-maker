from typing import List, Optional, Tuple
from app.utilities.typing import NID, Pos

from enum import Enum
from app.utilities.data import Prefab

class RegionType(str, Enum):
    NORMAL = 'normal'
    STATUS = 'status'
    EVENT = 'event'
    FORMATION = 'formation'
    FOG = 'fog'
    VISION = 'vision'
    TERRAIN = 'terrain'

class Region(Prefab):
    """
    A region prefab that has not been instantiated as a Region Object yet

    Attributes:
        nid (NID): The unique identifier for the region object.
        region_type (RegionType): The type of region (Event, Formation, etc.).
        position (Pos): The position of the region object. Defaults to None.
        size (Tuple[int, int]): The size of the region object in tiles. Defaults to [1, 1].
        sub_nid (str): Extra data for the region object. Defaults to None.
        condition (str): The condition for the region object to be enabled. Defaults to 'True'.
        time_left (Optional[int]): The number of turns left for the region object. Defaults to None, which means it is permanent.
        only_once (bool): Flag indicating if the region object triggers only once. Defaults to False.
        interrupt_move (bool): Flag indicating if the region object interrupts movement. Defaults to False. Set to True for things like an FE `Mine` or for Free Roam events
        hide_time (bool): Flag whether to hide the region's duration indicator.
    """
    def __init__(self, nid: NID):
        self.nid: NID = nid
        self.region_type: RegionType = RegionType.NORMAL
        self.position: Pos = None
        self.size: Tuple[int, int] = [1, 1]

        self.sub_nid: str = None
        self.condition: str = 'True'
        self.time_left: Optional[int] = None
        self.only_once: bool = False
        self.interrupt_move: bool = False
        
        self.hide_time: bool = False

    @classmethod
    def restore(cls, s_dict):
        self = super(Region, cls).restore(s_dict)
        # Move time left from sub_nid
        # to time left parameter
        if s_dict['region_type'] == 'time':
            self.time_left = self.sub_nid
            self.sub_nid = None
        return self

    def restore_attr(self, name, value):
        if name == 'region_type':
            # Replace deprecated time region with normal region
            if value == 'time':
                value = 'normal'
            value = RegionType(value)
        else:
            value = super().save_attr(name, value)
        return value

    @property
    def area(self) -> int:
        """
        Calculate the area of the region.

        Returns:
            int: The area of the region (width x height tiles).
        """
        return self.size[0] * self.size[1]

    @property
    def center(self) -> Pos:
        """
        Calculate the center position of the region.

        Returns:
            Pos: The center position of the region.
        """
        if self.position:
            x = int(self.position[0] + self.size[0] // 2)
            y = int(self.position[1] + self.size[1] // 2)
            return x, y
        else:
            return None

    def contains(self, pos: Pos) -> bool:
        """
        Check if the given position is within the region.

        Args:
            pos (Pos): The position to check.

        Returns:
            bool: True if the position is within the region, False otherwise.
        """
        x, y = pos
        if self.position:
            return self.position[0] <= x < self.position[0] + self.size[0] and \
                self.position[1] <= y < self.position[1] + self.size[1]
        else:
            return False

    def get_all_positions(self) -> List[Pos]:
        """
        Get all positions covered by the region.

        Returns:
            List[Pos]: A list of all positions covered by the region.
        """
        if self.position:
            positions = []
            for i in range(self.position[0], self.position[0] + self.size[0]):
                for j in range(self.position[1], self.position[1] + self.size[1]):
                    positions.append((i, j))
            return positions
        else:
            return []

    @classmethod
    def default(cls):
        return cls('None')
