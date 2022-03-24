# Gemini Trading bot
# Author: Deepak Dasarathan

import os
import pickle
from collections import defaultdict

from prettytable import PrettyTable

# GEMINI #

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_SECRET_KEY = os.environ.get('GEMINI_SECRET_KEY')
GEMINI_DRY_RUN = False
GEMINI_VERBOSE = False
GEMINI_MAX_RETRIES = 100
GEMINI_NO_OF_OUTSTANDING_TRADES = 20
GEMINI_CRYPTO_LIST = ["btcusd",
                      "ethusd",
                      "bchusd",
                      "ltcusd",
                      "lunausd",
                      "solusd",
                      "axsusd",
                      "linkusd",
                      "uniusd",
                      "sushiusd",
                      "sandusd",
                      "manausd",
                      "ftmusd",
                      "maticusd",
                      "batusd",
                      "grtusd",
                      "dogeusd",
                      "shibusd"]

GEMINI_OUTSTANDING_TRADE_LOTS_FILE = "outstanding_lots_gemini"

if os.path.exists(GEMINI_OUTSTANDING_TRADE_LOTS_FILE):
    GEMINI_OUTSTANDING_TRADE_LOTS = pickle.load(open(GEMINI_OUTSTANDING_TRADE_LOTS_FILE, 'rb'))
else:
    GEMINI_OUTSTANDING_TRADE_LOTS = defaultdict(list)

GEMINI_PERCENTAGES = [1.0,
                      1.0,
                      1.5,
                      1.5,
                      2.0,
                      2.0,
                      2.5,
                      2.5,
                      2.5,
                      5.0]

GEMINI_SELL_PERCENTAGES = [3.0,
                           3.0,
                           3.5,
                           3.5,
                           4.0,
                           5.0,
                           4.0,
                           4.5,
                           4.5,
                           5.0]

GEMINI_PURCHASE_AMOUNTS = [5.0,
                           10.0,
                           15.0,
                           20.0,
                           40.0,
                           80.0,
                           80.0,
                           100.0,
                           150.0,
                           200.0]

GEMINI_LOT_STATS = PrettyTable()
GEMINI_LOT_STATS.field_names = ["Coin",
                                "Amount",
                                "Cost",
                                "Quantity",
                                "Trade Id",
                                "Created"]

GEMINI_QUOTE_STATS = PrettyTable()
GEMINI_QUOTE_STATS.field_names = ["Coin",
                                  "Bid",
                                  "Ask",
                                  "Spread",
                                  "High",
                                  "Low",
                                  "Open",
                                  "Close"]

GEMINI_BREAK_EVEN_AND_PROFIT_STATS = PrettyTable()
GEMINI_BREAK_EVEN_AND_PROFIT_STATS.field_names = ["Coin",
                                                  "Amount",
                                                  "Quantity",
                                                  "Cost",
                                                  "Cost RT",
                                                  "Bid",
                                                  "Sell @",
                                                  "Sell @ RT",
                                                  "Ask",
                                                  "Buy @",
                                                  "% Break Even"]
