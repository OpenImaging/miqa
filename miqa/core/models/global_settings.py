from django.db import models


class GlobalSettings(models.Model):
    """Singleton table that holds global settings that need to be editable at runtime."""

    id = models.PositiveSmallIntegerField(primary_key=True)

    import_path = models.CharField(max_length=1000, default='', blank=True)
    export_path = models.CharField(max_length=1000, default='', blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]
