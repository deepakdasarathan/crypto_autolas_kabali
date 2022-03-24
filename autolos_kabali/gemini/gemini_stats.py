# Gemini Trading bot
# Author: Deepak Dasarathan
import math
import time
import traceback
from datetime import datetime
from termcolor import colored

from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_helper import get_signals, get_account_balance
from autolos_kabali.gemini.gemini_notion_helper import update_notion_stats


def print_signals(signal):
    precision = 9 if signal.symbol == "shibusd" else 5
    format_string = '{:.' + str(precision) + 'f}'
    GEMINI_QUOTE_STATS.add_row([signal.symbol,
                                signal.bid,
                                signal.ask,
                                '{:.9f}'.format(float(signal.ask) - float(signal.bid)).rstrip('0').rstrip('.'),
                                format_string.format(signal.high).rstrip('0').rstrip('.'),
                                format_string.format(signal.low).rstrip('0').rstrip('.'),
                                format_string.format(signal.open).rstrip('0').rstrip('.'),
                                format_string.format(signal.close).rstrip('0').rstrip('.')])


def print_break_even_and_profit_stats(signal):
    precision = 9 if signal.symbol == "shibusd" else 5
    format_string = '{:.' + str(precision) + 'f}'

    quantity_format_precision = 9 if signal.symbol == "btcusd" else 5
    quantity_format_string = '{:.' + str(quantity_format_precision) + 'f}'

    sell_at_formatted = format_string.format(signal.sell_at).rstrip('0').rstrip('.')
    if float(signal.bid) > signal.avg_cost and not math.isclose(signal.avg_cost, 0.0):
        sell_at_formatted = colored(str(sell_at_formatted), 'white', 'on_green')

    sell_at_recent_formatted = format_string.format(signal.sell_at_recent_trade).rstrip('0').rstrip('.')
    recent_cost = 0.0
    if bool(signal.lowest_outstanding_lot):
        recent_cost = float(signal.lowest_outstanding_lot['cost'])
        if float(signal.bid) > recent_cost and \
                not math.isclose(recent_cost, 0.0):
            sell_at_recent_formatted = colored(str(sell_at_recent_formatted), 'white', 'on_green')

    buy_at_formatted = format_string.format(signal.buy_at).rstrip('0').rstrip('.')
    if float(signal.ask) < recent_cost or (math.isclose(recent_cost, 0.0) and float(signal.ask) < signal.high):
        buy_at_formatted = colored(str(buy_at_formatted), 'white', 'on_red')

    GEMINI_BREAK_EVEN_AND_PROFIT_STATS.add_row([signal.symbol,
                                                format_string.format(signal.total_amount).rstrip('0').rstrip('.'),
                                                quantity_format_string.format(signal.total_quantity).rstrip('0').rstrip('.'),
                                                format_string.format(signal.avg_cost).rstrip('0').rstrip('.'),
                                                format_string.format(recent_cost).rstrip('0').rstrip('.'),
                                                signal.bid,
                                                sell_at_formatted,
                                                sell_at_recent_formatted,
                                                signal.ask,
                                                buy_at_formatted,
                                                '{:.9f}'.format(signal.break_even).rstrip('0').rstrip('.')])

    total_equity = signal.total_quantity * (float(signal.ask) + float(signal.bid)) / 2
    returns = total_equity - signal.total_amount
    notion_precision = 9 if signal.symbol == "shibusd" else 4
    update_notion_stats(signal.symbol,
                        round(signal.total_amount, 2),
                        round(total_equity, 2),
                        round(returns, 2),
                        round(signal.total_quantity, 9 if signal.symbol == "btcusd" else 3),
                        round(signal.avg_cost, notion_precision),
                        round(signal.sell_at, notion_precision),
                        round(float(signal.bid), notion_precision),
                        round(recent_cost, notion_precision),
                        round(signal.sell_at_recent_trade, notion_precision),
                        round(float(signal.ask), notion_precision),
                        round(signal.buy_at, notion_precision),
                        round(signal.break_even, 2)
                        )


def print_lot_details(symbol):
    total_crypto_bought_dollars = 0.0
    format_string = '{:.9f}' if symbol == "shibusd" else '{:.4f}'

    quantity_format_precision = 9 if symbol == "btcusd" else 5
    quantity_format_string = '{:.' + str(quantity_format_precision) + 'f}'

    for lot in GEMINI_OUTSTANDING_TRADE_LOTS[symbol]:
        iso_date_timestamp = datetime.fromtimestamp(float(lot['created']))
        GEMINI_LOT_STATS.add_row([symbol,
                                  round(lot['amount'], 5),
                                  format_string.format(round(lot['cost'], 9)).rstrip('0').rstrip('.'),
                                  quantity_format_string.format(lot['quantity']).rstrip('0').rstrip('.'),
                                  lot['order_id'],
                                  iso_date_timestamp])

        total_crypto_bought_dollars = total_crypto_bought_dollars + lot['amount']

    if len(GEMINI_OUTSTANDING_TRADE_LOTS[symbol]) > 0:
        GEMINI_LOT_STATS.add_row(['*'*10, '*'*13, '*'*13, '*'*13, '*'*15, '*'*23])
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
