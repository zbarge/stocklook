#!/usr/bin/env python
import numpy as np
from numpy import array, zeros, append, sum, subtract, empty, nan
from pandas import Series, stats, concat


# ------------------------------------------------
# Moving Averages
# ------------------------------------------------

def moving_average(span, data):
    """ Calculate n-point moving average
    :param span: Length of moving average window.
    :param data: Data to average.
    :returns: Moving average as a numpy array.
    """
    return np.array(stats.moments.rolling_mean(data, span))


def exp_weighted_moving_average(span, data):
    """ Calculate n-point exponentially weighted moving average
    :param span: Length of moving average window.
    :param data: Data to average.
    :returns: Exponentially weighted moving average as a numpy array.
    """
    return np.array(stats.moments.ewma(data, span=span))

def mag_diff(data, average):
    return np.array([np.nan if (avg is None or cur is None) else (cur - avg) for cur, avg in zip(data, average)])

def percent_diff(data, average):
    return np.array([np.nan if (avg is None or avg == 0.0 or cur is None) else ((cur - avg) / (avg + 1e-1000)) for cur,avg in zip(data, average)])


# ------------------------------------------------
# Moving Statistics
# ------------------------------------------------


def percent_change(data):
    """ Calculate percent change in data
    :param data: Data to process
    :returns: Percent change in data as a numpy array.
    """
    return np.array(Series(data).pct_change().values)



def moving_stdev(span, data):
    """ Calculate n-point moving standard deviation.
    :param data: Data to analyze.
    :param span: Length of moving window.
    :returns: Moving standard deviation as a numpy array.
    """
    return np.array(stats.moments.rolling_std(data, span))


def moving_var(span, data):
    """ Calculate n-point moving variance.
    :param data: Data to analyze.
    :param span: Length of moving window.
    :returns: moving variance as a numpy array.
    """
    return np.array(stats.moments.rolling_var(data, span))


# ------------------------------------------------
# Momentum Indicators
# ------------------------------------------------


def momentum(span, data):
    """ Calculate Momentum
    Momentum is defined as 100 times the ratio of the current value to the
    value *span - 1* days ago
    :param span: number of days before to use in the momentum calculation
    :param data: Raw data to analyze.
    :returns: Momentum as a numpy array.
    """
    momentum = np.array([100 * (cur / prev) for cur, prev in zip(data[span-1:], data)])
    blank = np.zeros(span-1)
    blank[:] = np.nan
    return append(blank, momentum) #.astype(float)

def rate_of_change(span, data):
    """ Calculate rate of change
    """
    roc = np.array([((cur - prev) / prev) for cur, prev in zip(data[span-1:], data)])
    blank = np.zeros(span-1)
    blank[:] = np.nan
    return append(blank, roc).astype(float)


def velocity(span, data):
    """ Calculate velocity
    """
    velocity = np.array([((cur - prev) / (span - 1)) for cur, prev in zip(data[span-1:], data)])
    blank = np.zeros(span-1)
    blank[:] = np.nan
    return append(blank, velocity).astype(float)


def acceleration(span, data, vel=None):
    """ Calculate acceleration
    """
    if vel is None:
        vel = velocity(span, data)
    acceleration = np.array([((cur - prev) / (span - 1)) for cur, prev in zip(vel[span-1:], vel)])
    blank = zeros(span-1)
    blank[:] = nan
    return append(blank, acceleration).astype(float)


def macd(data=None, fast_ewma=None, slow_ewma=None):
    """ Calculate Moving Average Convergence Divergence
    Moving Average Convergence Divergence is defined as the difference between
    the 12-day EWMA and the 26-day EWMA.
    :param data: (optional) Data to analyze.
    :param fast_ewma: (optional) 12-day EWMA for use in MACD calculation.
    :param slow_ewma: (optional) 26-day EWMA for use in MACD calculation.
    :returns: MACD as a numpy array.
    .. note::
        Either raw data or the 12 and 26 day EWMAs must be provided, all three
        are not necessary.
    """
  #  return exp_weighted_value_oscillator(12, 26, data, fast_ewma, slow_ewma)
    if fast_ewma is None and slow_ewma is None:
        if data is not None:
            slow_ewma = exp_weighted_moving_average(26, data)
            fast_ewma = exp_weighted_moving_average(12, data)
        else:
            pass
    return subtract(fast_ewma, slow_ewma).astype(float)


