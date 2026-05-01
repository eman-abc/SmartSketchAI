# Generated for SmartSketch forensic critic persistence.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_agentstatewrite'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedimage',
            name='generation_id',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='ForensicCritique',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_name', models.CharField(blank=True, max_length=255)),
                ('decision', models.CharField(default='accept', max_length=20)),
                ('score', models.FloatField(blank=True, null=True)),
                ('issues', models.JSONField(blank=True, default=list)),
                ('matched_features', models.JSONField(blank=True, default=list)),
                ('missing_features', models.JSONField(blank=True, default=list)),
                ('prompt_adjustment', models.TextField(blank=True)),
                ('safety_flags', models.JSONField(blank=True, default=list)),
                ('reasoning_summary', models.TextField(blank=True)),
                ('raw_report', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='critiques', to='api.editedimage')),
                ('image', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='critiques', to='api.generatedimage')),
            ],
        ),
    ]
