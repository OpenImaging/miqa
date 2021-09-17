from typing import List
from uri import URI
from abc import ABC, abstractclassmethod
from miqa.core.models import Image


class EvaluationModel(ABC):
    def __init__(self, uri: URI):
        self.uri = URI(uri)
        super().__init__()

    @abstractclassmethod
    def load(self):
        pass

    @abstractclassmethod
    def evaluate_images(self, image_set: List[Image]):
        pass


class NNModel(EvaluationModel):
    def load(self):
        return 'LOADED ' + str(self.uri)

    def evaluate_images(self, image_set: List[Image]):
        print('EVALUATION TIME!')


available_evaluation_models = {'MIQAT1-0': NNModel('uri'), 'MIQAT2-0': NNModel('fake_uri')}
