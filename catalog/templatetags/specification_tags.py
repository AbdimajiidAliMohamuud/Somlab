from django import template

from catalog.specifications import parse_specifications, render_specification_list


register = template.Library()


@register.filter
def render_specifications(value):
    return render_specification_list(parse_specifications(value))
