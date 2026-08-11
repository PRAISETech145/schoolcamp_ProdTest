from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access dict by variable key in templates."""
    return dictionary.get(key, [])
