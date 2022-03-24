# Gemini Trading bot
# Author: Deepak Dasarathan

from dataclasses import dataclass


@dataclass
class GeminiSignals:
    symbol: str
    ask: str
    bid: str
    high: float
    low: float
    open: float
    close: float
    closeness_to_lowest_trade: float
    percentage_dip: float
    percentage_up: float
    percentage_up_from_last_trade: float
    total_amount: float
    avg_cost: float
    total_quantity: float
    break_even: float
    sell_at: float
    sell_at_recent_trade: float
    buy_at: float
    lowest_outstanding_lot: {}
