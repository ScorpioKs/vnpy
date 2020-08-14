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


class FengBollStrategy(CtaTemplate):
    """"""

    author = "feng.shao"

    boll_window = 25  #
    boll_dev = 2.0  #
    # boll_dev_2 = 3.1  #
    # boll_pb_sal = 0.5  #
    # boll_bw_limit = 0.01
    fixed_size: float = 0.2  # 单笔buy 暂时固定为总资产的 千分之 1～4  （风险随之增加）
    limit_amt = 10.0  # 最小交易资金10 USDT -binance

    sweet_point = 0

    # first BB
    boll_up = 0
    boll_down = 0
    boll_mid = 0
    boll_pb = 0
    boll_bw = 0

    # Second BB dev should larger then First BB
    # boll_up_2 = 0
    # boll_down_2 = 0
    # boll_mid_2 = 0
    # boll_pb_2 = 0
    # boll_bw_2 = 0

    parameters = [
        "boll_window",
        "boll_dev",
        # "boll_dev_2",
        # "boll_pb_sal",
        # "boll_bw_limit",
        "fixed_size"
    ]
    variables = [
        # "boll_up",
        # "boll_down",
        # "boll_mid",
        "boll_pb",
        "sweet_point",
        # "boll_bw",
        # "boll_up_2",
        # "boll_down_2",
        # "boll_mid_2",
        # "boll_pb_2",
        # "boll_bw_2",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 15, self.on_mins_bar)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_bar(2)

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

    def on_mins_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        self.cancel_all()

        am = self.am
        am.update_bar(bar)

        if not am.inited:
            return

        self.boll_up, self.boll_mid, self.boll_down = am.boll(self.boll_window, self.boll_dev)
        self.boll_pb = self.percentbeta(bar.close_price, self.boll_up, self.boll_down)
        self.boll_bw = self.bandwidth(self.boll_up, self.boll_mid, self.boll_down)

        if self.boll_pb <= 0:
            min_size = self.size_by_limit_amt(self.limit_amt, bar.close_price)
            self.buy(bar.close_price, max(self.fixed_size, min_size), False)

        # elif self.boll_pb >= 1 \
        #         and self.boll_pb_2 < 1:
        #     self.short(bar.close_price, self.fixed_size, False)

        if self.pos > 0:

            if bar.open_price < self.boll_mid <= bar.close_price \
                    or bar.open_price > self.boll_mid >= bar.close_price:
                self.sweet_point = self.sweet_point + 1

            if self.sweet_point == 2:
                self.sell(bar.close_price, self.pos, False)
                self.sweet_point = 0

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
