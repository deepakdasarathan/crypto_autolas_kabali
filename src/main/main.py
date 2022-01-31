# Robinhood Trading bot
# Author: Deepak Dasarathan

import os.path
import pickle
import sys
import time
from collections import defaultdict
from robin_stocks import robinhood as r
from requests import exceptions

DRY_RUN = False
VERBOSE = False
MAX_RETRIES = 100
STARTING_AMOUNT = 1.0
STARTING_PERCENTAGE = 1.0
RAMPED_PERCENTAGE = 2.5
TRADE_LIMIT_PRICE = 7.5
VOLATILITY_PERCENTAGE = 2.5
CLOSENESS_PERCENTAGE = 2.5
DIP_PERCENTAGE = 2.5
HIGH_HISTORICAL_WINDOW = 24
NO_OF_OUTSTANDING_TRADES = 10
CRYPTO_LIST = ["BCH", "BSV", "BTC", "DOGE", "ETH", "ETC", "LTC"]
NEW_STRATEGY = ["BTC"]
OUTSTANDING_TRADE_LOTS = defaultdict(list)
OUTSTANDING_TRADE_LOTS_FILE = "outstanding_lots"


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
    return ((_a - _b) / _a) * 100


# What's the percentage A has gain to match B
def percentage_break_even(a, b):
    _a = float(a)
    _b = float(b)
    return ((_b - _a) / _a) * 100


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
    if len(outstanding_lots) <= 5:
        return STARTING_PERCENTAGE
    else:
        return RAMPED_PERCENTAGE


def buy_trade_logic(symbol, current_quote):
    historical_quotes = r.get_crypto_historicals(symbol=symbol)
    high_price = float(-1.0)
    for historical in historical_quotes[-HIGH_HISTORICAL_WINDOW:]:
        if float(historical['high_price']) > high_price:
            high_price = float(historical['high_price'])

    # per crypto find the allocated trade quantity
    trading_amount_dollars = evaluate_trading_amount(symbol)
    closeness_percentage = evaluate_closeness_percentage(symbol)

    if VERBOSE:
        print("Initial:", symbol, "High price in window", high_price)
        print("Initial:", symbol, "Current quote", current_quote)

    # if current ask_price is < x% of the high in window and outstanding lots.lowest_price > current ask_price
    # and if outstanding orders cost is < 70% of allocated budget
    current_ask_price = float(current_quote['ask_price'])
    percentage_dip = percentage_dip_expr(high_price, current_ask_price)

    if VERBOSE:
        print("Buy:", symbol, "Percentage Dip", percentage_dip)

    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
    closeness_to_lowest_trade = 0.0
    if not DRY_RUN:
        if bool(lowest_outstanding_lot):
            closeness_to_lowest_trade = percentage_dip_expr(lowest_outstanding_lot['cost'], current_ask_price)

        if (percentage_dip > DIP_PERCENTAGE and
                (not lowest_outstanding_lot or
                 (float(lowest_outstanding_lot['cost']) > current_ask_price and
                  closeness_to_lowest_trade > closeness_percentage)) and
                len(OUTSTANDING_TRADE_LOTS[symbol]) < NO_OF_OUTSTANDING_TRADES):
            #    then place an order at ask_price
            placed_buy_order = r.order_buy_crypto_limit_by_price(symbol, trading_amount_dollars,
                                                                 r.helper.round_price(current_ask_price))
            print("Initial:", symbol, "High price in window", high_price)
            print("Initial:", symbol, "Current quote", current_quote)
            print("Buy:", symbol, "Percentage Dip", percentage_dip)
            if bool(lowest_outstanding_lot):
                print("Buy:", symbol, "Lowest lot", lowest_outstanding_lot)
                print("Buy:", symbol, "Closeness to lowest trade", closeness_to_lowest_trade)
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
                print_break_even_and_profit_stats(symbol, current_quote)
                print()


def evaluate_break_even_and_profit(symbol, current_quote):
    outstanding_lots = OUTSTANDING_TRADE_LOTS[symbol]
    total_amount = 0.0
    total_quantity = 0.0
    for lot in outstanding_lots:
        total_amount = total_amount + float(lot['amount'])
        total_quantity = total_quantity + float(lot['quantity'])
    total_cost = total_amount / total_quantity
    current_bid_price = float(current_quote['bid_price'])
    break_even = percentage_break_even(current_bid_price, total_cost)
    return total_amount, total_cost, total_quantity, current_bid_price, break_even


def print_break_even_and_profit_stats(symbol, quote):
    total_amount, total_cost, total_quantity, current_bid_price, break_even = evaluate_break_even_and_profit(symbol,
                                                                                                             quote)
    print("Coin:", symbol.ljust(7),
          "Amount:", str(total_amount).ljust(25),
          "Cost:", str(total_cost).ljust(25),
          "Quantity:", str(total_quantity).ljust(25),
          "Current Bid:", str(current_bid_price).ljust(25),
          "Break Even %:", str(break_even).ljust(25))


def sell_trade_logic_close_all(symbol, quote):
    if len(OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        total_amount, total_cost, total_quantity, current_bid_price, break_even = evaluate_break_even_and_profit(symbol,
                                                                                                                 quote)
        percentage_up = percentage_break_even(total_cost, current_bid_price)
        if VERBOSE:
            print("New Strategy Sell:", symbol, "Percentage Up", percentage_up)
        positions = r.get_crypto_positions()
        quantity = -1.0
        for position in positions:
            if position['currency']['code'] == symbol:
                quantity = float(position['quantity'])
                if VERBOSE:
                    print("Found symbol, quantity", quantity)

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
                print_break_even_and_profit_stats(symbol, current_quote)
                print()


def crypto_trading_logic(symbol, run_counter):
    try:

        # get the current quote for the crypto
        current_quote = r.get_crypto_quote(symbol)

        if run_counter % 1000 == 0:
            print_break_even_and_profit_stats(symbol, current_quote)

        # Run the buy algorithm
        buy_trade_logic(symbol, current_quote)

        # Run the sell algorithm
        if symbol in NEW_STRATEGY:
            sell_trade_logic_close_all(symbol, current_quote)
        else:
            sell_trade_logic(symbol, current_quote)

    except TypeError:
        return
    except exceptions.ReadTimeout:
        time.sleep(10)
        return
    except exceptions.ConnectionError:
        time.sleep(10)
        return


def login_to_robinhood(email, password):
    r.login(username=email, password=password, store_session=True, pickle_name="aarthika")


def print_state():
    print("State of outstanding lots for all coins")
    for c in CRYPTO_LIST:
        for lot in OUTSTANDING_TRADE_LOTS[c]:
            print("Coin:", c.ljust(7),
                  "Amount:", str(lot['amount']).ljust(25),
                  "Cost:", str(lot['cost']).ljust(25),
                  "Quantity:", str(lot['quantity']).ljust(25),
                  "Trade Id:", lot['id'],
                  "Order Placed:", lot['updated'])
        print()
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
    hours_ran = 0
    while True:
        for crypto in CRYPTO_LIST:
            # print("Initial: Running trading magic for", crypto)
            crypto_trading_logic(crypto, run_count)
        if run_count % 1000 == 0:
            print()
        time.sleep(1)
        run_count = run_count + 1
        if run_count % 3600 == 0:
            hours_ran = hours_ran + 1
            print("State: Hourly check Hours count:", hours_ran, " Run count:", run_count)
            print_state()
