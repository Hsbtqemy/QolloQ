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
