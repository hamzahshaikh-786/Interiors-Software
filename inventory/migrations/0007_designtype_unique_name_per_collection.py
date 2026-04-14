from django.db import migrations, models
 
 
class Migration(migrations.Migration):
 
    dependencies = [
        ('inventory', '0006_purchaseitem_status_and_more'),
    ]
 
    operations = [
        migrations.AddConstraint(
            model_name='designtype',
            constraint=models.UniqueConstraint(fields=('collection', 'name'), name='uniq_design_name_per_collection'),
        ),
    ]
