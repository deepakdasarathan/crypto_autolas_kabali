# Robinhood Trading bot
# Author: Deepak Dasarathan

import os.path
import pickle
import sys
import time
from collections import defaultdict
from prettytable import PrettyTable
from robin_stocks import robinhood as r
from requests import exceptions
from termcolor import colored

DRY_RUN = False
VERBOSE = False
MAX_RETRIES = 100
STARTING_AMOUNT = 1.0
STARTING_PERCENTAGE = 1.0
RAMPED_PERCENTAGE = 2.5
TRADE_LIMIT_PRICE = 7.5
VOLATILITY_PERCENTAGE = 5.0
CLOSENESS_PERCENTAGE = 2.5
DIP_PERCENTAGE = 1.0
HIGH_HISTORICAL_WINDOW = 24
NO_OF_OUTSTANDING_TRADES = 9
CRYPTO_LIST = ["BCH", "BSV", "BTC", "DOGE", "ETH", "ETC", "LTC"]
NEW_STRATEGY = ["BCH", "BSV", "BTC", "DOGE", "ETH", "ETC", "LTC"]
OUTSTANDING_TRADE_LOTS = defaultdict(list)
OUTSTANDING_TRADE_LOTS_FILE = "outstanding_lots"
PERCENTAGES = [0.9, 1.0125, 1.1390625, 1.281445313, 1.441625977, 1.621829224,
               1.824557877, 2.052627611, 2.309206063, 2.59785682]
PURCHASE_AMOUNTS = [1.0, 1.4, 1.96, 2.75, 3.5, 7.0, 14.0, 28.0, 56.0, 112.0]
lot_stats = PrettyTable()
lot_stats.field_names = ["Coin", "Amount", "Cost", "Quantity", "Trade Id", "Order Placed"]
quote_stats = PrettyTable()
quote_stats.field_names = ["Coin", "High 24H", "Ask", "Bid", "Mark", "High", "Low", "Open", "% Dip from high",
                           "% Up from Avg. Cost", "% Close to Lowest"]
break_even_and_profit_stats = PrettyTable()
break_even_and_profit_stats.field_names = ["Coin", "Total Amount", "Total Quantity", "Average Cost",
                                           "Current Bid", "% Break Even"]


def get_lowest_outstanding_trade(symbol):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    lowest_outstanding_lot = {}
    lowest_cost = float(sys.maxsize)
    for lot in outstanding_lots:
        if float(lot['cost']) < lowest_cost:
            lowest_cost = float(lot['cost'])
            lowest_outstanding_lot = lot
    return lowest_outstanding_lot


def insert_recent_trade(symbol, trade_details):
    OUTSTANDING_TRADE_LOTS[symbol].append(trade_details)
    pickle.dump(OUTSTANDING_TRADE_LOTS, open(OUTSTANDING_TRADE_LOTS_FILE, 'wb'))
    print_state()


def remove_matched_trade(symbol, trade_details):
    OUTSTANDING_TRADE_LOTS[symbol].remove(trade_details)
    pickle.dump(OUTSTANDING_TRADE_LOTS, open(OUTSTANDING_TRADE_LOTS_FILE, 'wb'))
    print_state()


def remove_coin(symbol):
    del OUTSTANDING_TRADE_LOTS[symbol]
    pickle.dump(OUTSTANDING_TRADE_LOTS, open(OUTSTANDING_TRADE_LOTS_FILE, 'wb'))
    print_state()


