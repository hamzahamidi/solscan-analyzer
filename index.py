from enum import Enum
import requests
from datetime import datetime, time
from dotenv import load_dotenv
import os

# load environment variables from .env file
load_dotenv(dotenv_path="keys.env")

# credentials/configuration from environment variables
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
TOP_N = os.getenv("TOP_N")

if not SOLSCAN_API_KEY:
    raise ValueError(
        "SOLSCAN_API_KEY is not set. Please define it in keys.env.")
if not TOP_N:
    TOP_N = 10

class ValidTopN(Enum):
    TEN = 10
    TWENTY = 20
    THIRTY = 30
    FORTY = 40


def validate_top_n(top_n: int):
    if top_n not in [item.value for item in ValidTopN]:
        raise ValueError(f"Invalid topN value: {top_n}. Allowed values are {
                         [item.value for item in ValidTopN]}.")


class SolanaTokenAnalyzer:
    def __init__(self, token_address: str, top_n: int = 10):
        self.token_address = token_address
        self.top_n = top_n
        self.api_url = "https://pro-api.solscan.io/v2.0"
        self.headers = {"accept": "application/json", "token": SOLSCAN_API_KEY}

    def get_top_holders(self):
        url = f"{self.api_url}/token/holders"
        params = {"address": self.token_address, "page_size": self.top_n}
        
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()["data"]

    def get_first_activity_date(self, wallet_address: str):
        url = f"{self.api_url}/account/balance_change"
        params = {"address": wallet_address, "token": self.token_address,
                  "sort_by": "block_time", "sort_order": "asc", "remove_spam": "true"}
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        data = response.json()["data"]
        return data[0]["time"]

    def get_transactions(self, wallet_address: str):
        transactions = []
        url = f"{self.api_url}/account/balance_change"
        params = {
            "address": wallet_address,
            "token": self.token_address,
            "sort_by": "block_time",
            "sort_order": "desc",
            "remove_spam": "true",
            "page_size": 40,
            "page": 1
        }

        while True:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()

            data = response.json()["data"]

            if len(data) < 40:
                new_transactions = [
                    {
                        "tx_hash": tx["tx_hash"],
                        "fee": tx["fee"],
                        "amount": tx["amount"],
                        "time": tx["time"],
                        "change_type": tx["change_type"]
                    }
                    for tx in data
                ]
                transactions.extend(new_transactions)
                params["page"] += 1
                time.sleep(0.05)
            else:
                break

        return transactions

    def analyze_holder(self, transactions: list):
        number_of_transactions = len(transactions)
        number_of_in_transactions = len(
            [tx for tx in transactions if tx["change_type"] == "inc"])
        number_of_out_transactions = number_of_transactions - number_of_in_transactions

        type_of_holder = "Long-term holder" if number_of_out_transactions // number_of_transactions < 0.1 else "Frequent flipper"

        return {
            "number_of_transactions": number_of_transactions,
            "number_of_in_transactions": number_of_in_transactions,
            "number_of_out_transactions": number_of_out_transactions,
            "type_of_holder": type_of_holder
        }

    def get_token_details(self, token_address: str):
        url = f"{self.api_url}/token/meta"
        params = {"address": token_address}
        response = requests.get(url, params=params, headers=self.headers)

        response.raise_for_status()
        data = response.json()["data"]

        return {
            "name": data["name"],
            "symbol": data["symbol"],
            "icon": data["icon"],
            "address": data["address"],
            "price": data["price"],
            "decimals": data["decimals"],
            "total_supply": data["total_supply"]
        }

    def get_other_tokens(self, wallet_address: str):
        url = f"{self.api_url}/account/token-accounts"
        params = {"address": wallet_address, "type": "token",
                  "page_size": 40, "hide_zero": True}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()

        data = response.json()["data"]
        tokens = []
        for item in data:
            token_details = self.get_token_details(item["token_address"])

            tokens.append({
                "amount": item["amount"],
                "token_decimals": item["token_decimals"],
                **token_details
            })

        return tokens

    def analyze(self):
        top_holders = self.get_top_holders()

        analysis_results = []

        for holder in top_holders:
            wallet_address = holder["address"]
            transactions = self.get_transactions(wallet_address)
            holder = self.analyze_holder(transactions)
            other_tokens = self.get_other_tokens(wallet_address)
            analysis_results.append({
                "wallet_address": wallet_address,
                "token_balance": holder["amount"],
                "rank": holder["rank"],
                "first_activity_date": self.get_first_activity_date(wallet_address),
                "other_tokens": other_tokens,
                "holder": holder,
                "transactions": transactions
            })

        return analysis_results


def main(request):
    validate_top_n(TOP_N)

    analyzer = SolanaTokenAnalyzer(
        token_address=request["tokenAddress"], top_n=TOP_N)
    results = analyzer.analyze()

    return results


if __name__ == "__main__":
    request = {
        "tokenAddress": "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump",
        "topN": 10
    }

    validate_top_n(request["topN"])

    analyzer = SolanaTokenAnalyzer(
        token_address=request["tokenAddress"], top_n=request["topN"])
    results = analyzer.analyze()

    print(results)
