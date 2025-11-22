from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split the value by the given argument."""
    return value.split(arg)

@register.filter
def split_once(value):
    """Split the value by the first space."""
    return value.split(' ', 1)
