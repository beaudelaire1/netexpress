from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devis', '0001_initial'),
        ('tasks', '0004_task_assigned_to_many_to_many'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='client',
            field=models.ForeignKey(
                blank=True,
                help_text='Client concerné par cette tâche pour le suivi portail',
                null=True,
                on_delete=models.SET_NULL,
                related_name='tasks',
                to='devis.client',
            ),
        ),
    ]