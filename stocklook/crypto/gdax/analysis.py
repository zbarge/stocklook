"""
MIT License

Copyright (c) 2017 Zeke Barge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
# Evaluate price action for past hour, day, week, and month
General Rules:
- Never buy the top of a range...unless extreme volume and a quick trade
- Never buy a falling knife that has no support
- Never buy a product that is more than 10% above 14 period SMA
- Sell top of range if price has been ranging for less than 4 hours or more than 1 day

Questions:
- Is price going up, down, or ranging?
    - up
        Consider selling open positions
    - down
        Consider adding new positions
    - ranging
        Consider a series of buy-low-sell-high trades until it doesnt work anymore.

- Is volume weak, medeocre, or strong?
    - weak
        - on ranging price take ranging strategy
    - medeocre
        - on up price consider taking profits, ranging/down price hold position
    - strong
        - on up price hold until there's a clear sign to sell or we have a very
          healthy profit.
        - on down price consider looking for past support and bottom-fishing
        - on ranging price heavily consider adding a long

- Is price a healthy level near 14 and 8 period SMA?
    - far above
        Probably a little to risky to buy, good idea to close open positions
        only exception is if price has CONSISTENTLY been above these SMAs
    - right around
        Probably a good idea to hold - not much you can get from this signal
    - far below
        Probably a good idea to bottom fish, especially on a volume spike and on past support.

- What is current price velocity?
    - Fast
        - Consider quicker trading timeframes too much in one direction cant be good.
    - Medeocre
        - Consider mid-longer term timeframes with tight stops
    - Low
        - Consider longer term timeframes, not much to do here.

- Is 14 period RSI Overbought, Oversold, or in the Middle zone?
    Overbought:
        Consider taking profit unless embedded overbought
    Oversold:
        Consider bottom-fishing play
    Middle Zone:
        Consider holding and maybe adjusting stop to right below latest support.


How to determine an entry, target, and exit price:
    1) Consider the above questions, do most of them say buy now?
        - If no wait until they do

    2) A healthy target is maybe 30% of the average range for the trading time period.

    3) A stop loss should be set just under the next buy wall near the support price
        - This may need to be monitored to follow the buy wall since those seem to move constantly.

    4) A trading strategy should try 10 times and lose 2% each time with fewer than 5 wins before
       requesting help and shutting down.

       Preferably should be back-tested against past data to determine
       profit/loss before being used in production.

"""
import os
from stockstats import StockDataFrame
import pandas as pd
from stocklook.crypto.gdax import GdaxChartData, Gdax
from stocklook.utils.timetools import now, now_minus, now_plus, timestamp_to_path
from stocklook.config import config


def get_velocity(df, price='price', date='date'):
    df.sort_values(date, ascending=True, inplace=True)

class TradeSet:
    BUY = 'buy'
    SELL = 'sell'
    TYPES = [BUY, SELL]

    def __init__(self, margin=False, funds=10000):
        self.data = list()
        self._df = None
        self._pos_size = 0
        self.margin = margin
        self.funds = funds
        self.start_funds = funds
        self._trades = 0

    @property
    def df(self):
        if self._df is None:
            self.to_frame()
        return self._df

    @property
    def trades(self):
        return self._trades

    @property
    def position_size(self):
        return self._pos_size

    def add_trade(self, time, size, price, type):
        assert type in self.TYPES
        if type == self.SELL:
            if size < 0:
                size = abs(size)

            if self._pos_size < size and not self.margin:
                if self._pos_size <= 0:
                    # Can't sell coin you dont
                    # have without margin.
                    return False
                size = self._pos_size

            self._pos_size -= abs(size)

        elif type == self.BUY:
            if size > 0:
                size = -size

            total = size * price
            if self.funds + total < 0:
                if self.funds <= 0:
                    # Can't buy coin without funds.
                    return False
                size = self.funds / price
                size = -size

            self._pos_size += abs(size)

        self.funds += size * price

        assert price > 0

        contents = [time, size, price, type]
        self.data.append(contents)
        #print("Trade: {} - position: {} - funds: {}".format(contents, self._pos_size, self.funds))
        self._trades += 1
        return True

    def buy(self, time, size, price):
        return self.add_trade(time, size, price, self.BUY)

    def sell(self, time, size, price):
        return self.add_trade(time, size, price, self.SELL)

    def clear(self):
        self.data.clear()

    def close_positions(self, time, price):
        df = self.to_frame()
        size_sum = df['size'].sum()
        if size_sum < 0:
            self.add_trade(time, size_sum, price, self.SELL)
        elif size_sum > 0:
            self.add_trade(time, size_sum, price, self.BUY)

    def get_profit(self):
        return self.funds - self.start_funds

    def get_pnl(self):
        return round(((self.funds / self.start_funds) * 100) - 100, 2)

    def get_total_bought(self):
        df = self.df
        msk = df['type'].isin([self.BUY])
        t = df.loc[msk, 'size'].sum()
        return abs(t)

    def get_total_sold(self):
        df = self.df
        msk = df['type'].isin([self.SELL])
        t = df.loc[msk, 'size'].sum()
        return abs(t)

    def to_frame(self):
        data = self.data
        columns = ['time', 'size', 'price', 'type']
        idx = range(len(data))
        df = pd.DataFrame(data=data, columns=columns, index=idx)
        df.loc[:, 'total'] = df['size'] * df['price']
        self._df = df
        return df


