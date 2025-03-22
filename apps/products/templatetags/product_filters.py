from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    Returns the last part of a string split by the given argument
    Usage: {{ value|split:"/" }}
    """
    return value.split(arg)[-1] if value else ''