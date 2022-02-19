# Gemini Trading bot
# Author: Deepak Dasarathan

import math
import sys
import time
from enum import Enum
from pprint import pprint, pformat

from robin_stocks import gemini as g

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_signals import GeminiSignals


class OrderState(Enum):
    PLACED = 1
    PARTIAL_FILLED = 2
    FILLED = 3
    CANCELLED = 4
    UNKNOWN = 5


def get_lowest_outstanding_trade(symbol):
    outstanding_lots = GEMINI_OUTSTANDING_TRADE_LOTS[symbol]
    lowest_outstanding_lot = {}
    lowest_cost = float(sys.maxsize)
    for lot in outstanding_lots:
        if lot['cost'] < lowest_cost:
            lowest_cost = lot['cost']
            lowest_outstanding_lot = lot
    return lowest_outstanding_lot


def insert_recent_trade(symbol, trade_details):
    GEMINI_OUTSTANDING_TRADE_LOTS[symbol].append(trade_details)
    pickle.dump(GEMINI_OUTSTANDING_TRADE_LOTS, open(GEMINI_OUTSTANDING_TRADE_LOTS_FILE, 'wb'))


def remove_coin(symbol):
    del GEMINI_OUTSTANDING_TRADE_LOTS[symbol]
    pickle.dump(GEMINI_OUTSTANDING_TRADE_LOTS, open(GEMINI_OUTSTANDING_TRADE_LOTS_FILE, 'wb'))


def create_trade_details(symbol, order_id, client_order_id, quantity, cost, amount, created, created_ms):
    return {
        'symbol': symbol,
        'order_id': order_id,
        'client_order_id': client_order_id,
        'quantity': quantity,
        'cost': cost,
        'amount': amount,
        'created': created,
        'created_ms': created_ms
    }


# What's the percentage B has dipped compared to A
def percentage_dip_expr(a, b):
    _a = float(a)
    _b = float(b)
    return round(((_a - _b) / _a) * 100, 4)


# What's the percentage A has gain to match B
def percentage_break_even(a, b):
    _a = float(a)
    _b = float(b)
    return round(((_b - _a) / _a) * 100, 4)


def evaluate_exponential_trading_closeness_values(symbol):
    outstanding_lots = GEMINI_OUTSTANDING_TRADE_LOTS[symbol]
    index = len(outstanding_lots)
    if index < len(GEMINI_PURCHASE_AMOUNTS):
        trading_amount = GEMINI_PURCHASE_AMOUNTS[index]
        closeness_percentage = GEMINI_PERCENTAGES[index]
    else:
        trading_amount = GEMINI_PURCHASE_AMOUNTS[-1]
        closeness_percentage = GEMINI_PERCENTAGES[-1]
    return float(trading_amount), float(closeness_percentage)


def get_volatility_percentage_latest(symbol):
    outstanding_lots = GEMINI_OUTSTANDING_TRADE_LOTS[symbol]
    index = len(outstanding_lots)
    if index < len(GEMINI_PERCENTAGES):
        return GEMINI_PERCENTAGES[index - 1]
    else:
        return GEMINI_PERCENTAGES[-1]


def get_account_balance():
    balance = 0.0
    positions, _ = g.check_notional_balances(True)
    for position in positions:
        currency = position['currency'].lower()
        if currency == 'usd':
            amount = float(position['amount'])
            available = float(position['available'])
            if math.isclose(amount, available):
                balance = amount
            else:
                print("Account balance mismatch", amount, available)
                balance = available
    return balance


def get_min_quantity(symbol):
    symbol_details, _ = g.get_symbol_details(symbol, True)
    return float(symbol_details['min_order_size'])


def get_current_quote(symbol):
    """ Gets the recent trading information for a crypto.
    :Dictionary Keys: * symbol - BTCUSD etc.
                      * open - Open price from 24 hours ago
                      * high - High price from 24 hours ago
                      * low - Low price from 24 hours ago
                      * close - Close price (most recent trade)
                      * changes - Hourly prices descending for past 24 hours
                      * bid - Current best bid
                      * ask - Current best offer
    """
    quote, _ = g.get_ticker(symbol, True)
    return quote


def get_high_price(symbol):
    current_quote = get_current_quote(symbol)
    high_price = float(current_quote['high'])
    return high_price


def get_quantity(symbol):
    """  Gets a list of all available balances in every currency.
    :Dictionary Keys: * currency - The currency code.
                      * amount - The current balance
                      * available - The amount that is available to trade
                      * availableForWithdrawal - The amount that is available to withdraw
                      * type - "exchange"
   """
    quantity = None
    positions, _ = g.check_available_balances(True)
    for position in positions:
        currency = position['currency'].lower()
        if currency in symbol and currency != 'usd':
            amount = float(position['amount'])
            available = float(position['available'])
            if math.isclose(amount, available):
                quantity = amount
            else:
                print("Sell:", symbol, "All quantity not available to trade", amount, available)
    if GEMINI_VERBOSE:
        print("Sell:", symbol, "Found symbol, quantity", quantity)
        print()
    return quantity


