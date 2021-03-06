from collections import namedtuple
import numpy as np
import pytest

from vowpalwabbit.sklearn_vw import VW, VWClassifier, VWRegressor, tovw
from sklearn import datasets
from sklearn.exceptions import NotFittedError
from scipy.sparse import csr_matrix


"""
Test utilities to support integration of Vowpal Wabbit and scikit-learn
"""

Dataset = namedtuple('Dataset', 'x, y')


@pytest.fixture(scope='module')
def data():
    x, y = datasets.make_hastie_10_2(n_samples=100, random_state=1)
    x = x.astype(np.float32)
    return Dataset(x=x, y=y)


class TestVW:

    def test_validate_vw_estimator(self):
        """
        Run VW and VWClassifier through the sklearn estimator validation check

        Note: the VW estimators fail sklearn's estimator validation check. The validator creates a new
        instance of the estimator with the estimator's default args, '--quiet' in VW's case. At some point
        in the validation sequence it calls fit() with some fake data.  The data gets formatted  via tovw() to:

        2 1 | 0:0.5488135039273248 1:0.7151893663724195 2:0.6027633760716439 3:0.5448831829968969 4:0.4236547993389047 5:0.6458941130666561 6:0.4375872112626925 7:0.8917730007820798 8:0.9636627605010293 9:0.3834415188257777

        This gets passed into vw.learn and the python process dies with the error, "Process finished with exit code 139"

        At some point it would probably be worth while figuring out the problem  this and getting the two estimators to
        pass sklearn's validation check
        """

        # check_estimator(VW)
        # check_estimator(VWClassifier)

    def test_init(self):
        assert isinstance(VW(), VW)

    def test_fit(self, data):
        model = VW(loss_function='logistic')
        assert not hasattr(model, 'fit_')

        model.fit(data.x, data.y)
        assert model.fit_

    def test_passes(self, data):
        n_passes = 2
        model = VW(loss_function='logistic', passes=n_passes)
        assert model.passes_ == n_passes

        model.fit(data.x, data.y)
        weights = model.get_coefs()

        model = VW(loss_function='logistic')
        # first pass weights should not be the same
        model.fit(data.x, data.y)
        assert not np.allclose(weights.data, model.get_coefs().data)

    def test_predict_not_fit(self, data):
        model = VW(loss_function='logistic')
        with pytest.raises(NotFittedError):
            model.predict(data.x[0])

    def test_predict(self, data):
        model = VW(loss_function='logistic')
        model.fit(data.x, data.y)
        assert np.isclose(model.predict(data.x[:1][:1])[0], 0.406929)

    def test_predict_no_convert(self):
        model = VW(loss_function='logistic', convert_to_vw=False)
        model.fit(['-1 | bad', '1 | good'])
        assert np.isclose(model.predict(['| good'])[0], 0.245515)

    def test_set_params(self):
        model = VW()
        assert 'l' not in model.params

        model.set_params(l=0.1)
        assert model.params['l'] == 0.1

        # confirm model params reset with new construction
        model = VW()
        assert 'l' not in model.params

    def test_get_coefs(self, data):
        model = VW()
        model.fit(data.x, data.y)
        weights = model.get_coefs()
        assert np.allclose(weights.indices, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 116060])

    def test_get_intercept(self, data):
        model = VW()
        model.fit(data.x, data.y)
        intercept = model.get_intercept()
        assert isinstance(intercept, float)

    def test_oaa(self):
        X = ['1 | feature1:2.5',
             '2 | feature1:0.11 feature2:-0.0741',
             '3 | feature3:2.33 feature4:0.8 feature5:-3.1',
             '1 | feature2:-0.028 feature1:4.43',
             '2 | feature5:1.532 feature6:-3.2']
        model = VW(convert_to_vw=False, oaa=3)
        model.fit(X)
        assert np.allclose(model.predict(X), [ 1.,  2.,  3.,  1.,  2.])


class TestVWClassifier:

    def test_init(self):
        assert isinstance(VWClassifier(), VWClassifier)

    def test_decision_function(self, data):
        classes = np.array([-1., 1.])
        raw_model = VW(loss_function='logistic')
        raw_model.fit(data.x, data.y)
        predictions = raw_model.predict(data.x)
        class_indices = (predictions > 0).astype(np.int)
        expected = classes[class_indices]

        model = VWClassifier()
        model.fit(data.x, data.y)
        actual = model.predict(data.x)

        assert np.allclose(expected, actual)


class TestVWRegressor:

    def test_init(self):
        assert isinstance(VWRegressor(), VWRegressor)

    def test_predict(self, data):
        raw_model = VW()
        raw_model.fit(data.x, data.y)

        model = VWRegressor()
        model.fit(data.x, data.y)

        assert np.allclose(raw_model.predict(data.x), model.predict(data.x))
        # ensure model can make multiple calls to predict
        assert np.allclose(raw_model.predict(data.x), model.predict(data.x))

    def test_delete(self):
        raw_model = VW()
        del raw_model


def test_tovw():
    x = np.array([[1.2, 3.4, 5.6, 1.0, 10], [7.8, 9.10, 11, 0, 20]])
    y = np.array([1, -1])
    w = [1, 2]

    expected = ['1 1 | 0:1.2 1:3.4 2:5.6 3:1 4:10',
                '-1 2 | 0:7.8 1:9.1 2:11 4:20']

    assert tovw(x=x, y=y, sample_weight=w) == expected

    assert tovw(x=csr_matrix(x), y=y, sample_weight=w) == expected
