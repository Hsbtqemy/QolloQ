import markdown as md_lib
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def md(value):
    """Render Markdown text, with footnote and nl2br extensions."""
    if not value:
        return ""
    return mark_safe(md_lib.markdown(
        value,
        extensions=["footnotes", "nl2br"],
    ))


@register.filter
def dict_get(d, key):
    """Lookup a dict by key in a template: {{ mydict|dict_get:key }}."""
    return d.get(key) if d is not None else None


@register.simple_tag
def localized(obj, field, lang='fr'):
    """Retourne la valeur du champ EN si lang='en' et champ_en non vide, sinon FR."""
    if lang == 'en':
        val_en = getattr(obj, f"{field}_en", None)
        if val_en:
            return val_en
    return getattr(obj, field, '')
