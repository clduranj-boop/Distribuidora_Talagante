from django import template

register = template.Library()

@register.filter
def clp_format(value):
    try:
        # Formatea el valor como CLP (ejemplo: $1.234.567)
        return f"${int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return value  # Devuelve el valor original si falla