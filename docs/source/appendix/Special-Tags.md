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

## Map Step Sounds

When a unit walks across the map, it plays step sounds. The tags below choose which. A unit with none of them sounds like infantry.

| Tag | Sound effect(s) played |
| --- | --- |
| **Mogall** | `Map_Step_Mogall` |
| **Zombie** | `Map_Step_Zombie` |
| **Skeleton** | `Map_Step_Skeleton` |
| **Spider** | `Map_Step_Bael` |
| **Dog** | `Map_Step_Tarvos` |
| **Gorgon** | `Map_Step_Gorgon` |
| **Manakete** | `Map_Step_Manakete` |
| **Boat** | `Map_Step_Boat` |
| **Flying** | `Map_Step_Flier` |
| **Mounted** | `Map_Step_Mounted1`, `Map_Step_Mounted2`, `Map_Step_Mounted3` |
| **Armor** | `Map_Step_Armor1`, `Map_Step_Armor2` |
| _(none of these)_ | `Map_Step_Infantry1`, `Map_Step_Infantry2` |

If a unit has more than one of these tags, the one highest in the table wins. So a unit tagged both **Manakete** and **Flying** sounds like a manakete, and a unit tagged both **Mounted** and **Armor** sounds mounted.

The sounds are looked up by name in your project's sound effects. The default project has them all, and tags its zombie, skeleton and manakete classes. Despite its name, `Map_Step_Tarvos` is the GBA's Mauthe Doog walk; a Tarvos on the GBA walks with the mounted steps.
