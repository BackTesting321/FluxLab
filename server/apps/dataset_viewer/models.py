from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    allow_nsfw = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DatasetItem(models.Model):
    class Status(models.TextChoices):
        OK = 'ok', 'OK'
        NEEDS_FIX = 'needs_fix', 'Needs fix'
        REJECTED = 'rejected', 'Rejected'

    dataset = models.ForeignKey(Dataset, related_name='items', on_delete=models.CASCADE)
    rel_path = models.CharField(max_length=1024)
    size = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    tags = models.JSONField(default=list, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dataset_id}:{self.rel_path}"
