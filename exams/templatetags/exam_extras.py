from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dict lookup by variable key: {{ line.scores|get_item:subject.id }}"""
    return mapping.get(key)
