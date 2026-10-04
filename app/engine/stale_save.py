from __future__ import annotations

from typing import Iterable

from app.data.database.components import ComponentType
from app.utilities.typing import NID

class StaleSaveError(Exception):
    '''
    A save names something the project no longer has, most likely because it
    was renamed or deleted in the editor after the save was made. The save
    only stores the nid, so there is nothing to restore it from
    '''

def require(nid: NID, catalog: Iterable[NID], kind: str, owner: str):
    '''Raises a StaleSaveError naming owner if catalog has no kind called nid'''
    if nid not in catalog:
        raise StaleSaveError(
            "%s has %s '%s', but no %s with that nid was found in the database. "
            "Was it renamed or deleted after this save was made?" % (owner, kind, nid, kind))

def require_weapon_types(components, weapon_types: Iterable[NID], owner: str):
    '''
    Every item component whose value is a weapon type must name one the project
    has: combat looks the weapon type up to work out weapon advantage
    '''
    for component in components:
        if component.expose == ComponentType.WeaponType and component.value:
            require(component.value, weapon_types, 'weapon type', "%s's %s component" % (owner, component.nid))