def create_trade_details(symbol, order_id, quantity, cost, amount, created, updated):
    return {
        'symbol': symbol,
        'id': order_id,
        'quantity': quantity,
        'cost': cost,
        'amount': amount,
        'created': created,
        'updated': updated
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


def check_order_executed_or_cancel(symbol, order_type, order_id):
    filled_order = {}
    filled = False
    canceled = False
    retries = 0
    while not filled and not canceled:
        filled_order = r.get_crypto_order_info(order_id)
        if filled_order['state'] == "filled":
            filled = True
        time.sleep(0.1)
        retries = retries + 1
        # retry for a few minutes and then cancel order
        if retries % MAX_RETRIES == 0:
            print(order_type + ":", symbol, "Current quote", r.get_crypto_quote(symbol))
            r.cancel_crypto_order(order_id)
            print(order_type + ":", symbol, "10s passed and the limit buy order still did not execute. Canceling!")
            canceled = True
    return filled_order, canceled


def evaluate_trading_amount(symbol):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    if len(outstanding_lots) <= 5:
        return STARTING_AMOUNT
    else:
        lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
        return float(lowest_outstanding_lot['amount']) * 2.0


def evaluate_closeness_percentage(symbol):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    if len(outstanding_lots) < 5:
        return STARTING_PERCENTAGE
    else:
        return RAMPED_PERCENTAGE


def get_high_price(symbol):
    historical_quotes = r.get_crypto_historicals(symbol=symbol)
    high_price = float(-1.0)
    for historical in historical_quotes[-HIGH_HISTORICAL_WINDOW:]:
        if float(historical['high_price']) > high_price:
            high_price = float(historical['high_price'])
    return high_price


def evaluate_exponential_trading_closeness_values(symbol):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    index = len(outstanding_lots)
    if index < len(PURCHASE_AMOUNTS):
        trading_amount = PURCHASE_AMOUNTS[index]
        closeness_percentage = PERCENTAGES[index]
    else:
        trading_amount = PURCHASE_AMOUNTS[-1]
        closeness_percentage = PERCENTAGES[-1]
    return trading_amount, closeness_percentage


def get_signals(symbol, quote, high_price):
    current_ask_price = float(quote['ask_price'])
    percentage_dip = percentage_dip_expr(high_price, current_ask_price)

    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
    closeness_to_lowest_trade = 0.0
    if bool(lowest_outstanding_lot):
        closeness_to_lowest_trade = percentage_dip_expr(lowest_outstanding_lot['cost'], current_ask_price)

    percentage_up = 0.0
    if len(OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        total_amount, total_cost, total_quantity, current_bid_price, break_even = evaluate_break_even_and_profit(symbol,
                                                                                                                 quote)
        percentage_up = percentage_break_even(total_cost, current_bid_price)
    return current_ask_price, percentage_dip, lowest_outstanding_lot, closeness_to_lowest_trade, percentage_up


def buy_trade_logic(symbol, quote, high_price):
    trading_amount_dollars, closeness_percentage = evaluate_exponential_trading_closeness_values(symbol)

    current_ask_price, percentage_dip, lowest_outstanding_lot, closeness_to_lowest_trade, percentage_up = \
        get_signals(symbol, quote, high_price)

    if not DRY_RUN:
        if (percentage_dip > closeness_percentage and
                (not lowest_outstanding_lot or
                 (float(lowest_outstanding_lot['cost']) > current_ask_price and
                  closeness_to_lowest_trade > closeness_percentage)) and
                len(OUTSTANDING_TRADE_LOTS[symbol]) < NO_OF_OUTSTANDING_TRADES):

            #    then place an order at ask_price
            placed_buy_order = r.order_buy_crypto_limit_by_price(symbol, trading_amount_dollars,
                                                                 r.helper.round_price(current_ask_price))

            if bool(lowest_outstanding_lot):
                print("Buy:", symbol, "Lowest lot", lowest_outstanding_lot)
                print("Buy:", symbol, "Closeness to lowest trade", closeness_to_lowest_trade)
                print("Buy:", symbol, "Trading Amount:", trading_amount_dollars, "Closeness:", closeness_percentage)
            print("Buy:", symbol, "Order placed", placed_buy_order)

            filled_buy_order, canceled = check_order_executed_or_cancel(symbol, "Buy", placed_buy_order['id'])

            # ensure cancel went through
            if not canceled:
                placed_buy_trade = create_trade_details(symbol, filled_buy_order['id'],
                                                        filled_buy_order['cumulative_quantity'],
                                                        filled_buy_order['average_price'],
                                                        filled_buy_order['entered_price'],
                                                        filled_buy_order['created_at'],
                                                        filled_buy_order['updated_at'])
                insert_recent_trade(symbol, placed_buy_trade)


def evaluate_break_even_and_profit(symbol, current_quote):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    total_amount = 0.0
    total_quantity = 0.0
    total_cost = 0.0
    for lot in outstanding_lots:
        total_amount = total_amount + float(lot['amount'])
        total_quantity = total_quantity + float(lot['quantity'])
    if total_quantity > 0.0:
        total_cost = total_amount / total_quantity
    current_bid_price = float(current_quote['bid_price'])
    break_even = percentage_break_even(current_bid_price, total_cost)
    return total_amount, total_cost, total_quantity, current_bid_price, break_even


def sell_trade_logic_close_all(symbol, quote):
    if len(OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        total_amount, total_cost, total_quantity, current_bid_price, break_even = evaluate_break_even_and_profit(symbol,
                                                                                                                 quote)
        percentage_up = percentage_break_even(total_cost, current_bid_price)
        positions = r.get_crypto_positions()
        quantity = -1.0
        for position in positions:
            if position['currency']['code'] == symbol:
                quantity = float(position['quantity'])
                if VERBOSE:
                    print("New Strategy Sell: Found symbol, quantity", quantity)
                    print()

        if quantity > 0:
            if not DRY_RUN:
                if percentage_up > VOLATILITY_PERCENTAGE:
                    #   then place a sell order at bid_price
                    placed_sell_order = r.order_sell_crypto_limit(symbol, float(quantity),
                                                                  r.helper.round_price(current_bid_price))
                    print("New Strategy Sell:", symbol, "Percentage Up", percentage_up)
                    print("New Strategy Sell:", symbol, "Order placed", placed_sell_order)

                    filled_sell_order, canceled = check_order_executed_or_cancel(symbol,
                                                                                 "New Strategy Sell",
                                                                                 placed_sell_order['id'])

                    # ensure cancel went through
                    if not canceled:
                        remove_coin(symbol)
        else:
            print("New Strategy Sell:Quantity not found for", symbol)


def sell_trade_logic(symbol, current_quote):
    current_bid_price = float(current_quote['bid_price'])

    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
    percentage_up = 0.0
    if bool(lowest_outstanding_lot):
        # TODO change this
        percentage_up = ((current_bid_price - float(
            lowest_outstanding_lot['cost'])) / current_bid_price) * 100

    if not DRY_RUN:
        if (bool(lowest_outstanding_lot) and
                percentage_up > VOLATILITY_PERCENTAGE):
            #   then place a sell order at bid_price
            placed_sell_order = r.order_sell_crypto_limit(symbol, float(lowest_outstanding_lot['quantity']),
                                                          r.helper.round_price(current_bid_price))
            print("Sell:", symbol, "Lowest lot", lowest_outstanding_lot)
            if bool(lowest_outstanding_lot):
                print("Sell:", symbol, "Percentage Up", percentage_up)
            print("Sell:", symbol, "Order placed", placed_sell_order)

            filled_sell_order, canceled = check_order_executed_or_cancel(symbol, "Sell", placed_sell_order['id'])

            # ensure cancel went through
            if not canceled:
                remove_matched_trade(symbol, lowest_outstanding_lot)


def crypto_trading_logic(symbol):
    try:

        high_price = get_high_price(symbol)
        # get the current quote for the crypto
        current_quote = r.get_crypto_quote(symbol)

        # Run the buy algorithm
        buy_trade_logic(symbol, current_quote, high_price)

        # Run the sell algorithm
        if symbol in NEW_STRATEGY:
            sell_trade_logic_close_all(symbol, current_quote)
        else:
            sell_trade_logic(symbol, current_quote)

    except TypeError as e:
        print(e)
        return
    except exceptions.ReadTimeout as e:
        print(e)
        time.sleep(10)
        return
    except exceptions.ConnectionError as e:
        print(e)
        time.sleep(10)
        return


def login_to_robinhood(email, password):
    r.login(username=email, password=password, store_session=True, pickle_name="aarthika")


def print_signals(symbol, current_quote, percentage_dip, percentage_up, high_price, closeness):
    up_from_average_cost = percentage_up
    if percentage_up > 0.0:
        up_from_average_cost = colored(str(percentage_up), 'white', 'on_green')
    close_to_lowest = closeness
    if closeness > 0.0:
        close_to_lowest = colored(str(closeness), 'white', 'on_red')
    quote_stats.add_row([symbol, high_price, current_quote['ask_price'], current_quote['bid_price'],
                         current_quote['mark_price'], current_quote['high_price'], current_quote['low_price'],
                         current_quote['open_price'], percentage_dip, up_from_average_cost, close_to_lowest])


def print_break_even_and_profit_stats(symbol, quote):
    total_amount, total_cost, total_quantity, current_bid_price, break_even = \
        evaluate_break_even_and_profit(symbol, quote)
    break_even_and_profit_stats.add_row([symbol,
                                         total_amount,
                                         total_quantity,
                                         round(float(total_cost), 2),
                                         current_bid_price,
                                         break_even])


def print_state():

    try:
        total_crypto_bought_dollars = 0.0
        for c in CRYPTO_LIST:
            current_quote = r.get_crypto_quote(c)
            print_break_even_and_profit_stats(c, current_quote)

            high_price = get_high_price(c)
            current_ask_price, percentage_dip, lowest_outstanding_lot, closeness_to_lowest_trade, percentage_up = \
                get_signals(c, current_quote, high_price)

            print_signals(c, current_quote, percentage_dip, percentage_up, high_price, closeness_to_lowest_trade)

            for lot in OUTSTANDING_TRADE_LOTS[c]:
                lot_stats.add_row([c,
                                   round(float(lot['amount']), 8),
                                   round(float(lot['cost']), 8),
                                   round(float(lot['quantity']), 8),
                                   lot['id'],
                                   lot['updated']])
                total_crypto_bought_dollars = total_crypto_bought_dollars + float(lot['amount'])

            if len(OUTSTANDING_TRADE_LOTS[c]) > 0:
                print(lot_stats.get_string())
                lot_stats.clear_rows()

        cash_balance = float(r.load_portfolio_profile()['equity'])
        total_equity = total_crypto_bought_dollars + cash_balance
        print("\nTotal $$s spent to buy crypto:", round(float(total_crypto_bought_dollars), 2),
              "Available Cash $$:", cash_balance,
              "Total equity $$s:", total_equity)
        print()
        print(break_even_and_profit_stats.get_string())
        break_even_and_profit_stats.clear_rows()

        print(quote_stats.get_string())
        quote_stats.clear_rows()
    except TypeError as e:
        print(e)
        return
    print()


if __name__ == '__main__':
    _email = os.environ.get('ROBINHOOD_EMAIL')
    _password = os.environ.get('ROBINHOOD_PASSWORD')

    login_to_robinhood(_email, _password)

    # Read initial state
    if os.path.exists(OUTSTANDING_TRADE_LOTS_FILE):
        OUTSTANDING_TRADE_LOTS = pickle.load(open(OUTSTANDING_TRADE_LOTS_FILE, 'rb'))
    print_state()
    run_count = 0
    while True:
        for crypto in CRYPTO_LIST:
            crypto_trading_logic(crypto)
        time.sleep(1)
        run_count = run_count + 1
        if run_count % 500 == 0:
            print("Run count:", run_count)
            print_state()
