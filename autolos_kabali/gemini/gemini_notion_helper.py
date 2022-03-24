# Robinhood Trading bot
# Author: Deepak Dasarathan

import os.path
from notion_client import Client

NOTION_PAGES = {
    "btcusd": "32783907e23341229029c599218580c8",
    "ethusd": "7b171b46c9f141f1858daad87329cb71",
    "bchusd": "994df06d728f44beb76342924c52fc55",
    "ltcusd": "2787932a3d5149778c93e8e7fcd60514",
    "lunausd": "796825d989ed428e8a357d46a5896266",
    "solusd": "5ac723387e42450ea84de15918ada47a",
    "axsusd": "575b93b95e4748a0bfda0915fff78c7b",
    "linkusd": "18620674ddbc434182b4a4dd6b2d6cb8",
    "uniusd": "de9bb186dc354906a9e51359ab3622b8",
    "sushiusd": "9255b3b7c91447df88f9c7169da435fe",
    "sandusd": "d2ff295f4e654f348911371576de7ff7",
    "manausd": "0e926445adc14bf2be6fcbc23e640395",
    "ftmusd": "e03cc8634d1942b1a73de3771e7673de",
    "maticusd": "d39dafbd61df4b94b965ff53554e2b77",
    "batusd": "269e2c4a0a6a435d80958645e773cdd8",
    "grtusd": "a7e7c32e757244f5af2f2c3ca2717b5c",
    "dogeusd": "51e23ee3d70348e1bd3e3d8a49a8bef0",
    "shibusd": "a619635f2dbf49b8bf6d0b6b3e3dea12"
}

_notion_api = os.environ.get('NOTION_API_KEY')
NOTION = Client(auth=_notion_api)


def update_notion_stats(symbol,
                        total_amount,
                        total_equity,
                        returns,
                        total_quantity,
                        avg_cost,
                        sell_at,
                        bid,
                        cost_rt,
                        sell_at_rt,
                        ask,
                        buy_at,
                        break_even):
    page_id = NOTION_PAGES[symbol]
    data = {
            "Total $$": {"number": total_amount},
            "Total Equity": {"number": total_equity},
            "Returns": {"number": returns},
            "Total Quantity": {"number": total_quantity},
            "Avg. Cost": {"number": avg_cost},
            "Sell @": {"number": sell_at},
            "Bid": {"number": bid},
            "Cost RT": {"number": cost_rt},
            "Sell @RT": {"number": sell_at_rt},
            "Ask": {"number": ask},
            "Buy @": {"number": buy_at},
            "Break Even": {"number": break_even}
        }
    NOTION.pages.update(page_id, properties=data)


if __name__ == '__main__':

    cost = 0.0

    for crypto in NOTION_PAGES:
        print(crypto)
        # pprint(notion.pages.retrieve(NOTION_PAGES[crypto]))
        cost = round(cost + 0.1, 2)
        # cost = '{:.9f}'.format(cost).rstrip('0').rstrip('.')
        update_notion_stats(crypto, cost, cost, cost, cost, cost, cost, cost, cost, cost, cost, cost, cost)
