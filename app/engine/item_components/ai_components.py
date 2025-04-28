from app.data.database.item_components import ItemComponent, ItemTags

class NoAI(ItemComponent):
    nid = 'no_ai'
    desc = "Adding this component prevents the AI from trying to use the item. This is important for sequence items, which the AI is unable to handle."
    tag = ItemTags.BASE

    def ai_priority(self, unit, item, target, move):
        return -1

class TargetAI(ItemComponent):
    nid = 'targetai'
    desc = "Gives a condition under which the AI will target units with this item.  Higher priority makes the AI more likely to use the item."
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
                if evaluate.evaluate(self.value['condition'], unit, target, local_args={'item': item}):
                    priority_term = evaluate.evaluate(self.value['priority'], unit, target, local_args={'item': item})
                    return priority_term
            except:
                print("Could not evaluate condition or priority.")
        return 0
    