def macd_signal(data=None, macd=None):
    """ Calculate MACD signal
    The MACD signal is defined as the 9-day EWMA of the MACD.
    :param data: (Optional) Raw data to analyze.
    :param macd: (Optional) MACD to use in MACD signal calculation.
    :returns: MACD signal as a numpy array.
    .. note::
        Either raw data or the MACD must be provided, both ar not necessary
    """
    if macd is None:
        if data is not None:
            macd = macd(data)
        else:
            pass
        pass
    return exp_weighted_moving_average(9, macd)


def macd_hist(data=None, macd=None, macd_signal=None):
    """ Calculate MACD histogram
    The MACD Histogram is defined as the difference between the MACD signal
    and the MACD.
    :param data: (optional) Raw data to analyze.
    :param macd: (optional) MACD to use in MACD histogram calculation.
    :param macd_signal: (optional) MACD signal to use in MACD histogram
    calculation.
    :returns: MACD histogram as a numpy array.
    .. note::
        Either raw data or the MACD and MACD signal must be provided, all three
        are not necessary.
    """
    if macd is None and macd_signal is None:
        if data is not None:
            macd = macd(data)
            macd_signal = macd_signal(macd=macd)
        else:
            pass
    return subtract(macd, macd_signal)


def value_oscillator(fast_ma_len=5,slow_ma_len=20, data=None, fast_ma=None, slow_ma=None):
    """ Calculate value oscillator
    """
    if fast_ma is None and slow_ma is None:
        if data is not None:
            slow_ma = moving_average(slow_ma_len, data)
            fast_ma = moving_average(fast_ma_len, data)
        else:
            pass
    return subtract(fast_ma, slow_ma).astype(float)


def exp_weighted_value_oscillator(fast_ma_len=5, slow_ma_len=20, data=None, fast_ma=None, slow_ma=None):
    """ Calculate exponentially weighted value oscillator
    """
    if fast_ma is None and slow_ma is None:
        if data is not None:
            slow_ma = exp_weighted_moving_average(slow_ma_len, data)
            fast_ma = exp_weighted_moving_average(fast_ma_len, data)
        else:
            # Error
            pass
        return subtract(fast_ma, slow_ma).astype(float)


def trix(span, data):
    """ Calculate TRIX
    TRIX is the percent change of the triple ewma'ed value
    """
    first = (exp_weighted_moving_average(span, data))
    second = (exp_weighted_moving_average(span, first))
    third = (exp_weighted_moving_average(span, second))
    trix = [((cur - prev) / prev) for cur, prev in zip(third[span-1:], third)]
    blank = np.zeros(span - 1)
    blank[:] = nan
    return append(blank, trix).astype(float)

def chandes_momentum_oscillator(span, data):
    blank = np.zeros(span)
    blank[:] = nan
    deltas = append(blank, [cur - prev for cur, prev in zip(data[span:], data)]).astype(float)


def relative_strength_index(span, data):
    """ Calculate RSI
    """
    return relative_momentum_index(span, 1, data)


def relative_momentum_index(span, deltaspan, data):
    """ Calculate RMI
    """
    blank = np.zeros(deltaspan)
    blank[:] = nan
    deltas = append(blank, [cur - prev for cur, prev in zip(data[deltaspan:], data)]).astype(float)
    gains = array([x if x > 0 else 0 for x in deltas]).astype(float)
    losses = array([-x if x < 0 else 0 for x in deltas]).astype(float)
    avg_gains = moving_average(span, gains)
    avg_losses = moving_average(span, losses)
    return array([100 - (100 / (1 + gain/loss))  for gain, loss in zip(avg_gains, avg_losses)]).astype(float)



# ------------------------------------------------
# Market Momentum Indicators
# ------------------------------------------------

def accumulation_distribution(high, low, close, volume, prev=0):
    """ Calculate Accumulation/Distribution
    """
    money_flow_volume = array([v *  (((c - l) - (h - c)) / (h - l)) for h, l, c, v in zip(high, low, close, volume)]).astype(float)
    adl = zeros(len(money_flow_volume))
    for i in range(len(money_flow_volume)):
        adl[i] = prev + money_flow_volume[i]
        prev = adl[i]
    return adl.astype(float)


def chaikin_oscillator(high=None, low=None, close=None, volume=None, prev=0,adl=None):
    if adl is None:
        if high is not None and low is not None and close is not None and volume is not None:
            adl = accumulation_distribution(high, low, close, volume, prev)
            fast_ma = exp_weighted_moving_average(3, adl)
            slow_ma = exp_weighted_moving_average(10, adl)
        else:
            # Error
            pass
        return subtract(fast_ma, slow_ma).astype(float)
