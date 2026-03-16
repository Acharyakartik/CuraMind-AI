from django import template

register = template.Library()


@register.filter(name="length_is")
def length_is(value, arg) -> bool:
    """
    Compatibility filter for older templates (e.g., some AdminLTE admin themes).

    Django 5 removed the built-in `length_is` filter; keep legacy templates working.
    """
    try:
        expected = int(arg)
    except (TypeError, ValueError):
        return False

    try:
        return len(value) == expected
    except TypeError:
        return False

