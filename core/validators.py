import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validar_contraseña_fuerte(password):
    if len(password) < 8:
        raise ValidationError("La contraseña debe tener al menos 8 caracteres.")

    if not re.search(r"[A-Z]", password):
        raise ValidationError("La contraseña debe contener al menos una mayúscula.")

    if not re.search(r"[0-9]", password):
        raise ValidationError("La contraseña debe contener al menos un número.")

    comunes = ["12345678", "password", "123456789", "qwerty123", "admin123"]
    if password.lower() in comunes or password.lower() in [c[::-1] for c in comunes]:
        raise ValidationError("Esa contraseña es muy común. Elige una más segura.")