# Gemini Trading bot
# Author: Deepak Dasarathan

import time
import traceback

from robin_stocks import gemini as g

from autolos_kabali.gemini.gemini_buy_logic import buy_trade_logic
from autolos_kabali.gemini.gemini_constants import *
from autolos_kabali.gemini.gemini_sell_logic import sell_logic_hybrid
from autolos_kabali.gemini.gemini_stats import print_state


def crypto_trading_logic(symbol):
    try:
        # Run the buy algorithm
        buy_trade_logic(symbol)

        # Run the sell algorithm
        sell_logic_hybrid(symbol)

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        time.sleep(10)
        return


def login_to_gemini(api_key, secret_key):
    g.login(api_key, secret_key)


if __name__ == '__main__':

    login_to_gemini(GEMINI_API_KEY, GEMINI_SECRET_KEY)

    run_count = 0

    while True:
        for crypto in GEMINI_CRYPTO_LIST:
            crypto_trading_logic(crypto)
        if run_count % 10 == 0:
            print("Run count:", run_count)
            print_state()
        run_count = run_count + 1
