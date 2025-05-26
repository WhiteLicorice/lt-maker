from typing import Optional, Tuple
from app.utilities.typing import NID, Pos

from app.events.regions import RegionType, Region

class RegionObject(Region):
    """
    A region object in the game. Not the same as a Region Prefab, which is the unchanging Region you created in the level editor. 

    Inherits from the Region Prefab to access Region's helper functions like area and center.

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

    def __init__(self, nid: NID, region_type: RegionType, 
                 position: Pos = None, size: Tuple[int, int] = [1, 1], 
                 sub_nid: str = None, condition: str = 'True', time_left: Optional[int] = None,
                 only_once: bool = False, interrupt_move: bool = False, hide_time: bool = False):
        self.nid = nid
        self.region_type = region_type
        self.position = tuple(position) if position else None
        self.size = size

        self.sub_nid = sub_nid
        self.condition: str = condition
        self.time_left: Optional[int] = time_left
        self.only_once: bool = only_once
        self.interrupt_move: bool = interrupt_move
        
        self.hide_time: bool = hide_time

        self.data = {}

    @classmethod
    def from_prefab(cls, prefab):
        return cls(prefab.nid, prefab.region_type, prefab.position, prefab.size,
                   prefab.sub_nid, prefab.condition, prefab.time_left,
                   prefab.only_once, prefab.interrupt_move, prefab.hide_time)

    def save(self) -> dict:
        serial_dict = {}
        serial_dict['nid'] = self.nid
        serial_dict['region_type'] = self.region_type
        serial_dict['position'] = self.position
        serial_dict['size'] = self.size
        serial_dict['sub_nid'] = self.sub_nid
        serial_dict['condition'] = self.condition
        serial_dict['time_left'] = self.time_left
        serial_dict['only_once'] = self.only_once
        serial_dict['interrupt_move'] = self.interrupt_move
        serial_dict['hide_time'] = self.hide_time

        serial_dict['data'] = self.data
        return serial_dict

    @classmethod
    def restore(cls, dat: dict):
        self = cls(dat['nid'], dat['region_type'], dat['position'], dat['size'],
                   dat['sub_nid'], dat['condition'], dat['time_left'],
                   dat['only_once'], dat['interrupt_move'], dat.get('hide_time', False))
        self.data = dat['data']
        return self
