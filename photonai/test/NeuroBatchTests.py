import unittest
import numpy as np
from ..neuro.NeuroBase import NeuroBatch


class DummyBatchTransformer:

    def __init__(self):
        self.needs_y = False
        self.needs_covariates = True
        self.predict_count = 0

    def fit(self, X, y, **kwargs):
        pass

    def transform(self, X, y, **kwargs):
        X_new = []
        for i, x in enumerate(X):
            X_new.append([str(sub_x) + str(y[i]) for sub_x in x])

        if not np.array_equal(y, kwargs["animals"]):
            raise Exception("Batching y and kwargs delivery is strange")

        kwargs["animals"] = [i[::-1] for i in kwargs["animals"]]

        return X_new, y, kwargs

    def predict(self, X, y=None, **kwargs):

        self.predict_count += 1
        predictions = np.ones(X.shape) * self.predict_count
        return predictions


class NeuroBatchTests(unittest.TestCase):

    def setUp(self):
        self.batch_size = 10
        nr_features = 3
        origin_list = ["affe", "tiger", "schwein", "giraffe", "löwe"]
        self.data = None
        self.targets = None

        self.neuro_batch = NeuroBatch(DummyBatchTransformer(), batch_size=self.batch_size)

        for element in origin_list:
            features = [element + str(i) for i in range(0, nr_features)]
            if self.data is None:
                self.data = np.array([features] * self.batch_size)
            else:
                self.data = np.vstack((self.data, [features] * self.batch_size))
            if self.targets is None:
                self.targets = np.array([element] * self.batch_size)
            else:
                self.targets = np.hstack((self.targets,  [element] * self.batch_size))

        self.data = np.array(self.data)
        self.targets = np.array(self.targets)
        self.kwargs = {"animals": self.targets}

    def test_transform(self):
        X_new, y_new, kwargs_new = self.neuro_batch.transform(self.data, self.targets, **self.kwargs)
        self.assertListEqual(X_new[0, :].tolist(), ["affe0affe", "affe1affe", "affe2affe"])
        self.assertListEqual(X_new[49, :].tolist(), ["löwe0löwe", "löwe1löwe", "löwe2löwe"])
        self.assertEqual(kwargs_new["animals"][0], "effa")
        self.assertEqual(kwargs_new["animals"][49], "ewöl")

    def test_predict(self):
        X_predicted, _, _ = self.neuro_batch.predict(self.data, **self.kwargs)
        # assure that predict is batch wisely called
        self.assertTrue(X_predicted[0][0] == 1)
        self.assertTrue(X_predicted[-1][0] == (self.data.shape[0]/self.batch_size))
