# Manual recruiter decisions on candidates + free-text candidate notes.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recruitment', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='is_manual_decision',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='candidate',
            name='decided_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidate_decisions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='candidate',
            name='decided_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='CandidateNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidate_notes', to=settings.AUTH_USER_MODEL)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='recruitment.candidate')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
