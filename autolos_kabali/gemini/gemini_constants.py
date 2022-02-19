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
GEMINI_NO_OF_OUTSTANDING_TRADES = 6
GEMINI_CRYPTO_LIST = ["axsusd",
                      "shibusd",
                      "uniusd",
                      "linkusd",
                      "maticusd",
                      "ftmusd",
                      "grtusd",
                      "sushiusd",
                      "batusd",
                      "manausd"]

GEMINI_OUTSTANDING_TRADE_LOTS_FILE = "outstanding_lots_gemini"

if os.path.exists(GEMINI_OUTSTANDING_TRADE_LOTS_FILE):
    GEMINI_OUTSTANDING_TRADE_LOTS = pickle.load(open(GEMINI_OUTSTANDING_TRADE_LOTS_FILE, 'rb'))
else:
    GEMINI_OUTSTANDING_TRADE_LOTS = defaultdict(list)

GEMINI_PERCENTAGES = [0.9,
                      1.17,
                      1.521,
                      1.9773,
                      2.57049,
                      3.341637,
                      4.3441281]
GEMINI_PURCHASE_AMOUNTS = [0.5,
                           1.0,
                           2.0,
                           4.0,
                           8.0,
                           16.0,
                           32.0]

GEMINI_LOT_STATS = PrettyTable()
GEMINI_LOT_STATS.field_names = ["Coin",
                                "Amount",
                                "Cost",
                                "Quantity",
                                "Trade Id",
                                "Created"]

GEMINI_QUOTE_STATS = PrettyTable()
GEMINI_QUOTE_STATS.field_names = ["Coin",
                                  "Ask",
                                  "Bid",
                                  "High",
                                  "Low",
                                  "Open",
                                  "Close"]

GEMINI_BREAK_EVEN_AND_PROFIT_STATS = PrettyTable()
GEMINI_BREAK_EVEN_AND_PROFIT_STATS.field_names = ["Coin",
                                                  "Amount",
                                                  "Quantity",
                                                  "Cost",
                                                  "Bid",
                                                  "Sell @",
                                                  "Ask",
                                                  "Buy @",
                                                  "% Break Even"]