class DecisionMaker:
    """
    A decision maker analyzes a row of data
    and decides whether or not to buy or sell.
    """
    def __init__(self, stock_data_frame, trade_set, size, **kwargs):
        self.sdf = stock_data_frame
        self.tset = trade_set
        self.kwargs = kwargs
        self.size = size
        self.trades = list()

    def calculate(self):
        raise NotImplementedError("Child classes should update "
                                  "their sdf (StockDataFrame) here.")

    def execute(self, row):
        """
        Should buy or sell a position based on data found in the row.

        :param row:
        :return:
        """
        raise NotImplementedError("Child classes should buy or sell here.")

    def inputs(self):
        raise NotImplementedError("Child classes should return "
                                  "key class properties here.")

    def register_trade(self, row, type):
        row['type'] = type
        self.trades.append(row)

    def __repr__(self):
        return "DecisionMaker(size='{}', trades='{}')".format(self.size, len(self.trades))


class MACDRSIMaker(DecisionMaker):
    def __init__(self, *args, buy_ratio=1.7, sell_ratio=0.95):
        DecisionMaker.__init__(self, *args)
        self.buy_ratio = buy_ratio
        self.sell_ratio = sell_ratio
        self.macd_buy_point = None
        self.macd_sell_point = None
        self.rsi_buy_point = None
        self.rsi_sell_point = None
        if self.sdf is not None:
            self.calculate()

    def inputs(self):
        return dict(buy_ratio=self.buy_ratio,
                    sell_ratio=self.sell_ratio,
                    macd_buy_point=self.macd_buy_point,
                    macd_sell_point=self.macd_sell_point,
                    rsi_buy_point=self.rsi_buy_point,
                    rsi_sell_point=self.rsi_sell_point)

    def calculate(self):
        self.sdf.get('macd')
        self.sdf.get('rsi_6')
        df = self.sdf.dropna(subset=['rsi_6', 'macd'], how='any')
        df = df.loc[df['rsi_6'] > 0.1, :]
        df = df.loc[df['macd'] > 0.1, :]

        macd, rsi = df['macd'], df['rsi_6']
        min_macd, max_macd = macd.min(), macd.max()
        min_rsi, max_rsi = rsi.min(), rsi.max()
        self.macd_buy_point = min_macd * self.buy_ratio
        self.macd_sell_point = max_macd * self.sell_ratio
        self.rsi_buy_point = min_rsi * self.buy_ratio
        self.rsi_sell_point = max_rsi * self.sell_ratio

    def execute(self, row):
        tset, rec = self.tset, row
        macd_buy = rec['macd'] <= self.macd_buy_point
        rsi_buy = rec['rsi_6'] <= self.rsi_buy_point
        macd_sell = rec['macd'] >= self.macd_sell_point
        rsi_sell = rec['rsi_6'] >= self.rsi_sell_point
        time = rec['time']
        price = rec['close']
        size = self.size

        if macd_buy or rsi_buy:
            buyable = tset.funds / price
            if buyable > size * 3:
                s = buyable / 3
            else:
                s = size
            s = round(s, 0)
            t = tset.buy(time, s, price)
            if t:
                self.register_trade(row, tset.BUY)

        elif macd_sell or rsi_sell:
            if tset.position_size > size * 3:
                s = round(tset.position_size * .5, 0)
            else:
                s = size
            t = tset.sell(time, s, price)
            if t:
                self.register_trade(row, tset.SELL)

    def __repr__(self):
        return ','.join("{}='{}'".format(k, v) for k, v in self.inputs().items())



