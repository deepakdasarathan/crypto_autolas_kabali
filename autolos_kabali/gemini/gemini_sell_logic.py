# Gemini Trading bot
# Author: Deepak Dasarathan

import math
from pprint import pformat

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_helper import place_and_check_order_executed_or_cancel, remove_coin, get_quantity, \
    get_signals, create_trade_details, insert_recent_trade, get_sell_volatility_percentage_latest, \
    remove_recent_trade, get_min_quantity, get_quote_increment
from autolos_kabali.gemini.gemini_stats import print_state


def aggressive_bid(symbol, bid):
    if '.' in bid:
        exponent, mantissa = bid.split('.')
        quote_increment = get_quote_increment(symbol)
        mantissa_size = int(round(1/quote_increment))
        mantissa_max = mantissa_size - 1
        mantissa_len = len(str(mantissa_max))
        mantissa_int = int(mantissa)
        if mantissa_int > 0:
            if mantissa_int == mantissa_max:
                return str(int(exponent) + 1) + '.' + '0'.zfill(mantissa_len)
            aggressive_mantissa = int(float('0.' + mantissa) * mantissa_size) + 1
            return exponent + '.' + str(aggressive_mantissa).zfill(mantissa_len)
    return bid


def sell_logic_hybrid(symbol):
    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        signal = get_signals(symbol)
        # print("Sell:", symbol, "% up from total cost", signal.percentage_up,
        #       "% up from last trade", signal.percentage_up_from_last_trade,
        #       "% break even", signal.break_even)
        if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) <= 6:
            # print("Sell:", symbol, "Sell all")
            sell_trade_logic(symbol, signal)
        else:
            # print("Sell:", symbol, "Sell last")
            sell_trade_logic_last_lot(symbol, signal)


def sell_trade_logic_last_lot(symbol, signal):
    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        quantity = get_quantity(symbol)
        last_trade_quantity = float(signal.lowest_outstanding_lot['quantity'])

        if not GEMINI_DRY_RUN:

            sell_quantity = last_trade_quantity
            if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) == 1:
                sell_quantity = quantity
                if not math.isclose(last_trade_quantity, quantity):
                    print("Sell:", symbol, "Total Quantity:", last_trade_quantity, "Quantity in Gemini:", quantity)

            volatility_percentage = get_sell_volatility_percentage_latest(symbol)
            # print("Sell:", symbol, "% up from recent trace", signal.percentage_up_from_last_trade,
            #       "Volatility %", volatility_percentage)

            if signal.percentage_up_from_last_trade > volatility_percentage:
                sell_trade_impl(symbol,
                                sell_quantity,
                                signal.bid,
                                float(signal.lowest_outstanding_lot['cost']),
                                signal.lowest_outstanding_lot)


def sell_trade_logic(symbol, signal):
    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        quantity = get_quantity(symbol)

        if isinstance(quantity, float) and quantity > 0.0:

            if not GEMINI_DRY_RUN:

                volatility_percentage = get_sell_volatility_percentage_latest(symbol)

                if signal.percentage_up > volatility_percentage:
                    if not math.isclose(signal.total_quantity, quantity):
                        print("Sell:", symbol, "Total Quantity:", signal.total_quantity, "Quantity in Gemini:",
                              quantity)
                    sell_trade_impl(symbol,
                                    quantity,
                                    signal.bid,
                                    signal.avg_cost)
        else:
            if isinstance(quantity, float) and math.isclose(quantity, 0.0):
                print("Sell:", symbol, "Quantity not found. Cleanup coin lot")
                remove_coin(symbol)
                print_state(True)


def sell_trade_impl(symbol, quantity, bid, cost, lowest_outstanding_trade=None):
    aggressive_bid_f = aggressive_bid(symbol, bid)
    print("Sell:", symbol, "Current Bid Price:", bid, "Aggressive bid", aggressive_bid_f)
    sell_order = place_and_check_order_executed_or_cancel(symbol,
                                                          quantity,
                                                          "sell",
                                                          aggressive_bid_f)
    if sell_order is not None:
        executed_amount = float(sell_order['executed_amount'])
        if executed_amount > 0.0:
            if bool(lowest_outstanding_trade):
                remove_recent_trade(symbol, lowest_outstanding_trade)
            else:
                remove_coin(symbol)

            if not math.isclose(quantity, executed_amount):
                # partially executed
                min_quantity = get_min_quantity(symbol)
                remaining_quantity = float(sell_order['remaining_amount'])
                if remaining_quantity > min_quantity:
                    dollar_amount = remaining_quantity * cost
                    remaining_trade = create_trade_details(symbol,
                                                           sell_order['order_id'],
                                                           sell_order['client_order_id'],
                                                           remaining_quantity,
                                                           cost,
                                                           dollar_amount,
                                                           sell_order['timestamp'],
                                                           sell_order['timestampms'])
                    insert_recent_trade(symbol, remaining_trade)
        print_state(True)

        try:
            print("Sell:", symbol, "Sell Order", pformat(sell_order))
        except Exception as e:
            print("Sell: Caught exception when printing", e)
