from abc import ABC, abstractclassmethod

from uri import URI

from miqa.learning.nn_classifier import get_model


class EvaluationModel(ABC):
    def __init__(self, uri: URI):
        self.uri = URI(uri)
        super().__init__()

    @abstractclassmethod
    def load(self):
        pass


class NNModel(EvaluationModel):
    def load(self):
        return get_model('miqa/learning/models/' + str(self.uri))


available_evaluation_models = {
    'MIQAT1-0': NNModel('miqaT1-val0.pth'),
    'MIQAT2-0': NNModel('fake_uri'),
}
