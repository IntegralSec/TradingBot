import logging
import pprint
import time
import hmac
import hashlib
from urllib.parse import urlencode

import requests

# API DOCS
# https://binance-docs.github.io/apidocs/#change-log

logger = logging.getLogger()

class BinancefutureClient:
    def __init__(self, public_key, secret_key, testnet=True, ):
        """
        Initiate the class
        :param testnet: True if using the testnet (default) else False if using production
        """
        if testnet:
            self.base_url = "https://testnet.binancefuture.com"
            logger.info("Binance Futures Testnet Client successfully initiated")
        else:
            self.base_url = "https://fapi.binance.com"
            logger.info("Binance Futures Client successfully initiated")
        self.prices = dict()

        self.public_key = public_key
        self.secret_key = secret_key

        self.headers = {'X-MBX-APIKEY': self.public_key}

    def make_request(self, method, endpoint, data):
        """
        Helper method for making API requests
        :param method:
        :param endpoint:
        :param data:
        :return:
        """
        if method == "GET":
            response = requests.get(self.base_url + endpoint, params=data, headers=self.headers)
        else:
            return ValueError("Only supports HTTP GET")

        if response.status_code == 200:
            return response.json()
        if response.status_code == 400:
            logger.error("Error 400")
            logger.debug(response.text)
        if response.status_code == 404:
            logger.error("Error 404")
            logger.debug(response.text)
        else:
            logger.error("Error %s while making %s to %s ", response.status_code, method, endpoint)
            return None

    def generate_signature(self, data):
        """
        Genenereate a signature that the API requires in the last argument
        :param data: the data that you are sending to the API
        :return: The a dictionary {'signature': the_signature}
        """
        if data is None:
            return None
        if self.secret_key is None:
            return None
        signature_data = urlencode(data)
        key = self.secret_key
        signature = hmac.new(key.encode(), signature_data.encode(), hashlib.sha256).hexdigest()
        signature = {'signature': signature}
        return signature

    def get_balance(self):
        """
        Gets a list of your holdings
        :return: A dictionary of balances
        """
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        # The signature needs to be added to the end of the data
        data.update(self.generate_signature(data))
        account_data = self.make_request("GET", "/fapi/v1/account", data)
        balances = dict()  # This will be the return value
        if account_data is not None:
            for a in account_data['assets']:
                balances[a['asset']] = a
            # Return the dictionary of balances
            return balances
        else:
            return None

    def get_wallet_balance(self):
        result = self.get_balance()
        return_value = dict()
        for key, value in result.items():
            return_value.update({key: value['walletBalance']})
        return return_value

    def get_contracts(self):
        """
        Returns a list of contracts and their details
        :return:
        """

        exchange_info = self.make_request("GET", "/fapi/v1/exchangeInfo", None)
        contracts = dict()
        if exchange_info is not None:
            for contract_data in exchange_info['symbols']:
                contracts[contract_data['pair']] = contract_data
        return contracts

    def get_historical_candles(self, symbol, interval):
        data = dict()
        data['symbol'] = symbol
        data['interval'] = interval
        data['limit'] = 1000

        raw_candles = self.make_request("GET", "/fapi/v1/klines", data)
        candles = []
        if raw_candles is not None:
            for c in raw_candles:
                # note it's appending a list
                candles.append([c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4])])
            # If complete
            return candles
        else:
            return None

    def get_bid_ask(self, symbol):
        """
        Returns the bid and ask price of a stock
        :param symbol: The symbol of the stock
        :return:
        """
        data = dict()
        data["symbol"] = symbol
        ob_data = self.make_request("GET", "/fapi/v1/ticker/bookTicker", data)
        if ob_data is not None:
            if symbol not in self.prices:
                self.prices[symbol] = {"bid": float(ob_data["bidPrice"]), "ask": float(ob_data["askPrice"])}

        else:
            self.prices[symbol]['bid'] = float(ob_data['bidPrice'])
            self.prices[symbol]['ask'] = float(ob_data['askPrice'])
            return None
        return self.prices[symbol]

    def place_order(self):
        return

    def cancel_order(self):
        return

    def get_order_status(self, symbol, order_id):
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        data['symbol'] = symbol
        data['order_id'] = order_id
        data['signature'] = self.generate_signature(data)
        order_status = self.make_request("GET", "/fapi/v1/order", data)
        return order_status

