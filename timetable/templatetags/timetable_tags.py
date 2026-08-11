from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access dict by variable key in templates. Usage: {{ mydict|get_item:key }}"""
    return dictionary.get(key, [])
