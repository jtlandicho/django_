from django import template

register = template.Library()

@register.filter
def get_dict_value(dictionary, key):
    """Get a value from a dictionary using a key."""
    return dictionary.get(key, 0)
