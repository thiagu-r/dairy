from django import template

register = template.Library()

@register.filter
def get_or_none(queryset, product):
    try:
        return queryset.get(product=product)
    except:
        return None