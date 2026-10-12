"""Política de correos para las cuentas de esta instalación local."""
import re


def validar_correo_gmail(valor):
    """Valida formato y dominio; no verifica la existencia de una cuenta de Gmail."""
    if not isinstance(valor, str):
        raise ValueError('El correo debe ser una dirección válida de @gmail.com')
    correo = valor.strip()
    if len(correo) > 100 or not re.fullmatch(
            r'[A-Za-z0-9](?:[A-Za-z0-9._+\-]*[A-Za-z0-9])?@gmail\.com',
            correo, flags=re.IGNORECASE):
        raise ValueError('El correo debe ser una dirección válida de @gmail.com')
    local, dominio = correo.rsplit('@', 1)
    if '..' in local:
        raise ValueError('El correo debe ser una dirección válida de @gmail.com')
    return local + '@' + dominio.lower()
