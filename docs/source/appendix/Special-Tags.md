(Special-Tags)=
# Special Tags

_last updated v0.1_

This appendix details every tag that the **Lex Talionis** engine handles uniquely. You can of course assign other tags to units and classes and check for them in your own event scripts or item/skill components.

Both units and classes can be assigned tags. A unit in game has it's own tags as well as the tags of it's class. 

**Lord** - If 'Autocursor' is **ON**, will be hovered over by the cursor when the player phase starts.

**Boss** - The unit will be designated as a boss. They will have a boss icon on their sprite, and give more EXP when defeated if the _Boss Bonus_ constant is set. 

**Required** - Unit must be chosen from among the list of available units to deploy in the Prep Screen.

**Blacklist** - Unit cannot be deployed for the chapter in the Prep Screen.

**Armor** - Denotes a unit as Armor. Affects movement SFX when the unit walks.

**Mounted** - Denotes a unit as Mounted. Affects movement SFX, as well as the Aid icon.

**Flying** - Denotes a unit as Flying. Affects movement SFX, as well as the Aid icon.

**SlowMove** - The unit/class walks across the map at half the usual pace, as the armored and robed classes of the GBA games do. This is only how fast the unit is shown moving: how far it can move is unchanged. An event that moves the unit at a speed of its own is unaffected.

**Dragon** - Denotes a unit as a Dragon. Used for the Aid icon.

**AutoPromote** - This unit/class will automatically promote if they level past their class's maximum level.

**NoAutoPromote** - This unit/class cannot promote via leveling up past their class's maximum level.

**Convoy** - Allows the unit/class to access the convoy during their turn.

**AdjConvoy** - Allows allies adjacent to the unit/class to access the convoy during their turn.

**Tile** - Denotes a unit should behave as a destructible tile. Unit cannot be selected, and will not show up in the Info Menu. Unit will also not be contained in most lists of units throughout the engine.

**Protect** - Unit will have the protect icon on their sprite.
