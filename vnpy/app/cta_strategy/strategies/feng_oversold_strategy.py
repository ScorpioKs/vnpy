from vnpy.app.cta_strategy import (
    CtaTemplate,
    CtaEngine,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import math

from vnpy.trader.utility import Interval


class FengOversoldStrategy(CtaTemplate):
    """高百分比超跌恢复策略"""

    author = "feng.shao"

    oversold_pct = -0.05  # 当日跌幅超过5%
    limit_amt = 10.0  # 最小交易资金10 USDT -binance
    fixed_size = 1.0

    parameters = [
        "oversold_pct",
        "fixed_size"
    ]
    variables = [
        "oversold_pct",
        "fixed_size"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 1, self.on_day_bar, Interval.DAILY, 8)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.bg.update_bar(bar)

    def on_day_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()
        am = self.am
        am.update_bar(bar)

        if not am.inited:
            return

        long_signal = 0
        min_size = max(self.fixed_size, self.size_by_limit_amt(self.limit_amt, bar.close_price))

        # 两日K 连续下跌，总跌幅超过 oversold_pct &，并且 (kdj 超跌，j <0 或 日K下穿 BOLL 上界超涨后的大跌)
        price_change_pct_d1 = (am.close_array[-2] - am.open_array[-2]) / am.open_array[-2]  # 计算第一日跌幅%
        price_change_pct_d2 = (am.close_array[-1] - am.open_array[-1]) / am.open_array[-1]  # 计算第二日跌幅%
        price_change_pct_2d = price_change_pct_d1 + price_change_pct_d2
        upper, middle, lower = am.boll(array=True)

        # 判断两日K线是否下穿过BOLL 上界
        downcross_flag = 0
        if am.open_array[-2] >= upper[-2] and am.close_array[-1] < lower[-1]:
            downcross_flag = 1

        k, d, j = am.kdj()
        if price_change_pct_d1 < 0 and price_change_pct_d2 < 0 and \
                price_change_pct_2d <= self.oversold_pct and \
                (j < 0 or downcross_flag == 1):
            long_signal = 0

        # 日K 跌幅超过 oversold_pct
        price_change_pct = (bar.close_price - bar.open_price) / bar.open_price  # 计算当日跌幅
        print(str(bar.datetime) + " : " + str(price_change_pct))
        if price_change_pct <= self.oversold_pct:
            long_signal = 1

        # elif self.boll_pb >= 1 \
        #         and self.boll_pb_2 < 1:
        #     self.short(bar.close_price, self.fixed_size, False)

        if self.pos > 0:
            self.sell(bar.close_price, self.pos, False)

        print(str(bar.datetime) + " : " + str(price_change_pct) + " : " + str(price_change_pct_2d))
        if long_signal == 1:
            self.buy(bar.close_price, min_size, False)

        # elif self.pos < 0:
        #     if self.boll_pb <= 1-self.boll_pb_sal:
        #         self.cover(bar.close_price, self.pos, False)

        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass

    def percentbeta(self, close: float, up: float, low: float) -> float:
        """
        %b of boll
        """
        pb = (close - low) / (up - low)

        return pb

    def bandwidth(self, up: float, mid: float, low: float) -> float:
        """
        bandwidth of boll
        """
        bw = (up - low) / mid

        return bw

    def size_by_limit_amt(self, limit_amt: float, price: float) -> float:

        return math.ceil(limit_amt / price * 1000000) / 1000000
