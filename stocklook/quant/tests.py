import numpy as np
import stocklook.quant.analysis as analysis

""" tests.py
Unit tests for quant module
"""

# arrays for testing
zeros_array = np.zeros(10).astype(float)
ones_array = np.ones(10).astype(float)
lin_ramp = np.arange(10).astype(float)
exp_ramp = np.array([x**2 for x in lin_ramp]).astype(float)
sin_signal = 10 * np.sin(lin_ramp) + 20
nan_array = np.array([np.nan, np.nan, np.nan, np.nan, np.nan,
                      np.nan, np.nan, np.nan, np.nan, np.nan]).astype(float)

# ------------------------------------------------
# Moving Averages
# ------------------------------------------------


def test_zero_length_moving_average():
    """ [quant.analysis] Test zero-length moving average
    """
    result = analysis.moving_average(0, lin_ramp)
    np.testing.assert_array_equal(result, nan_array)

def test_unit_length_moving_average():
    """ [quant.analysis] Test unit-length moving average
    """
    result = analysis.moving_average(1, lin_ramp)
    np.testing.assert_array_equal(result, lin_ramp)

def test_moving_average_with_zeros():
    """ [quant.analysis] Test moving average with zeros
    """
    result = analysis.moving_average(3, zeros_array)
    np.testing.assert_array_equal(result, [np.nan, np.nan, 0, 0, 0, 0, 0, 0, 0, 0])

def test_moving_average_with_ones():
    """ [quant.analysis] Test moving average with ones
    """
    result = analysis.moving_average(3, ones_array)
    np.testing.assert_array_equal(result, [np.nan, np.nan, 1, 1, 1, 1, 1, 1, 1, 1])

def test_moving_average_with_ramp():
    """ [quant.analysis] Test moving average with ramp
    """
    result = analysis.moving_average(3, lin_ramp)
    np.testing.assert_array_equal(result, [np.nan, np.nan, 1, 2, 3, 4, 5, 6, 7, 8])


def test_unit_length_exp_weighted_moving_average():
    """ [quant.analysis] Test unit-length EWMA
    """
    result = analysis.exp_weighted_moving_average(1, lin_ramp)
    np.testing.assert_array_equal(result, lin_ramp)

def test_exp_weighted_moving_average_with_zeros():
    """ [quant.analysis] Test EWMA with zeros
    """
    result = analysis.exp_weighted_moving_average(3, zeros_array)
    np.testing.assert_array_equal(result, zeros_array)

def test_exp_weighted_moving_average_with_ones():
    """ [quant.analysis] Test EWMA with ones
    """
    result = analysis.exp_weighted_moving_average(3, ones_array)
    np.testing.assert_array_equal(result, ones_array)

def test_exp_weighted_moving_average_with_ramp():
    """ [quant.analysis] Test EWMA with ramp
    """
    result = analysis.exp_weighted_moving_average(3, lin_ramp)
    matlab_result = [0, 0.66666667, 1.42857143, 2.26666667, 3.16129032,
                     4.0952381, 5.05511811, 6.03137255, 7.01761252, 8.00977517]

    np.testing.assert_array_almost_equal(result, matlab_result)

def test_mag_diff():
    """ [quant.analysis] Test Magnitude Difference with ramp
    """
    result = analysis.mag_diff(lin_ramp, zeros_array)
    np.testing.assert_array_almost_equal(result,lin_ramp)

def test_percent_diff():
   """ [quant.analysis] Test Percent Difference with ramp
   """
   result = analysis.percent_diff(lin_ramp,ones_array)
   np.testing.assert_array_almost_equal(result,lin_ramp-1.0)


# ------------------------------------------------
# Moving Statistics
# ------------------------------------------------

def test_percent_change():
    """ [quant.analysis] Test percent change calculation against Matlab
    """
    result = analysis.percent_change(lin_ramp)
    matlab_result = [np.nan, np.inf, 1, 0.5, 0.333333333333333, 0.25, 0.2,
                     0.166666666666667, 0.142857142857143, 0.125]
    np.testing.assert_array_almost_equal(np.nan_to_num(result),
                                         np.nan_to_num(matlab_result))

def test_moving_stdev():
    """ [quant.analysis] Test moving standard deviation calculation against Matlab
    """
    result = analysis.moving_stdev(4, exp_ramp)
    matlab_result = [np.nan, np.nan, np.nan, 4.041451884327381,
                     6.557438524302000, 9.110433579144299, 11.676186592091330,
                     14.247806848775006, 16.822603841260722, 19.399312702601950]

    np.testing.assert_array_almost_equal(result, matlab_result)


def test_moving_variance():
    """ [quant.analysis] Test moving variance calculation against Matlab
    """
    result = analysis.moving_var(4, exp_ramp)
    matlab_result = [np.nan, np.nan, np.nan,  16.333333333333332, 43, 83,
                     136.3333333333333, 203, 283,  376.3333333333333]

    np.testing.assert_array_almost_equal(result, matlab_result)


# ------------------------------------------------
# Momentum Indicators
# ------------------------------------------------

def test_momentum():
    """ [quant.analysis] Test momentum calculation against Matlab
    """
    result = analysis.momentum(4, exp_ramp)
    matlab_result = np.array([np.nan, np.nan, np.nan, np.inf, 1600., 625., 400., 306.25, 256., 225.])
    np.testing.assert_array_almost_equal(result, matlab_result)

def test_rate_of_change():
    """ [quant.analysis] Test rate of change calculation against Matlab
    """
    result = analysis.rate_of_change(4, exp_ramp)
    matlab_result = [np.nan, np.nan, np.nan, np.inf, 15, 5.25, 3, 2.0625, 1.56, 1.25 ]
    np.testing.assert_array_almost_equal(result, matlab_result)


def test_velocity():
    """ [quant.analysis] Test velocity calculation against Matlab
    """
    result = analysis.velocity(4, exp_ramp)
    matlab_result = [np.nan, np.nan, np.nan, 3, 5, 7, 9, 11, 13, 15]
    np.testing.assert_array_almost_equal(result, matlab_result)


def test_acceleration():
    """ [quant.analysis] Test acceleration calculation against Matlab
    """
    result = analysis.acceleration(4, exp_ramp)
    matlab_result = [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 2, 2, 2, 2]
    np.testing.assert_array_almost_equal(result, matlab_result)



def test_trix():
    """ [quant.analysis] Test TRIX calculation against Matlab
    """
    result = analysis.trix(4, exp_ramp)


def test_relative_strength_index():
    """ [quant.analysis] Test RSI calculation against Matlab
    """
    result = analysis.relative_strength_index(4, sin_signal)

def test_relative_momentum_index():
    """ [quant.analysis] Test RMI calculation against Matlab
    """
    result = analysis.relative_momentum_index(4,2, sin_signal)


if  __name__ == '__main__':
    test_zero_length_moving_average()
    test_unit_length_exp_weighted_moving_average()
    test_moving_average_with_zeros()
    test_moving_average_with_ones()
    test_moving_average_with_ramp()

    test_unit_length_exp_weighted_moving_average()
    test_exp_weighted_moving_average_with_zeros()
    test_exp_weighted_moving_average_with_ones()
    test_exp_weighted_moving_average_with_ramp()
    test_mag_diff()
    test_percent_diff()
    test_percent_change()
    test_moving_stdev()
    test_moving_variance()

    test_momentum()
    test_rate_of_change()
    test_velocity()
    test_acceleration()
    test_trix()
    test_relative_strength_index()
    test_relative_momentum_index()
