# Robinhood Trading bot
# Author: Deepak Dasarathan

import os.path
from notion_client import Client

NOTION_PAGES = {
    "BCH": "0729e4f71ccf41a0b768b7e8d2e2b03c",
    "BSV": "938cd1663769480ea9cd4645d53c31b3",
    "BTC": "1314410100504fed907f4017825377b6",
    "DOGE": "57b37c93149345c2bfe862ca421a7985",
    "ETC": "2df5854b88bd45f0baf6a75d109cb420",
    "ETH": "cf914990a667430b88870aca7df1c042",
    "LTC": "900434c39f324626941568022b38dc1b"
}

_notion_api = os.environ.get('NOTION_API_KEY')
NOTION = Client(auth=_notion_api)


def update_notion_stats(symbol, total_amount, total_quantity, avg_cost, high, ask, bid, sell_at, buy_at):
    page_id = NOTION_PAGES[symbol]
    data = {
            "Total $$": {"number": total_amount},
            "Total Quantity": {"number": total_quantity},
            "Avg. Cost": {"number": avg_cost},
            "High": {"number": high},
            "Ask": {"number": ask},
            "Bid": {"number": bid},
            "Sell @": {"number": sell_at},
            "Buy @": {"number": buy_at}
        }
    NOTION.pages.update(page_id, properties=data)


if __name__ == '__main__':

    for crypto in NOTION_PAGES:
        print(crypto)
        # pprint(notion.pages.retrieve(NOTION_PAGES[crypto]))
        update_notion_stats(crypto, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1, 1.1)