def get_signals(symbol):
    high_price = get_high_price(symbol)
    quote = get_current_quote(symbol)
    ask_price = quote['ask']
    bid_price = quote['bid']
    percentage_dip = percentage_dip_expr(high_price, ask_price)
    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)

    closeness_to_lowest_trade = 0.0
    percentage_up = 0.0
    total_amount = 0.0
    total_cost = 0.0
    total_quantity = 0.0
    break_even = 0.0

    if bool(lowest_outstanding_lot):
        closeness_to_lowest_trade = percentage_dip_expr(lowest_outstanding_lot['cost'], ask_price)

    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        total_amount, total_cost, total_quantity, break_even = evaluate_break_even_and_profit(symbol, quote)
        percentage_up = percentage_break_even(total_cost, bid_price)

    volatility_percentage = get_volatility_percentage_latest(symbol)
    sell_at = total_cost * (1.0 + volatility_percentage / 100.0)

    trading_amount_dollars, closeness_percentage = evaluate_exponential_trading_closeness_values(symbol)

    if bool(lowest_outstanding_lot):
        buy_at = lowest_outstanding_lot['cost'] * (1.0 - closeness_percentage / 100.0)
    else:
        buy_at = high_price * (1.0 - closeness_percentage / 100.0)

    signal = GeminiSignals(symbol,
                           ask_price,
                           bid_price,
                           high_price,
                           float(quote['low']),
                           float(quote['open']),
                           float(quote['close']),
                           closeness_to_lowest_trade,
                           percentage_dip,
                           percentage_up,
                           total_amount,
                           total_cost,
                           total_quantity,
                           break_even,
                           sell_at,
                           buy_at,
                           lowest_outstanding_lot)
    return signal


def evaluate_break_even_and_profit(symbol, current_quote):
    outstanding_lots = GEMINI_OUTSTANDING_TRADE_LOTS[symbol]
    total_amount = 0.0
    total_quantity = 0.0
    total_cost = 0.0
    for lot in outstanding_lots:
        total_amount = total_amount + lot['amount']
        total_quantity = total_quantity + lot['quantity']
    if total_quantity > 0.0:
        total_cost = total_amount / total_quantity
    current_bid_price = float(current_quote['bid'])
    break_even = percentage_break_even(current_bid_price, total_cost)
    return total_amount, total_cost, total_quantity, break_even


def get_order_execution_state(order_status):
    if order_status['is_cancelled']:
        return OrderState.CANCELLED

    elif (order_status['is_live'] and
          math.isclose(float(order_status['executed_amount']), 0.0) and
          math.isclose(float(order_status['remaining_amount']), float(order_status['original_amount']))
          ):
        return OrderState.PLACED

    elif (order_status['is_live'] and
          float(order_status['remaining_amount']) > 0.0 and
          float(order_status['executed_amount']) > 0.0 and
          not math.isclose(float(order_status['remaining_amount']), float(order_status['original_amount'])) and
          not math.isclose(float(order_status['executed_amount']), float(order_status['original_amount']))
          ):
        return OrderState.PARTIAL_FILLED

    elif (not order_status['is_live'] and
          math.isclose(float(order_status['remaining_amount']), 0.0) and
          math.isclose(float(order_status['executed_amount']), float(order_status['original_amount']))
          ):
        return OrderState.FILLED

    else:
        return OrderState.UNKNOWN


def place_and_check_order_executed_or_cancel(symbol, quantity, side, price):
    filled = False
    canceled = False
    order_in_placed_counter = 0

    min_quantity = get_min_quantity(symbol)
    if side == "buy" and quantity < min_quantity:
        quantity = min_quantity
    # Place an order
    order_status, _ = g.order(symbol, quantity, side, price=price, options=["maker-or-cancel"], jsonify=True)
    order_id = order_status['order_id']

    while not filled and not canceled:
        order_state = get_order_execution_state(order_status)

        if order_state == OrderState.PLACED or order_state == OrderState.PARTIAL_FILLED:
            # do nothing, wait (cancel after a while)
            order_in_placed_counter = order_in_placed_counter + 1
            if order_in_placed_counter % GEMINI_MAX_RETRIES == 0:
                print(side + ":", symbol, "Current quote", get_current_quote(symbol))
                print(side + ":", symbol, GEMINI_MAX_RETRIES,
                      "attempts passed and the limit buy order still did not execute. Canceling!")
                print(side + ":", symbol, "Order has Placed status", order_state, pformat(order_status))
                order_status, _ = g.cancel_order(order_id, jsonify=True)
                print(side + ":", symbol, "Attempted to cancel order", pformat(order_status))

        elif order_state == OrderState.FILLED:
            # done! order is filled, so exit
            filled = True

        elif order_state == OrderState.CANCELLED:
            # order got cancelled
            canceled = True

        else:
            print("Order has unknown status", order_state, order_status, symbol)
            sys.exit(-1)

        time.sleep(0.2)

        # refresh the order status
        order_status, _ = g.order_status(order_id, jsonify=True)

    return order_status