class Strategy:
    def __init__(self, stock_data_frame=None, margin=False, funds=1500, position_size=5):
        self.tset = TradeSet(margin=margin, funds=funds)
        self.stock_data_frame = stock_data_frame
        self.position_size = position_size
        self.makers = list()

    def add_decision_maker(self, cls, **kwargs):
        trade_set = TradeSet(margin=self.tset.margin,
                             funds=self.tset.funds)
        maker = cls(self.stock_data_frame,
                    trade_set,
                    self.position_size,
                    **kwargs)
        self.makers.append(maker)

    def execute(self):
        """
        You can override this however you want with subclassed

        :param stock_data_frame:
        :return:
        """
        sdf = self.stock_data_frame
        sdf.sort_values(['time'], ascending=[True], inplace=True)

        [[maker.execute(rec) for maker in self.makers]
         for _, rec in sdf.iterrows()]
        rec = sdf.iloc[-1]
        [maker.tset.close_positions(rec['time'], rec['close'])
         for maker in self.makers]

    def set_stock_df(self, df):
        self.stock_data_frame = df
        for maker in self.makers:
            maker.sdf = df
            try:
                maker.calculate()
            except:
                pass



def run_macd_rsi_decisions(data_dir, product, start, end, granularity, overwrite=True, strat=None):
    # File paths to be saved at the end.
    out_name = '{}-BTEST-{}-{}.csv'.format(product, granularity, timestamp_to_path(end))
    tout_name = out_name.split('.')[0] + '-TRADES.csv'
    pout_name = out_name.split('.')[0] + '-PNL.csv'
    out_path = os.path.join(data_dir, out_name)  # Chart Data
    tout_path = os.path.join(data_dir, tout_name)  # Trade Data
    pout_path = os.path.join(data_dir, pout_name)  # PNL Data

    if os.path.exists(tout_path) and not overwrite:
        tdf = pd.read_csv(tout_path, parse_dates=['time'])
        return tout_path, tdf

    if os.path.exists(out_path) and not overwrite:
        df = pd.read_csv(out_path, parse_dates=['time'])
    else:
        data = GdaxChartData(Gdax(), product, start, end, granularity=granularity)
        try:
            df = data.df
        except ValueError:
            return None, pd.DataFrame()

    if strat is None:
        sdf = StockDataFrame.retype(df)
        strat = Strategy(sdf, margin=False, funds=1500, position_size=5)
        print("Composing decision makers.")
        ratios = ((0.1, 0.1), (0.1, 0.5),
                  (0.5, 0.1), (0.2, 0.1),
                  (0.1, 0.2), (0.25, 0.35),
                  (0.01, 0.02), (0.09, 0.075),
                  (1, 2), (0.005, 0.003),
                  (0.003, 0.005),
                  (0.9, 0.45), (0.8, 0.64),
                  (1.3, .9), (1.5, .6))

        for b, s in ratios:
            for i in range(1, 100):
                b1, s1 = b * i, s * i
                strat.add_decision_maker(MACDRSIMaker,
                                         buy_ratio=b1,
                                         sell_ratio=s1)
        for s, b in ratios:
            for i in range(1, 100):
                b1, s1 = b * i, s * i
                strat.add_decision_maker(MACDRSIMaker,
                                         buy_ratio=b1,
                                         sell_ratio=s1)
    else:
        if strat.stock_data_frame is None:
            strat.set_stock_df(StockDataFrame.retype(df))
        sdf = strat.stock_data_frame

    print("Processing decisions.")
    strat.execute()
    print("Execution finished. Compiling results.")
    results, trade_list = list(), list()

    for idx, maker in enumerate(strat.makers):
        inputs = maker.inputs()
        tset = maker.tset
        inputs['profit'] = tset.get_profit()
        inputs['bought'] = tset.get_total_bought()
        inputs['trades'] = tset.trades
        inputs['start_funds'] = tset.start_funds
        inputs['end_funds'] = tset.funds
        inputs['pnl'] = tset.get_pnl()
        inputs['maker_id'] = idx
        tdf = tset.df
        if not tdf.empty:
            tdf.loc[:, 'maker_id'] = idx

        results.append(inputs)
        trade_list.append(tdf)

    print("Calculating PNL")
    strat_df = pd.DataFrame(data=results, index=range(len(results)))
    strat_df.sort_values(['profit'], ascending=[False], inplace=True)
    strat_df = strat_df.loc[strat_df['profit'] > -100, :]

    print("Composing trade data")
    trade_df = pd.concat(trade_list)
    if not trade_df.empty:
        trade_df = pd.merge(strat_df, trade_df, how='left', on='maker_id')
        sdf_bit = sdf.loc[:, ['open', 'low', 'high', 'close', 'rsi_6', 'macd', 'time']]
        trade_df = pd.merge(trade_df, sdf_bit, how='left', on=['time'])

    print("Writing files.")
    sdf.to_csv(out_path, index=False)
    strat_df.to_csv(pout_path, index=False)
    trade_df.to_csv(tout_path, index=False)
    print("Done: {}".format(out_path))
    try:
        top_id = int(strat_df.iloc[0]['maker_id'])
        print("Top decision maker: {}".format(strat.makers[top_id]))
    except:
        pass
    return tout_path, trade_df



