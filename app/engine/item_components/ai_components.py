import logging
from app.data.database.components import ComponentType
from app.data.database.item_components import ItemComponent, ItemTags

class NoAI(ItemComponent):
    nid = 'no_ai'
    desc = "Adding this component prevents the AI from trying to use the item. This is important for sequence items, which the AI is unable to handle."
    tag = ItemTags.BASE

    def ai_priority(self, unit, item, target, move):
        return -1

class EvalAIPriority(ItemComponent):
    nid = 'eval_ai_priority'
    desc = """Gives a condition under which the AI will target units with this item.  Higher priority makes the AI more likely to use this item.
    Priority values should typically be between 0 and 1, but values above 1 can be used to more strongly encourage an action."""
    tag = ItemTags.UTILITY
    expose = ComponentType.NewMultipleOptions
    options = {
        'condition': ComponentType.String,
        'priority': ComponentType.String
    }

    def __init__(self, value=None):
        self.value = {
            'condition': 'True',
            'priority': '0'
        }
        if value:
            self.value.update(value)

    def ai_priority(self, unit, item, target, move):
        if target:
            from app.engine import evaluate
            try:
                condition: bool = bool(evaluate.evaluate(self.value['condition'], unit, target, local_args={'item': item, 'move': move}))
            except Exception as e:
                logging.error("eval_ai_priority failed to evaluate condition %s with error %s", self.value['condition'], e)
                return 0
            if condition:
                    try:
                        priority_term: float = float(evaluate.evaluate(self.value['priority'], unit, target, local_args={'item': item, 'move': move}))
                        return priority_term
                    except Exception as e:
                        logging.error("eval_ai_priority failed to evaluate priority %s with error %s", self.value['priority'], e)
        return 0
