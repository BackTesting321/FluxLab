from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('allow_nsfw', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='DatasetItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rel_path', models.CharField(max_length=1024)),
                ('size', models.IntegerField()),
                ('width', models.IntegerField()),
                ('height', models.IntegerField()),
                ('status', models.CharField(choices=[('ok', 'OK'), ('needs_fix', 'Needs fix'), ('rejected', 'Rejected')], default='ok', max_length=10)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='dataset_viewer.dataset')),
            ],
        ),
    ]
