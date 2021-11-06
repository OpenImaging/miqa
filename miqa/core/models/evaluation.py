from uuid import uuid4

from django.db import models


class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    frame = models.OneToOneField(
        'Frame',
        null=False,
        on_delete=models.CASCADE,
        related_name='frame_evaluation',
    )
    evaluation_model = models.CharField(max_length=50)
    results = models.JSONField()

    def __str__(self):
        return f'Evaluation for {str(self.frame.raw_path)}'
