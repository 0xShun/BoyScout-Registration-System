from django import template

register = template.Library()

@register.filter
def percent(value, arg):
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return None
        return (value / arg) * 100
    except (ValueError, TypeError):
        return None 