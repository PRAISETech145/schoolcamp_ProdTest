from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Timetable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='My Timetable', max_length=100)),
                ('semester', models.CharField(choices=[('1', 'Semester 1'), ('2', 'Semester 2'), ('annual', 'Annual')], default='1', max_length=10)),
                ('academic_year', models.CharField(default='2024/2025', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('is_shared', models.BooleanField(default=False)),
                ('share_token', models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timetables', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('code', models.CharField(blank=True, max_length=20)),
                ('lecturer', models.CharField(blank=True, max_length=100)),
                ('room', models.CharField(blank=True, max_length=50)),
                ('day_of_week', models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('color', models.CharField(choices=[('#4CAF50', 'Green'), ('#2196F3', 'Blue'), ('#F44336', 'Red'), ('#FF9800', 'Orange'), ('#9C27B0', 'Purple'), ('#00BCD4', 'Cyan'), ('#E91E63', 'Pink'), ('#795548', 'Brown'), ('#607D8B', 'Blue Grey'), ('#FFEB3B', 'Yellow')], default='#4CAF50', max_length=7)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('timetable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='timetable.timetable')),
            ],
            options={
                'ordering': ['day_of_week', 'start_time'],
            },
        ),
        migrations.CreateModel(
            name='TimetableShareRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('seen', models.BooleanField(default=False)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_share_requests', to=settings.AUTH_USER_MODEL)),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_share_requests', to=settings.AUTH_USER_MODEL)),
                ('timetable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='timetable.timetable')),
            ],
        ),
    ]
