from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        total = float(value) * float(arg)
        return "{:.2f}".format(total)  # format with 2 decimal places
    except (ValueError, TypeError):
        return ''
