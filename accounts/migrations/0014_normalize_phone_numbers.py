from django.db import migrations


def normalize_numbers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    try:
        from phonenumber_field.phonenumber import PhoneNumber
        from phonenumber_field.validators import validate_international_phonenumber
    except Exception:
        PhoneNumber = None
        validate_international_phonenumber = None

    for user in User.objects.all():
        changed = False
        for field in ['phone_number', 'emergency_phone']:
            val = getattr(user, field, None)
            if not val:
                continue
            try:
                if PhoneNumber and hasattr(val, 'as_e164'):
                    # Already a PhoneNumber instance
                    normalized = val.as_e164
                else:
                    s = str(val)
                    digits = ''.join(filter(str.isdigit, s))
                    if s.startswith('+'):
                        normalized = s
                    elif len(digits) == 11 and digits.startswith('09'):
                        normalized = f'+63{digits[1:]}'
                    elif len(digits) == 10 and digits.startswith('9'):
                        normalized = f'+63{digits}'
                    else:
                        normalized = s
                setattr(user, field, normalized)
                changed = True
            except Exception:
                # Leave as-is on failure
                pass
        if changed:
            try:
                user.save(update_fields=['phone_number', 'emergency_phone'])
            except Exception:
                # Skip invalid rows
                pass


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0013_alter_user_phone_fields'),
    ]

    operations = [
        migrations.RunPython(normalize_numbers, migrations.RunPython.noop),
    ]
