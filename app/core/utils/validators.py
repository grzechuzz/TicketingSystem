import re
from phonenumbers import parse, is_valid_number, NumberParseException, format_number, PhoneNumberFormat
from pydantic import SecretStr

def check_password_strength(password: SecretStr) -> None:
    password = password.get_secret_value()
    errors = []
    if not re.search(r'[a-z]', password):
        errors.append('a lowercase letter')
    if not re.search(r'[A-Z]', password):
        errors.append('an uppercase letter')
    if not re.search(r'\d', password):
        errors.append('a digit')
    if not re.search(r'[^\w\s]', password):
        errors.append('a special character')
    if errors:
        needed = ', '.join(errors)
        raise ValueError(f'Password must contain: {needed}')


def normalize_phone_or_none(v: str | None, default_region: str | None = None) -> str | None:
    if v is None or not v.strip():
        return None
    try:
        num = parse(v, default_region)
    except NumberParseException:
        raise ValueError("Invalid phone number")
    if not is_valid_number(num):
        raise ValueError("Invalid phone number")
    return format_number(num, PhoneNumberFormat.E164)


def ensure_passwords_match(model, password: SecretStr, password_confirm: SecretStr):
    if password.get_secret_value() != password_confirm.get_secret_value():
        raise ValueError("Passwords do not match")
    return model
