# Nihil
In ordinary Fire Emblem, Nihil negates the effects of certain skills so that they cannot be used against the bearer of Nihil.

With a custom component, we can achieve a similar effect. As one would imagine, this makes use of the `condition` hook.

Unfortunately, because the `condition` hook does not work in combat, this requires a few supporting hooks to be made use of. This is modeled off of the `combat_component` Component.

In short, this component will be put on the skill **to be cancelled by Nihil**. The player will put this component on cancellable skills, and create a custom `Nihil` that serves as a placeholder for this component to react to.

```python
class NihiledBy(SkillComponent):
    nid = 'nihiled_by'
    desc = "Takes a list of skills as its value. If a skill from this list is present on `target`, then *this* skill does not work."
    tag = SkillTags.CUSTOM

    expose = (ComponentType.List, ComponentType.Skill)
    value = []

    ignore_conditional = True
    _condition = True

    def pre_combat(self, playback, unit, item, target, item2, mode):
        all_target_nihils = set(self.value)
        for skill in target.skills:
            if skill.nid in all_target_nihils:
                self._condition = False
                return
        self._condition = True

    def post_combat_unconditional(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self._condition = True

    def condition(self, unit, item):
        return self._condition

    def test_on(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self.pre_combat(playback, unit, item, target, item2, mode)

    def test_off(self, playback, unit, item, target, item2, mode):
        game.on_alter_game_state()
        self._condition = True
```