# Gemini Trading bot
# Author: Deepak Dasarathan

import math
from pprint import pformat

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_helper import place_and_check_order_executed_or_cancel, remove_coin, get_quantity, \
    get_signals, create_trade_details, insert_recent_trade, get_volatility_percentage_latest
from autolos_kabali.gemini.gemini_stats import print_state


def aggresive_bid(bid):
    if '.' in bid:
        exponent, mantissa = bid.split('.')
        mantissa_int = int(mantissa)
        if mantissa_int > 0:
            mantissa_int = mantissa_int + 1
            return exponent + '.' + str(mantissa_int).zfill(len(mantissa))
    return bid


def sell_trade_logic(symbol):
    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        signal = get_signals(symbol)
        quantity = get_quantity(symbol)

        if isinstance(quantity, float) and quantity > 0.0:

            if not GEMINI_DRY_RUN:
                if not math.isclose(signal.total_quantity, quantity):
                    print("Sell:", symbol, "Total Quantity:", signal.total_quantity, "Quantity in Gemini:", quantity)

                volatility_percentage = get_volatility_percentage_latest(symbol)

                if signal.percentage_up > volatility_percentage:
                    sell_order = place_and_check_order_executed_or_cancel(symbol,
                                                                          quantity,
                                                                          "sell",
                                                                          aggresive_bid(signal.bid))

                    executed_amount = float(sell_order['executed_amount'])
                    if executed_amount > 0.0:
                        if math.isclose(quantity, executed_amount):
                            remove_coin(symbol)
                        else:
                            # partially executed
                            remove_coin(symbol)
                            remaining_amount = float(sell_order['remaining_amount'])
                            dollar_amount = remaining_amount * signal.avg_cost
                            remaining_trade = create_trade_details(symbol,
                                                                   sell_order['order_id'],
                                                                   sell_order['client_order_id'],
                                                                   remaining_amount,
                                                                   signal.avg_cost,
                                                                   dollar_amount,
                                                                   sell_order['timestamp'],
                                                                   sell_order['timestampms'])
                            insert_recent_trade(symbol, remaining_trade)
                    print_state(True)

                    try:
                        print("Sell:", symbol, "Percentage Up", signal.percentage_up)
                        print("Sell:", symbol, "Sell Order", pformat(sell_order))
                    except Exception as e:
                        print("Sell: Caught exception when printing", e)
        else:
            if isinstance(quantity, float) and math.isclose(quantity, 0.0):
                print("Sell:", symbol, "Quantity not found. Cleanup coin lot")
                remove_coin(symbol)
                print_state(True)
