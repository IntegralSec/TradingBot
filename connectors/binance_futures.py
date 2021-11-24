import logging
import pprint
import time
import hmac
import hashlib
from urllib.parse import urlencode
import websocket
import threading
import requests
import json

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
            self.wss_url = "wss://stream.binancefuture.com/ws"
            logger.info("Binance Futures Testnet Client successfully initiated")
        else:
            self.base_url = "https://fapi.binance.com"
            self.wss_url = "wss://fstream.binance.com/ws"
            logger.info("Binance Futures Client successfully initiated")
        self.prices = dict()
        self.id = 1
        self.ws = None
        # Create a Thread object and start it
        t = threading.Thread(target=self.start_ws())
        t.start()
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
        elif method == "POST":
            response = requests.post(self.base_url + endpoint, params=data, headers=self.headers)
        elif method == "DELETE":
            response = requests.delete(self.base_url + endpoint, params=data, headers=self.headers)
        else:
            return ValueError("The Method arg only supports GET, POST or DELETE")

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
        signature = self.generate_signature(data)
        data.update(signature)
        account_data = self.make_request("GET", "/fapi/v1/account", data)
        balances = dict()
        if account_data is not None:
            for asset in account_data['assets']:
                balances.update({asset['asset']: asset})
            return balances
        else:
            return None

    def get_asset_balance(self):
        """
        Gets the symbol and current balance
        :return: A dictionary with {symbol: currentBalance} of each item in the wallet
        """
        data = dict()
        data['timestamp'] = int(time.time() * 1000)
        # The signature needs to be added to the end of the data
        signature = self.generate_signature(data)
        data.update(signature)
        account_data = self.make_request("GET", "/fapi/v1/account", data)
        assets = account_data['assets']
        return_value = dict()
        for asset in assets:
            return_value.update({asset['asset']: asset['availableBalance']})
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
        """
        Gets a set of candle information from the exchange
        :param symbol:
        :param interval:
        :return: A nested list.  The child items contain the candle info for the interavl
        """
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

    def place_order(self, symbol, side, quantity, order_type, price=None, tif=None):
        data = dict()
        data['symbol'] = symbol
        data['side'] = side
        data['quantity'] = quantity
        data['type'] = order_type
        if price is not None:
            data['price'] = price
        if tif is not None:
            data['timeInForce'] = tif
        data['timestamp'] = int(time.time() * 1000)
        signature = self.generate_signature(data)
        data.update(signature)
        order_status = self.make_request("POST", "/fapi/v1/order", data)
        if order_status is not None:
            return order_status
        else:
            return False

    def cancel_order(self, symbol, order_id=None, orig_client_order_id=None):
        data = dict()
        data['symbol'] = symbol
        if order_id is not None:
            data['order_id'] = order_id
        if orig_client_order_id is not None:
            data['origClientOrderId'] = orig_client_order_id
        data['timestamp'] = int(time.time() * 1000)
        signature = self.generate_signature(data)
        data.update(signature)
        order_status = self.make_request("DELETE", "/fapi/v1/order", data)
        if order_status is not None:
            return order_status
        else:
            return False

    def get_order_status(self, symbol, order_id=None, orig_client_order_id=None):
        data = dict()
        data['symbol'] = symbol
        if order_id is not None:
            data['order_id'] = order_id
        if orig_client_order_id is not None:
            data['origClientOrderId'] = orig_client_order_id
        data['timestamp'] = int(time.time() * 1000)
        signature = self.generate_signature(data)
        data.update(signature)
        order_status = self.make_request("GET", "/fapi/v1/order", data)
        return order_status

    def start_ws(self):
        self.ws = websocket.WebSocketApp(self.wss_url, on_open=self.on_open, on_close=self.on_close, on_error=self.on_error, on_message=self.on_message)
        self.ws.run_forever()
        return

    def on_error(self, wsapp, err):
        logger.warning("Binance WebSocket connection error: " + str(err))
        return

    def on_open(self, wsapp):
        logger.info("Binance WebSocket connection opened")
        self.subscribe_channel("BTCUSDT")
        return

    def on_close(self, wsapp, close_status_code, close_msg):
        # Because on_close was triggered, we know the opcode = 8
        logger.info("Binance WebSocket connection closed")
        if close_status_code or close_msg:
            logger.info("close status code: " + str(close_status_code))
            logger.info("close message: " + str(close_msg))

    def on_message(self, wsapp, msg):
        # convert string to json
        data = json.loads(msg)
        if "e" in data:
            data['e'] == "bookTicker"
            symbol = data['s']
            if symbol not in self.prices:
                self.prices[symbol] = {"bid": float(data["b"]), "ask": float(data["a"])}
            else:
                self.prices[symbol]['bid'] = float(data['b'])
                self.prices[symbol]['ask'] = float(data['a'])
            print(self.prices[symbol])

        return

    def subscribe_channel(self, symbol):
        data = dict()
        data['method'] = "SUBSCRIBE"
        data['params'] = []
        data['params'].append(symbol.lower() + "@bookTicker")
        data['id'] = self.id
        # convert json to string and send
        self.ws.send(json.dumps(data))
        self.id += 1
        return