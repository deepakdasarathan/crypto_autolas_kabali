# Robinhood Trading bot
# Author: Deepak Dasarathan

import os.path
import pickle
import sys
import time
from collections import defaultdict

from robin_stocks import robinhood as r

MAX_RETRIES = 1000
TRADE_LIMIT_PRICE = 5.0
VOLATILITY_PERCENTAGE = 5
CLOSENESS_PERCENTAGE = 3
HIGH_HISTORICAL_WINDOW = 24
NO_OF_OUTSTANDING_TRADES = 10
CRYPTO_LIST = ["BCH", "BSV", "BTC", "DOGE", "ETH", "ETC", "LTC"]
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


def crypto_trading_logic(symbol):
    # Get the high price in window

    historical_quotes = r.get_crypto_historicals(symbol=symbol)
    high_price = float(-1.0)
    for historical in historical_quotes[-HIGH_HISTORICAL_WINDOW:]:
        if float(historical['high_price']) > high_price:
            high_price = float(historical['high_price'])

    # per crypto find the allocated trade quantity
    trading_amount_dollars = TRADE_LIMIT_PRICE

    # get the current quote for the crypto
    current_quote = r.get_crypto_quote(symbol)

    # print("Initial:", symbol, "High price in window", high_price)
    # print("Initial:", symbol, "Current quote", current_quote)

    # if current ask_price is < x% of the high in window and outstanding lots.lowest_price > current ask_price
    # and if outstanding orders cost is < 70% of allocated budget
    current_ask_price = float(current_quote['ask_price'])
    percentage_dip = ((high_price - current_ask_price) / high_price) * 100
    # print("Buy:", symbol, "Percentage Dip", percentage_dip)

    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
    closeness_to_lowest_trade = 0.0
    if bool(lowest_outstanding_lot):
        closeness_to_lowest_trade = ((float(
            lowest_outstanding_lot['cost']) - current_ask_price) / float(
            lowest_outstanding_lot['cost'])) * 100
    if (percentage_dip > CLOSENESS_PERCENTAGE and
            (not lowest_outstanding_lot or
             (float(lowest_outstanding_lot['cost']) > current_ask_price and
              closeness_to_lowest_trade > CLOSENESS_PERCENTAGE)) and
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
        print("Buy:", symbol, "order placed", placed_buy_order)
        filled = False
        canceled = False
        filled_buy_order = {}
        retries = 0
        while not filled and not canceled:
            filled_buy_order = r.get_crypto_order_info(placed_buy_order['id'])
            if filled_buy_order['state'] == "filled":
                filled = True
            time.sleep(0.1)
            retries = retries + 1
            # retry for a few minutes and then cancel order
            if retries % MAX_RETRIES == 0:
                print("Buy:", symbol, "Current quote", r.get_crypto_quote(symbol))
                canceled_buy_order = r.cancel_crypto_order(placed_buy_order['id'])
                print("Buy:", symbol, "100s passed and the limit buy order still did not execute. Canceling!",
                      canceled_buy_order)
                canceled = True

            # ensure cancel went through
        if not canceled:
            placed_buy_trade = create_trade_details(symbol, filled_buy_order['id'],
                                                    filled_buy_order['cumulative_quantity'],
                                                    filled_buy_order['average_price'],
                                                    filled_buy_order['entered_price'],
                                                    filled_buy_order['created_at'],
                                                    filled_buy_order['updated_at'])
            insert_recent_trade(symbol, placed_buy_trade)

    # if current bid_price > lots.lowest_price by x%
    current_bid_price = float(current_quote['bid_price'])
    lowest_outstanding_lot = get_lowest_outstanding_trade(symbol)
    percentage_up = 0.0
    if bool(lowest_outstanding_lot):
        percentage_up = ((current_bid_price - float(
            lowest_outstanding_lot['cost'])) / current_bid_price) * 100
    if (bool(lowest_outstanding_lot) and
            percentage_up > VOLATILITY_PERCENTAGE):
        #   then place a sell order at bid_price
        placed_sell_order = r.order_sell_crypto_limit(symbol, float(lowest_outstanding_lot['quantity']),
                                                      r.helper.round_price(current_bid_price))
        print("Sell:", symbol, "Lowest lot", lowest_outstanding_lot)
        if bool(lowest_outstanding_lot):
            print("Sell:", symbol, "Percentage Up", percentage_up)
        print("Sell:", symbol, "order placed", placed_sell_order)

        filled = False
        canceled = False
        retries = 0
        while not filled and not canceled:
            filled_sell_order = r.get_crypto_order_info(placed_sell_order['id'])
            if filled_sell_order['state'] == "filled":
                filled = True
            time.sleep(0.1)
            retries = retries + 1
            # retry for a few minutes and then cancel order
            if retries % MAX_RETRIES == 0:
                print("Sell:", symbol, "Current quote", r.get_crypto_quote(symbol))
                canceled_sell_order = r.cancel_crypto_order(placed_sell_order['id'])
                print("Sell:", symbol, "100s passed and the limit sell order still did not execute. Canceling!",
                      canceled_sell_order)
                canceled = True

            # ensure cancel went through
        if not canceled:
            remove_matched_trade(symbol, lowest_outstanding_lot)


def find_trading_quantity():
    # Get the total cash balance for the account
    # Get total crypto outstanding orders cost for the account
    # the ratio of the above balances should be 1:1 approximately
    # the ratio of all the outstanding crypto cost should be 1
    # this determines the total budget for each crypto
    return False


def login_to_robinhood(email, password):
    r.login(username=email, password=password, store_session=True)


def print_state():
    for c in CRYPTO_LIST:
        print("Initial state: Outstanding trades for", c, "is", str(len(OUTSTANDING_TRADE_LOTS[c])))
        for lot in OUTSTANDING_TRADE_LOTS[c]:
            print("Initial state:", lot)


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
            crypto_trading_logic(crypto)
        time.sleep(1)
        run_count = run_count + 1
        if run_count % 3600 == 0:
            hours_ran = hours_ran + 1
            print("State: Hourly check Hours count:", hours_ran, " Run count:", run_count)
            print_state()
