"""
Account, Position, Order, and Trade data models for the backtest framework.
FIXED — do not modify. The agent edits strategy.py instead.
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
    """A single OHLCV bar at minute granularity."""
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
    """A trading signal emitted by a strategy."""
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
    """A filled order with execution details."""
    timestamp: str
    symbol: str
    direction: Direction
    quantity: int
    price: float
    commission: float
    slippage: float
    notional: float = 0.0   # trade value = price * quantity * multiplier

    def __repr__(self):
        return (f"Trade({self.timestamp}, {self.symbol}, {self.direction.value}, "
                f"qty={self.quantity}, price={self.price:.2f})")


@dataclass
class Position:
    """Current position in a single instrument."""
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
    Uses simplified margin model: full cash collateral for shorts.
    """

    def __init__(self, initial_capital: float, commission_rate: float = 0.0003,
                 slippage_rate: float = 0.0001, multiplier: float = 1.0,
                 allow_short: bool = True):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.multiplier = multiplier
        self.allow_short = allow_short

        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self._equity_timestamps: List[str] = []

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def execute_order(self, order: Order, fill_price: float,
                      timestamp: str) -> Optional[Trade]:
        """
        Execute an order at the given fill price.
        Returns the filled Trade, or None if rejected (insufficient funds).
        """
        if not self.allow_short and order.direction == Direction.SHORT:
            return None

        if order.quantity <= 0:
            return None

        # Apply slippage: adverse price movement
        slippage_amount = fill_price * self.slippage_rate
        if order.direction == Direction.LONG:
            exec_price = fill_price + slippage_amount
        else:
            exec_price = fill_price - slippage_amount

        notional = exec_price * order.quantity * self.multiplier
        commission = notional * self.commission_rate
        total_cost = notional + commission

        # Check sufficient funds
        if total_cost > self.cash:
            return None

        # Deduct cash
        self.cash -= total_cost

        # Update position
        symbol = order.symbol
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.direction == order.direction:
                # Increase existing position
                total_qty = pos.quantity + order.quantity
                pos.avg_price = ((pos.avg_price * pos.quantity +
                                  exec_price * order.quantity) / total_qty)
                pos.quantity = total_qty
            else:
                # Opposite direction — reduce or reverse
                if order.quantity >= pos.quantity:
                    # Close existing position
                    close_qty = pos.quantity
                    if pos.direction == Direction.LONG:
                        # Closing long: undo line 137 deduction + receive sale proceeds
                        self.cash += close_qty * exec_price * self.multiplier * 2
                    # else: closing short — line 137 deduction was correct
                    #        (buying to cover costs money), no refund needed
                    remaining = order.quantity - pos.quantity
                    if remaining > 0:
                        # Open new position in opposite direction
                        pos.direction = order.direction
                        pos.quantity = remaining
                        pos.avg_price = exec_price
                    else:
                        del self.positions[symbol]
                else:
                    # Partially close
                    if pos.direction == Direction.LONG:
                        self.cash += order.quantity * exec_price * self.multiplier * 2
                    # else: partial close of short, line 137 deduction stands
                    pos.quantity -= order.quantity
        else:
            # New position
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
    # ------------------------------------------------------------------

    def mark_to_market(self, timestamp: str, prices: Dict[str, float]):
        """
        Record current equity given market prices for all held instruments.
        Call once per bar.
        """
        total_equity = self.cash
        for symbol, pos in self.positions.items():
            if symbol in prices:
                total_equity += pos.market_value(prices[symbol], self.multiplier)
        self.equity_curve.append(total_equity)
        self._equity_timestamps.append(timestamp)
        return total_equity

    def get_equity(self) -> float:
        """Return latest total equity."""
        if self.equity_curve:
            return self.equity_curve[-1]
        return self.initial_capital

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Return a dict of account summary statistics."""
        n_trades = len(self.trades)
        if n_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return": 0.0,
                "final_equity": self.initial_capital,
            }

        # P&L per trade (approximate — pairs buys and sells)
        wins = 0
        gross_pnl = 0.0
        # Track open/close pairs for win rate
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
        """
        pnls = []
        long_stack = []  # (quantity, price) for LONG entries
        short_stack = []  # (quantity, price) for SHORT entries

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                long_stack.append((trade.quantity, trade.price))
            else:
                short_stack.append((trade.quantity, trade.price))

            # Match LONG entry with subsequent SHORT exit
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
