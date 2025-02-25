from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def timeformat(value):
    """Convert a timedelta object to a human-readable string"""
    if not isinstance(value, timedelta):
        return value
    
    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
