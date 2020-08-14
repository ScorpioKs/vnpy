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


class FbbStrategy(CtaTemplate):
    """"""

    author = "feng.shao"

    boll_window = 20  #
    boll_dev = 2.0  #
    boll_bw_limit = 0.01
    fixed_size: float = 0.2  # 单笔buy 暂时固定为总资产的 千分之 1～4  （风险随之增加）
    limit_amt = 10.0  # 最小交易资金10 USDT -binance


    #BB
    boll_up = 0
    boll_down = 0
    boll_mid = 0
    boll_pb = 0
    boll_bw = 0

    #kdj

    k = 0
    d = 0
    j = 0

    last_boll_pb = 0


    parameters = [
        "boll_window",
        "boll_dev",
        # "boll_dev_2",
        # "boll_pb_sal",
        "boll_bw_limit",
        "fixed_size"
    ]
    variables = [
        # "boll_up",
        # "boll_down",
        # "boll_mid",
        "boll_pb",
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

        # start
        self.get_boll(bar)
        self.get_kdj()

        print(str(self.k) + "  -  " + str(self.d) + "  -  " + str(self.j) + "  -  " + bar.datetime.strftime("%Y-%m-%d %H:%M:%S"))

        # 低于 boll_down 并且width 不小于limit 买入
        if self.boll_pb <= 0 and self.boll_bw > self.boll_bw_limit:
            self.buy(bar.close_price, self.check_minimum_size(bar.close_price, self.fixed_size), False)


        if self.pos > 0:
            # 上穿 up 卖出信号
            if self.last_boll_pb < 1 <= self.boll_pb and self.boll_bw < self.boll_bw_limit:
                self.sell(bar.close_price, self.pos, False)
            # 未达up 而下穿 mid 卖出
            if self.last_boll_pb > 0.5 >= self.boll_pb and self.boll_bw < self.boll_bw_limit:
                self.sell(bar.close_price, self.pos, False)
            # down 下方 ，width 很小 卖出
            if self.boll_pb <= 0 and self.boll_bw <= self.boll_bw_limit:
                self.sell(bar.close_price, self.pos, False)


        self.last_boll_pb = self.boll_pb


        #     self.short(bar.close_price, self.fixed_size, False)


        #     self.cover(bar.close_price, self.pos, False)

        self.put_event()

    def check_minimum_size(self, price: float, order_size) -> float:
        min_size = self.size_by_limit_amt(self.limit_amt, price)
        return max(order_size, min_size)

    def kdj_signal(self):
        if self.d <= self.k < 20:
            return True


    def get_boll(self, bar: BarData):
        self.boll_up, self.boll_mid, self.boll_down = self.am.boll(self.boll_window, self.boll_dev)
        self.boll_pb = self.percentbeta(bar.close_price, self.boll_up, self.boll_down)
        self.boll_bw = self.bandwidth(self.boll_up, self.boll_mid, self.boll_down)

    def get_kdj(self):
        self.k, self.d, self.j = self.am.kdj()

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
