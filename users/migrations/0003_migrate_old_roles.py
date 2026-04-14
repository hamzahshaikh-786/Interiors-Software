from django.db import migrations

def migrate_roles(apps, schema_editor):
    User = apps.get_model('users', 'User')
    role_mapping = {
        'cutter': 'warehouse_manager',
        'dispatcher': 'warehouse_manager',
        'delivery_partner': 'delivery_person',
    }
    for old_role, new_role in role_mapping.items():
        User.objects.filter(role=old_role).update(role=new_role)

def reverse_migrate_roles(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(migrate_roles, reverse_migrate_roles),
    ]
