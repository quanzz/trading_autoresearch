"""
Account, Position, Order, and Trade data models for the backtest framework.
Supports long and short positions with margin-based trading.

回测框架的账户、持仓、订单和交易数据模型。
支持多头和空头持仓，采用保证金交易模型。

FIXED — do not modify. The agent edits files under strategies/ instead.
固定模块 — 请勿修改。agent 在 strategies/ 目录下编辑策略文件。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class Direction(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class Bar:
    """A single OHLCV bar at minute granularity.

    分钟级别的单根 OHLCV K 线。"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    amt: float = 0.0       # turnover / 成交额
    oi: float = 0.0         # open interest / 持仓量


@dataclass
class Order:
    """A trading signal emitted by a strategy.

    策略发出的交易信号。"""
    symbol: str
    direction: Direction
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None

    def __repr__(self):
        return (f"Order({self.symbol}, {self.direction.value}, "
                f"qty={self.quantity}, type={self.order_type.value})")


@dataclass
class Trade:
    """A filled order with execution details.

    已成交的订单，包含执行详情。"""
    timestamp: str
    symbol: str
    direction: Direction
    quantity: int
    price: float
    commission: float
    slippage: float
    notional: float = 0.0   # trade value = price * quantity * multiplier
                            # 交易价值 = 价格 × 数量 × 乘数

    def __repr__(self):
        return (f"Trade({self.timestamp}, {self.symbol}, {self.direction.value}, "
                f"qty={self.quantity}, price={self.price:.2f})")


@dataclass
class Position:
    """Current position in a single instrument.

    单个品种的当前持仓。"""
    symbol: str
    direction: Direction
    quantity: int
    avg_price: float

    def market_value(self, current_price: float, multiplier: float) -> float:
        return self.quantity * current_price * multiplier

    def unrealized_pnl(self, current_price: float, multiplier: float) -> float:
        if self.direction == Direction.LONG:
            return (current_price - self.avg_price) * self.quantity * multiplier
        else:
            return (self.avg_price - current_price) * self.quantity * multiplier


