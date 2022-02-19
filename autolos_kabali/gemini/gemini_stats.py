# Gemini Trading bot
# Author: Deepak Dasarathan
import math
import time
import traceback

from termcolor import colored

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_helper import get_signals, get_account_balance


def print_signals(signal):
    precision = 9 if signal.symbol == "shibusd" else 4
    format_string = '{:.' + str(precision) + 'f}'
    GEMINI_QUOTE_STATS.add_row([signal.symbol,
                                signal.ask,
                                signal.bid,
                                format_string.format(round(signal.high, precision)),
                                format_string.format(round(signal.low, precision)),
                                format_string.format(round(signal.open, precision)),
                                format_string.format(round(signal.close, precision))])


def print_break_even_and_profit_stats(signal):
    precision = 9 if signal.symbol == "shibusd" else 4
    format_string = '{:.' + str(precision) + 'f}'
    sell_at_formatted = format_string.format(round(signal.sell_at, precision))
    if float(signal.bid) > signal.avg_cost and not math.isclose(signal.avg_cost, 0.0):
        sell_at_formatted = colored(str(sell_at_formatted), 'white', 'on_green')
    buy_at_formatted = format_string.format(round(signal.buy_at, precision))
    if float(signal.ask) < signal.buy_at:
        buy_at_formatted = colored(str(buy_at_formatted), 'white', 'on_red')
    GEMINI_BREAK_EVEN_AND_PROFIT_STATS.add_row([signal.symbol,
                                                format_string.format(round(signal.total_amount, precision)),
                                                format_string.format(round(signal.total_quantity, precision)),
                                                format_string.format(round(signal.avg_cost, precision)),
                                                signal.bid,
                                                sell_at_formatted,
                                                signal.ask,
                                                buy_at_formatted,
                                                format_string.format(signal.break_even)])


def print_lot_details(symbol):
    total_crypto_bought_dollars = 0.0
    for lot in GEMINI_OUTSTANDING_TRADE_LOTS[symbol]:
        GEMINI_LOT_STATS.add_row([symbol,
                                  round(lot['amount'], 9),
                                  round(lot['cost'], 9),
                                  round(lot['quantity'], 9),
                                  lot['order_id'],
                                  lot['created']])

        total_crypto_bought_dollars = total_crypto_bought_dollars + lot['amount']

    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        GEMINI_LOT_STATS.add_row(['*'*10, '*'*10, '*'*10, '*'*10, '*'*20, '*'*20])
    return total_crypto_bought_dollars


def print_state(print_stdout=True):
    try:
        total_crypto_bought_dollars = 0.0
        for c in GEMINI_CRYPTO_LIST:
            signal = get_signals(c)

            print_signals(signal)
            print_break_even_and_profit_stats(signal)
            total_crypto_bought_dollars = total_crypto_bought_dollars + print_lot_details(c)

        cash_balance = get_account_balance()
        total_equity = total_crypto_bought_dollars + cash_balance
        if print_stdout:
            print(GEMINI_LOT_STATS.get_string())
            print()
            print("Total $$s spent to buy crypto:", round(total_crypto_bought_dollars, 2),
                  "Available Cash $$:", round(cash_balance, 2),
                  "Total equity $$s:", round(total_equity, 2))
            print()
            print(GEMINI_BREAK_EVEN_AND_PROFIT_STATS.get_string())
            print(GEMINI_QUOTE_STATS.get_string())
        GEMINI_LOT_STATS.clear_rows()
        GEMINI_BREAK_EVEN_AND_PROFIT_STATS.clear_rows()
        GEMINI_QUOTE_STATS.clear_rows()
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        time.sleep(10)
        return
    if print_stdout:
        print()
