from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import models

from miqa.learning.evaluation_models import available_evaluation_models


class Evaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    image = models.ForeignKey('Image', null=False, on_delete=models.CASCADE)
    evaluation_model = models.CharField(max_length=50)
    results = models.JSONField()

    def __str__(self):
        return f'Evaluation for {str(self.image.raw_path)}'

    def save(self, *args, **kwargs):
        evaluation_model = available_evaluation_models[self.evaluation_model]
        if any([key not in evaluation_model.expected_outputs for key in self.results.keys()]):
            raise ValidationError(
                'Result keys must match expected outputs of associated evaluation model.'
            )

        super(Evaluation, self).save(*args, **kwargs)
