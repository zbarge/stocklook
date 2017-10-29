import pandas
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt


def rsi_test():
    # Window length for moving average
    window_length = 14

    # Dates
    start = datetime.datetime(2010, 1, 1)
    end = datetime.datetime(2013, 1, 27)

    # Get data
    data = pandas.io.data.DataReader('FB', 'yahoo', start, end)
    # Get just the close
    close = data['Adj Close']
    # Get the difference in price from previous step
    delta = close.diff()
    # Get rid of the first row, which is NaN since it did not have a previous
    # row to calculate the differences
    delta = delta[1:]

    # Make the positive gains (up) and negative gains (down) Series
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0

    # Calculate the EWMA
    roll_up1 = pandas.stats.moments.ewma(up, window_length)
    roll_down1 = pandas.stats.moments.ewma(down.abs(), window_length)

    # Calculate the RSI based on EWMA
    RS1 = roll_up1 / roll_down1
    RSI1 = 100.0 - (100.0 / (1.0 + RS1))

    # Calculate the SMA
    roll_up2 = pandas.rolling_mean(up, window_length)
    roll_down2 = pandas.rolling_mean(down.abs(), window_length)

    # Calculate the RSI based on SMA
    RS2 = roll_up2 / roll_down2
    RSI2 = 100.0 - (100.0 / (1.0 + RS2))

    # Compare graphically
    plt.figure()
    RSI1.plot()
    RSI2.plot()
    plt.legend(['RSI via EWMA', 'RSI via SMA'])
    plt.show()


def RSI(prices, n=14):
    # RSI = 100 - (100 / (1 + RS))
    # where RS = (Wilder-smoothed n-period average of gains / Wilder-smoothed n-period average of -losses)
    # Note that losses above should be positive values
    # Wilder-smoothing = ((previous smoothed avg * (n-1)) + current value to average) / n
    # For the very first "previous smoothed avg" (aka the seed value), we start with a straight average.
    # Therefore, our first RSI value will be for the n+2nd period:
    #     0: first delta is nan
    #     1:
    #     ...
    #     n: lookback period for first Wilder smoothing seed value
    #     n+1: first RSI

    # First, calculate the gain or loss from one price to the next. The first value is nan so replace with 0.
    deltas = (prices - prices.shift(1)).fillna(0)

    # Calculate the straight average seed values.
    # The first delta is always zero, so we will use a slice of the first n deltas starting at 1,
    # and filter only deltas > 0 to get gains and deltas < 0 to get losses
    avg_of_gains = deltas[1:n + 1][deltas > 0].sum() / n
    avg_of_losses = -deltas[1:n + 1][deltas < 0].sum() / n

    # Set up pd.Series container for RSI values
    rsi_series = pd.Series(0.0, deltas.index)

    # Now calculate RSI using the Wilder smoothing method, starting with n+1 delta.
    up = lambda x: x if x > 0 else 0
    down = lambda x: -x if x < 0 else 0
    i = n + 1
    for d in deltas[n + 1:]:
        avg_of_gains = ((avg_of_gains * (n - 1)) + up(d)) / n
        avg_of_losses = ((avg_of_losses * (n - 1)) + down(d)) / n
        if avg_of_losses != 0:
            rs = avg_of_gains / avg_of_losses
            rsi_series[i] = 100 - (100 / (1 + rs))
        else:
            rsi_series[i] = 100
        i += 1

    return rsi_series