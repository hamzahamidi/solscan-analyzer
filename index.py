from datetime import datetime
from enum import Enum
import requests
from openai import OpenAI
import time
from dotenv import load_dotenv
import os

# load environment variables from .env file
load_dotenv(dotenv_path="keys.env")

# credentials/configuration from environment variables
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TOP_N = os.getenv("TOP_N")

if not SOLSCAN_API_KEY:
    raise ValueError(
        "SOLSCAN_API_KEY is not set. Please define it in keys.env.")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY is not set. Please define it in keys.env.")
if TOP_N:
    TOP_N = int(TOP_N)
else:
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


def validate_token_address(token_address: str):
    if not token_address:
        raise ValueError("tokenAddress is required.")
    if not isinstance(token_address, str):
        raise ValueError("tokenAddress must be a string.")
    if len(token_address) != 44:
        raise ValueError("tokenAddress must be 44 characters long.")


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
        return response.json()["data"]["items"]

    def get_first_activity_date(self, wallet_address: str):
        url = f"{self.api_url}/account/balance_change"
        params = {"address": wallet_address, "token": self.token_address,
                  "sort_by": "block_time", "sort_order": "asc", "remove_spam": "true"}
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        data = response.json()["data"]
        return None if len(data) == 0 else data[0]["time"]

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
            new_transactions = [
                {
                    "trans_id": tx.get("trans_id"),
                    "fee": tx.get("fee"),
                    "amount": tx.get("amount"),
                    "time": tx.get("time"),
                    "change_type": tx.get("change_type")
                }
                for tx in data
            ]
            transactions.extend(new_transactions)

            if len(data) < 40 or len(transactions) >= 100:
                break

            params["page"] += 1
            time.sleep(0.05)

        return transactions

    def determine_holder_type(number_of_transactions, number_of_out_transactions):
        if number_of_transactions == 0 or number_of_out_transactions / number_of_transactions < 0.1:
            return "Long-term holder"
        return "Frequent flipper"

    def analyze_holder(self, transactions: list):
        number_of_transactions = len(transactions)
        number_of_in_transactions = sum(
            1 for tx in transactions if tx["change_type"] == "inc")
        number_of_out_transactions = number_of_transactions - number_of_in_transactions

        type_of_holder = SolanaTokenAnalyzer.determine_holder_type(
            number_of_transactions, number_of_out_transactions)

        def format_count(count):
            return "more than 100" if count >= 100 else count

        return {
            "number_of_transactions": format_count(number_of_transactions),
            "number_of_in_transactions": format_count(number_of_in_transactions),
            "number_of_out_transactions": format_count(number_of_out_transactions),
            "type_of_holder": type_of_holder
        }

    def get_token_details(self, token_address: str):
        url = f"{self.api_url}/token/meta"
        params = {"address": token_address}
        response = requests.get(url, params=params, headers=self.headers)

        response.raise_for_status()
        data = response.json()["data"]

        return {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "icon": data.get("icon"),
            "address": data.get("address"),
            "price": data.get("price"),
            "decimals": data.get("decimals"),
            "supply": data.get("supply")
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
        token = self.get_token_details(self.token_address)
        analysis = []

        for holder in top_holders:
            wallet_address = holder["address"]
            transactions = self.get_transactions(wallet_address)
            holder_details = self.analyze_holder(transactions)
            other_tokens = self.get_other_tokens(wallet_address)
            analysis.append({
                "wallet_address": wallet_address,
                "token_balance": holder.get("amount"),
                "rank": holder["rank"],
                "first_activity_date": self.get_first_activity_date(wallet_address),
                "other_tokens": other_tokens,
                "holder_details": holder_details,
                "transactions": transactions
            })

        return {
            "token": token,
            "analysis": analysis,
            "date": datetime.now().isoformat()
        }


def summarize_results(results):
    # ignore transactions because they are not needed for summarization
    token = results.get("token")
    analysis = [
        {
            "wallet_address": result.get("wallet_address"),
            "token_balance": result.get("token_balance"),
            "rank": result.get("rank"),
            "first_activity_date": result.get("first_activity_date"),
            "other_tokens": result.get("other_tokens"),
            "holder_details": result.get("holder_details")
        }
        for result in results.get("analysis")
    ]
    date = results.get("date")

    client = OpenAI(
        api_key=OPENAI_API_KEY
    )
    analysis_str = f"Token: {token}\nAnalysis Data: {str(analysis)}\nDate of Analysis: {date}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes blockchain analysis results."},
            {"role": "user", "content": f"Summarize the following blockchain analysis data in a human-readable form:\n\n{analysis_str}"}
        ],
        temperature=0.7,
        max_tokens=200,
    )
    return response.get("choices")[0].get("message").get("content").strip()


def main(request, store):
    validate_top_n(TOP_N)
    validate_token_address(request["tokenAddress"])
    
    key = f"analysis-{request['tokenAddress']}"
    if key in store:
        return store[key]

    analyzer = SolanaTokenAnalyzer(
        token_address=request["tokenAddress"], top_n=TOP_N)
    results = analyzer.analyze()
    
    store[key] = summarize_results(results)
    return store[key]


if __name__ == "__main__":
    request = {
        "tokenAddress": "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump"
    }
    validate_top_n(TOP_N)
    validate_token_address(request["tokenAddress"])

    analyzer = SolanaTokenAnalyzer(
        token_address=request["tokenAddress"], top_n=TOP_N)
    results = analyzer.analyze()

    print(summarize_results(results))
