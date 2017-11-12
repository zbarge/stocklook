from stocklook.patterns.pattern import Pattern


class InsideBars(Pattern):

    @property
    def mother_candle(self):
        return self.data[-1]

    @property
    def high(self):
        return self.mother_candle[1]

    @property
    def low(self):
        return self.mother_candle[2]

    def __repr__(self):
        return "InsideBars(high={}, low={}, " \
               "length={}, number={})".format(
            self.high, self.low, self.time_elapsed,
            len(self.data))

