from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    root_dir = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class DatasetItem(models.Model):
    dataset = models.ForeignKey(Dataset, related_name="items", on_delete=models.CASCADE)
    image_path = models.CharField(max_length=1024)
    caption_path = models.CharField(max_length=1024, blank=True)
    mask_path = models.CharField(max_length=1024, blank=True)
    width = models.IntegerField(null=True)
    height = models.IntegerField(null=True)
    sha256 = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.dataset_id}:{self.image_path}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("dataset", "image_path"), name="dataset_item_unique"
            )
        ]
        indexes = [
            models.Index(fields=("dataset",)),
            models.Index(fields=("image_path",)),
        ]
