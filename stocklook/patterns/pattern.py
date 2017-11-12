from pandas import DataFrame


class Pattern:
    def __init__(self, data, time_frame=None, **kwargs):
        assert data and len(data) > 1
        self.data = data
        self.time_frame = time_frame
        self.kwargs = kwargs

    @property
    def time_elapsed(self):
        return self.data[0][-1] - self.data[-1][-1]

    @property
    def df(self):
        cols = ['open', 'high', 'low', 'close', 'time']
        return DataFrame(data=self.data,
                         columns=cols,
                         index=range(len(self.data)))