if __name__ == '__main__':
    data_dir = config['DATA_DIRECTORY']
    product = 'LTC-USD'
    day_range = 60
    start = now_minus(days=60)
    end = now()
    granularity = 60*60*4
    grans = [(60*60, 4), (60*15, 3)]

    results = list()
    for i in range(30):
        fp, df = run_macd_rsi_decisions(data_dir,
                                        product,
                                        start,
                                        end,
                                        granularity,
                                        overwrite=False)
        results.append((fp, df))
        start -= pd.DateOffset(day_range)
        end -= pd.DateOffset(day_range)
        print("Start: {}, End: {}".format(start, end))
        if fp is None:
            break

    master_path = os.path.join(data_dir, '{}-BTEST-MASTER-TRADES-{}.csv'.format(product, granularity))
    if not os.path.exists(master_path):
        df = pd.concat([r[1] for r in results])
        df.to_csv(master_path, index=False)
        print("Entry tests complete: {}".format(master_path))
    else:
        df = pd.read_csv(master_path, parse_dates=['time'])

    df.sort_values(['pnl'], ascending=[False], inplace=True)
    # Get buy ratio and sell ratio with highest average return.
    df.drop_duplicates(subset=['pnl', 'buy_ratio', 'sell_ratio'], inplace=True)
    tops = df.iloc[:15]
    avg_buy_ratio = tops.buy_ratio.mean()
    avg_sell_ratio = tops.sell_ratio.mean()

    results = list()
    for gran, days in grans:
        start = now_minus(days=days)
        end = now()
        for _ in range(int(365/days)):
            strat = Strategy(margin=False, funds=1500, position_size=5)
            for idx, row in tops.iterrows():
                strat.add_decision_maker(MACDRSIMaker,
                                         buy_ratio=row['buy_ratio'],
                                         sell_ratio=row['sell_ratio'])
            fp, df = run_macd_rsi_decisions(data_dir,
                                            product,
                                            start,
                                            end,
                                            gran,
                                            overwrite=False,
                                            strat=strat)
            if fp is not None and not df.empty:
                df.loc[:, 'granularity'] = gran
            results.append((fp, df))
            day_change = pd.DateOffset(days=days)
            start -= day_change
            end -= day_change
    df = pd.concat([r[1] for r in results])

    final_path = os.path.join(data_dir, '{}-BTEST-FINAL-TRADES.csv'.format(product))
    df.to_csv(final_path, index=False)
    print("Final tests complete: {}".format(final_path))