class Account:
    """
    Simulated trading account with cash, positions, and trade history.
    Supports long and short positions (Chinese futures standard).
    Uses margin-based trading: only margin (not full notional) is
    reserved when opening a position.

    模拟交易账户，包含现金、持仓和交易历史。
    支持多头和空头持仓（中国期货标准）。
    使用保证金交易模型：开仓时仅冻结保证金，而非全额名义价值。
    """

    def __init__(self, initial_capital: float, commission_rate: float = 0.0003,
                 slippage_rate: float = 0.0001, multiplier: float = 1.0,
                 allow_short: bool = True, margin_rate: float = 0.10):
        self.initial_capital = initial_capital
        self.cash = initial_capital          # available cash / 可用现金
        self.frozen_margin = 0.0             # margin locked in positions / 持仓占用的保证金
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.multiplier = multiplier
        self.allow_short = allow_short
        self.margin_rate = margin_rate        # margin rate / 保证金率

        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self._equity_timestamps: List[str] = []

    # ------------------------------------------------------------------
    # Order execution
    # 订单执行
    # ------------------------------------------------------------------

    def execute_order(self, order: Order, fill_price: float,
                      timestamp: str) -> Optional[Trade]:
        """
        Execute an order at the given fill price.
        Returns the filled Trade, or None if rejected (insufficient funds).

        Margin model: only margin + commission is deducted from cash.

        以给定的成交价执行订单。
        返回已成交的 Trade，如果被拒绝（资金不足）则返回 None。

        保证金模型：仅从现金中扣除保证金 + 佣金。
        """
        if not self.allow_short and order.direction == Direction.SHORT:
            return None

        if order.quantity <= 0:
            return None

        # Apply slippage: adverse price movement
        # 应用滑点：不利价格变动
        slippage_amount = fill_price * self.slippage_rate
        if order.direction == Direction.LONG:
            exec_price = fill_price + slippage_amount
        else:
            exec_price = fill_price - slippage_amount

        notional = exec_price * order.quantity * self.multiplier
        commission = notional * self.commission_rate
        margin_required = notional * self.margin_rate

        symbol = order.symbol

        # ------------------------------------------------------------------
        # Position update with margin accounting
        # 持仓更新 + 保证金核算
        # ------------------------------------------------------------------
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.direction == order.direction:
                # Same direction — increase existing position
                # 同方向 — 加仓
                total_needed = margin_required + commission
                if total_needed > self.cash:
                    return None

                self.cash -= total_needed
                self.frozen_margin += margin_required

                # Weighted-average entry price
                # 加权平均开仓价
                total_qty = pos.quantity + order.quantity
                pos.avg_price = ((pos.avg_price * pos.quantity +
                                  exec_price * order.quantity) / total_qty)
                pos.quantity = total_qty
            else:
                # Opposite direction — close or reverse
                # 相反方向 — 平仓或反转

                close_qty = min(order.quantity, pos.quantity)

                # Release margin for the closed portion.
                # Margin was frozen at position's avg_price.
                # 释放已平仓部分的保证金（按持仓均价计算冻结额）。
                closed_notional = close_qty * pos.avg_price * self.multiplier
                released_margin = closed_notional * self.margin_rate

                # Realized P&L on closed portion
                # 已平仓部分的已实现盈亏
                if pos.direction == Direction.LONG:
                    close_pnl = (exec_price - pos.avg_price) * close_qty * self.multiplier
                else:
                    close_pnl = (pos.avg_price - exec_price) * close_qty * self.multiplier

                # Net cash change:
                #   - commission (real cost on full order)
                #   + released margin from closed position
                #   + realized P&L
                # 现金净变动：- 佣金 + 释放保证金 + 已实现盈亏
                self.cash -= commission
                self.cash += released_margin + close_pnl
                self.frozen_margin -= released_margin

                if close_qty >= pos.quantity:
                    # Fully closed
                    # 完全平仓
                    del self.positions[symbol]
                else:
                    # Partially closed
                    # 部分平仓
                    pos.quantity -= close_qty

                # If remaining quantity, open new position in opposite direction.
                # Commission was already fully deducted above.
                # 如果还有剩余数量，以相反方向开新仓。佣金已在上方全部扣除。
                remaining = order.quantity - close_qty
                if remaining > 0:
                    new_notional = exec_price * remaining * self.multiplier
                    new_margin = new_notional * self.margin_rate

                    if new_margin > self.cash:
                        # Edge case: can't afford margin for reversal.
                        # Skip reversal — position stays closed.
                        # 边界情况：可用资金不足以支付反转仓位保证金。跳过反转。
                        pass
                    else:
                        self.cash -= new_margin
                        self.frozen_margin += new_margin
                        self.positions[symbol] = Position(
                            symbol=symbol,
                            direction=order.direction,
                            quantity=remaining,
                            avg_price=exec_price,
                        )
        else:
            # New position
            # 新开仓
            total_needed = margin_required + commission
            if total_needed > self.cash:
                return None

            self.cash -= total_needed
            self.frozen_margin += margin_required
            self.positions[symbol] = Position(
                symbol=symbol,
                direction=order.direction,
                quantity=order.quantity,
                avg_price=exec_price,
            )

        trade = Trade(
            timestamp=timestamp,
            symbol=symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=exec_price,
            commission=commission,
            slippage=slippage_amount,
            notional=notional,
        )
        self.trades.append(trade)
        return trade

    # ------------------------------------------------------------------
    # Mark-to-market
    # 逐日盯市
    # ------------------------------------------------------------------

    def mark_to_market(self, timestamp: str, prices: Dict[str, float]):
        """
        Record current equity given market prices for all held instruments.
        Call once per bar.

        Margin-model equity:
          equity = available_cash + frozen_margin + unrealized_pnl

        根据所有持仓品种的市价记录当前权益。
        每根 K 线调用一次。

        保证金模型权益：
          权益 = 可用现金 + 冻结保证金 + 未实现盈亏
        """
        total_equity = self.cash + self.frozen_margin
        for symbol, pos in self.positions.items():
            if symbol in prices:
                total_equity += pos.unrealized_pnl(prices[symbol], self.multiplier)
        self.equity_curve.append(total_equity)
        self._equity_timestamps.append(timestamp)
        return total_equity

    def get_equity(self) -> float:
        """Return latest total equity.

        返回最新的总权益。"""
        if self.equity_curve:
            return self.equity_curve[-1]
        return self.initial_capital

    # ------------------------------------------------------------------
    # Summary
    # 摘要
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Return a dict of account summary statistics.

        返回账户摘要统计字典。"""
        n_trades = len(self.trades)
        if n_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return": 0.0,
                "final_equity": self.initial_capital,
            }

        # P&L per trade (approximate — pairs buys and sells)
        # 每笔交易盈亏（近似 — 配对买入和卖出）
        wins = 0
        gross_pnl = 0.0
        # Track open/close pairs for win rate
        # 追踪开平仓配对以计算胜率
        trade_pnls = self._compute_trade_pnls()
        for pnl in trade_pnls:
            if pnl > 0:
                wins += 1
            gross_pnl += pnl

        win_rate = wins / len(trade_pnls) if trade_pnls else 0.0
        total_return = (self.get_equity() - self.initial_capital) / self.initial_capital

        return {
            "total_trades": n_trades,
            "win_rate": win_rate,
            "total_return": total_return,
            "final_equity": self.get_equity(),
            "gross_pnl": gross_pnl,
            "round_trips": len(trade_pnls),
        }

    def _compute_trade_pnls(self) -> List[float]:
        """
        Compute realized P&L per round-trip (open → close).
        Simplification: pairs sequential LONG trades with offsetting SELLs.

        计算每笔往返交易（开仓 → 平仓）的已实现盈亏。
        简化处理：按顺序配对 LONG 交易与对冲的 SELL。
        """
        pnls = []
        long_stack = []   # (quantity, price) for LONG entries / LONG 开仓（数量, 价格）
        short_stack = []  # (quantity, price) for SHORT entries / SHORT 开仓（数量, 价格）

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                long_stack.append((trade.quantity, trade.price))
            else:
                short_stack.append((trade.quantity, trade.price))

            # Match LONG entry with subsequent SHORT exit
            # 将 LONG 开仓与后续 SHORT 平仓配对
            while long_stack and short_stack:
                l_qty, l_price = long_stack[0]
                s_qty, s_price = short_stack[0]
                matched_qty = min(l_qty, s_qty)
                pnl = (s_price - l_price) * matched_qty * self.multiplier
                pnls.append(pnl)

                if l_qty > matched_qty:
                    long_stack[0] = (l_qty - matched_qty, l_price)
                    short_stack.pop(0)
                elif s_qty > matched_qty:
                    short_stack[0] = (s_qty - matched_qty, s_price)
                    long_stack.pop(0)
                else:
                    long_stack.pop(0)
                    short_stack.pop(0)

        return pnls
