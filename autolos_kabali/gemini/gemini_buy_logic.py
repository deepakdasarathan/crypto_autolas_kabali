# Gemini Trading bot
# Author: Deepak Dasarathan

from pprint import pformat

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_helper import insert_recent_trade, place_and_check_order_executed_or_cancel, \
    create_trade_details, get_signals, get_account_balance, evaluate_exponential_trading_closeness_values
from autolos_kabali.gemini.gemini_stats import print_state


def gemini_round(price):
    price = float(price)
    if price <= 1e-2:
        return_price = round(price, 6)
    elif price < 1e0:
        return_price = round(price, 4)
    else:
        return_price = round(price, 2)

    return return_price


def aggresive_ask(ask):
    if '.' in ask:
        exponent, mantissa = ask.split('.')
        mantissa_int = int(mantissa)
        if mantissa_int > 0:
            mantissa_int = mantissa_int - 1
            return exponent + '.' + str(mantissa_int).zfill(len(mantissa))
    return ask


def buy_trade_logic(symbol):
    trading_amount_dollars, closeness_percentage = evaluate_exponential_trading_closeness_values(symbol)
    signal = get_signals(symbol)

    if not GEMINI_DRY_RUN:
        buy = False

        if signal.percentage_dip > closeness_percentage and not signal.lowest_outstanding_lot:
            buy = True

        if (bool(signal.lowest_outstanding_lot) and
                signal.closeness_to_lowest_trade > closeness_percentage and
                len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) < GEMINI_NO_OF_OUTSTANDING_TRADES):
            buy = True

        if buy:
            available_balance = get_account_balance()
            if trading_amount_dollars > available_balance:
                print("Buy:", symbol, "Insufficient funds, Available Balance:", available_balance,
                      "Trading Amount:", trading_amount_dollars, "Current Ask Price:", signal.ask)
                return

            order_quantity = trading_amount_dollars / float(signal.ask)
            buy_order = place_and_check_order_executed_or_cancel(symbol,
                                                                 gemini_round(order_quantity),
                                                                 "buy",
                                                                 aggresive_ask(signal.ask))

            executed_amount = float(buy_order['executed_amount'])
            if executed_amount > 0.0:
                avg_execution_price = float(buy_order['avg_execution_price'])
                dollar_amount = executed_amount * avg_execution_price
                placed_buy_trade = create_trade_details(symbol,
                                                        buy_order['order_id'],
                                                        buy_order['client_order_id'],
                                                        executed_amount,
                                                        avg_execution_price,
                                                        dollar_amount,
                                                        buy_order['timestamp'],
                                                        buy_order['timestampms'])
                insert_recent_trade(symbol, placed_buy_trade)
            print_state(True)

            try:
                if bool(signal.lowest_outstanding_lot):
                    print("Buy:", symbol, "Lowest lot", signal.lowest_outstanding_lot)
                    print("Buy:", symbol, "Closeness to lowest trade", signal.closeness_to_lowest_trade)
                print("Buy:", symbol, "Trading Amount:", trading_amount_dollars, "Closeness:", closeness_percentage)
                print("Buy:", symbol, "Order placed", pformat(buy_order))
            except Exception as e:
                print("Buy:", symbol, "Caught exception when printing", e)
