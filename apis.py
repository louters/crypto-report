#!/usr/bin/env python3
from abc import ABC, abstractmethod
import base64
import json
import hashlib
import hmac
import time
import urllib.parse

import pandas as pd
import requests


class Api(ABC):
    col_names = ['Asset', 'Amount', 'price_f', 'price_c']

    def __init__(self, path: str = '') -> None:
        """ Initialize session w/ API and load optional keys.

        Args:
        - path: Path to file with key and secret, each on a line
        """
        self.load_key(path)
        self.session = requests.Session()
        self.balance = None

    def load_key(self, path: str, addr_path: str = '') -> None:
        """ Load key and secret or address from file(s).

        Args: 
        - path: Path to file with API public key and, if an exchange, secret
        - (optional) addr_path: Path to file with addresses (only applicable
          to etherscan and blockchain explorer)
        """
        try:
            with open(path) as f:
                self.key = f.readline().strip()

                if not addr_path:
                    self.secret = f.readline().strip()

            if addr_path:
                with open(addr_path) as f:
                    self.address = f.readline().strip()
                
        except FileNotFoundError:
            print('Warning: File with key/secret not found')
            self.key = self.secret = self.address = ''

    @staticmethod
    def _balance_to_dataframe(balance: dict, api_name: str) -> pd.DataFrame:
        '''Convert dictionary balance into a pandas dataframe.'''
        df = pd.DataFrame.from_dict(balance, orient = 'index', dtype='float')
        df.reset_index(inplace = True)
        df.columns = Api.col_names
        df['API'] = api_name
        df = df[['API'] + Api.col_names]

        return df
        
    def _nonce(self) -> int:
        """ Nonce counter."""
        return int(1000 * time.time())

    @abstractmethod    
    def get_balance(self) -> pd.DataFrame:
        """ Get balance of holdings from an API source."""
        pass

    @abstractmethod
    def _sign(self, data: dict, urlpath: str) -> str:
        """ Authenticate according to API source's scheme.

        Args:
        - data: API request parameters
        - urlpath: API URL path w/o uri
        """
        pass


class Kraken(Api):
    """ Maintain a single session betwen this machine and Kraken.

    Inspired by Krakenex:
    https://github.com/veox/python3-krakenex/blob/master/krakenex/api.py
    """
    uri = "https://api.kraken.com/"
    api_version = "0"
    public_methods = (
                   "Time",
                   "Assets",
                   "AssetPairs",
                   "Ticker",
                   "OHLC",
                   "Depth",
                   "Trades",
                   "Spread"
                   )

    def close(self) -> None:
        """ Close this session. """
        self.session.close()
        print("Kraken session closed.")

    def query(self, method: str, data: dict = {}, headers: dict = {}):
        """ Low-level query handling.

        Args:
        - method: API method name
        - urlpath: API URL w/o uri
        - data: API request parameters
        """
        # Public Query
        if method in Kraken.public_methods:
            url = Kraken.uri + Kraken.api_version + "/public/" + method

        # Private Query
        else:
            if not self.key or not self.secret:
                raise Exception("At least one of key or secret is not set.")
            data['nonce'] = self._nonce()
            urlpath = "/" + Kraken.api_version + "/private/" + method
            headers = {
                    'API-Key': self.key,
                    'API-Sign': self._sign(data, urlpath)
                    }

            url = Kraken.uri + Kraken.api_version + "/private/" + method

        response = self.session.post(url, data=data, headers=headers)
        if response.status_code not in (200, 201, 202):
            response.raise_for_status()
        return response.json()['result']

    def _sign(self, data: dict, urlpath: str) -> str:
        """ Return signature digest according to Kraken' scheme.

        Args:
        - data: API request parameters
        - urlpath: API URL path w/o uri
        """
        postdata = urllib.parse.urlencode(data)

        encoded = (str(data['nonce']) + postdata).encode()
        msg = urlpath.encode() + hashlib.sha256(encoded).digest()

        sig = hmac.new(base64.b64decode(self.secret), msg, hashlib.sha512)
        sig_digest = base64.b64encode(sig.digest())
        return sig_digest.decode()

    def get_balance(self, base_fiat: str = '', base_crypto: str = '') -> pd.DataFrame:
        """ Get balance of holdings from an API source.

        Args:
        - base_fiat: currency in which the holdings are reported
        - base_crypto: digital asset in which the holdings are reported
        """
        balance = self.query('Balance')
        self.base_fiat = base_fiat
        if base_crypto == 'BTC':
            base_crypto = 'XBT'
        self.base_crypto = base_crypto

        # Remove zero values
        balance = {
                Kraken.clean_ticker(crypto): [float(amount)]
                for (crypto, amount) in balance.items()
                if float(amount) != 0
                }

        # Remove Kraken Fees
        balance.pop('KFEE', None)

        if base_fiat or base_crypto:
            for ticker in balance:
                # Get prices
                prices = self.get_price(
                                        ticker,
                                        self.base_fiat,
                                        self.base_crypto
                                        )
                prices = [float(price) for price in prices]
                balance[ticker] = balance[ticker] + prices
                                           
        self.balance = Api._balance_to_dataframe(balance, 'Kraken')

        return self.balance

    def get_price(
                 self, ticker: str, base_fiat: str, base_crypto: str = ''
                 ) -> tuple:
        """ Return last trade price of ticker in base fiat or crypto.

        Note: Potential issues when multiple pairs in one query, so base_fiat
        and base_crypto queries are called separately.

        Args:
        - ticker: Ticker of digital asset
        - base_fiat: currency in which the holdings are reported
        - base_crypto: digital asset in which the holdings are reported
        """
        # Handle when ticker is fiat
        if ticker in ('EUR', 'USD'):
            if base_crypto:
                return 1, 1
            else:
                return 1, 0

        # Clean staking tickers
        if ticker.endswith('.S'):
            ticker = ticker[:-2]

        data = {'pair': ticker + base_fiat}
        res = self.query('Ticker', data)
        fiat_price = res[list(res.keys())[0]]['c'][0]

        # Just fiat value asked
        if not base_crypto:
            return fiat_price, 0

        if base_crypto == ticker:
            return (fiat_price, 1)

        if base_crypto == 'ETH' and ticker == 'XBT':
            data_crypto = {'pair': 'ETHXBT'}
            res = self.query('Ticker', data_crypto)
            crypto_price = 1/float(res[list(res.keys())[0]]['c'][0])

        else:
            data_crypto = {'pair': ticker + base_crypto}
            res = self.query('Ticker', data_crypto)
            crypto_price = res[list(res.keys())[0]]['c'][0]

        return (fiat_price, crypto_price)

    @staticmethod
    def clean_ticker(ticker: str) -> str:
        """ Clean ticker so we can use it for other API calls."""
        if len(ticker) == 4 and ticker[0] in ('X', 'Z'):
            return ticker[1:]
        else:
            return ticker


class Bitfinex(Api):
    """ Maintain a single session betwen this machine and Bitfinex."""
    uri = "https://api-pub.bitfinex.com/v2/"
    public_methods = (
                   'platform/status',
                   'tickers',
                   'Trades',
                   'book',
                   'stats1',
                   'candles/trade',
                   'conf',
                   'status',
                   'liquidation/hist',
                   'rankings',
                   'pulse/hist',
                   'pulse/profile',
                   'calc/trade/avg',
                   'calc/fx'
                   )
    'Crytpo that will be ignored, to keep updated'
    shitcoins = ('ATD', 'ADD', 'MTO', 'MQX', 'IQX')

    def _sign(self, data: dict, urlpath: str) -> dict:
        """ Return signature digest according to Bitfinex's scheme.

        Args:
        - data: API request parameters
        - urlpath: API URL path w/o uri
        """
        nonce = str(self._nonce())
        signature = f'/api/v2/{urlpath}{nonce}{data}'
        h = hmac.new(self.secret.encode('utf8'), signature.encode('utf8'),
                     hashlib.sha384)
        signature = h.hexdigest()

        return {
            "bfx-nonce": nonce,
            "bfx-apikey": self.key,
            "bfx-signature": signature
            }

    def post(self, method: str, data: dict = {}, params: str = "") -> list:
        """ Signed POST query to Bitfinex's API.

        Args:
        - method: API URL path w/o uri
        - data: API request mandatory parameters
        - params: API request optional parameters
        """
        url = f'{Bitfinex.uri}{method}'
        data = json.dumps(data)
        headers = self._sign(data, method)
        headers['content-type'] = 'application/json'
        response = self.session.post(url + params, headers=headers, data=data)
        if response.status_code not in (200, 201, 202):
            response.raise_for_status()
        return json.loads(response.text)

    def fetch(self, method: str, params: str = "") -> list:
        """ GET query to Bitfinex's API.

        Args:
        - method: API url w/o uri
        - params: API request optional parameters
        """
        url = f'{Bitfinex.uri}{method}{params}'
        response = self.session.get(url)
        if response.status_code not in (200, 201, 202):
            response.raise_for_status()
        return json.loads(response.text)

    def get_balance(self, base_fiat: str = '', base_crypto: str = '') -> dict:
        """ Get balance of holdings from a API source.

        Args:
        - base_fiat: currency in which the holdings are reported
        - base_crypto: digital asset in which the holdings are reported
        """
        # Get wallets
        method = 'auth/r/wallets'
        res = self.post(method)
        balance = {}
        for wallet in res:
            if wallet[1] not in Bitfinex.shitcoins:
                balance[wallet[1]] = [float(wallet[2])]

        self.base_fiat = base_fiat
        self.base_crypto = base_crypto

        if base_fiat or base_crypto:
            for ticker in balance:
                # Get prices
                prices = self.get_price(ticker,
                                        self.base_fiat,
                                        self.base_crypto
                                        )
                prices = [float(price) for price in prices]
                balance[ticker] = balance[ticker] + prices

        self.balance = Api._balance_to_dataframe(balance, 'Bitfinex')

        return self.balance

    def get_price(self, ticker: str, base_fiat: str,
                  base_crypto: str = "") -> tuple:
        """ Return last trade price of ticker in base fiat or crypto.

        Args:
        - ticker: Ticker of digital asset
        - base_fiat: currency in which the holdings are reported
        - base_crypto: digital asset in which the holdings are reported
        """
        # Handle when ticker is fiat
        if ticker in ('EUR', 'USD'):
            if base_crypto:
                return 1, 1
            else:
                return 1, 0

        # Fetch price
        try:
            method = f'ticker/t{ticker}{base_fiat}'
            fiat_price = self.fetch(method)[6]
        # Handle case where ticker not available in base_fiat
        except requests.exceptions.HTTPError:
            if base_crypto != 'USD':
                fiat_price = (self.fetch(f'ticker/t{ticker}USD')[6] /
                              self.fetch(f'ticker/t{base_fiat}USD')[0])
            else:
                raise requests.exceptions.HTTPError

        # Just fiat value asked
        if not base_crypto:
            return fiat_price, 0

        if base_crypto == ticker:
            return (fiat_price, 1)

        if base_crypto == 'ETH' and ticker == 'BTC':
            method = f'ticker/t{base_crypto}{ticker}'
            crypto_price = 1/float(self.fetch(method)[6])

        else:
            method = f'ticker/t{ticker}{base_crypto}'
            crypto_price = self.fetch(method)[6]

        return (fiat_price, crypto_price)


class Etherscan(Api):
    """ Maintain a single session between this machine and Etherscan. """
    uri = "https://api.etherscan.io/api"

    def __init__(self, key_path: str = 'etherscan.key', addr_path: str = 'eth_addr') -> None:
        """ Initialize session w/ API and load key and ETH addresses.

        Note: At the moment, it allows only one Ethereum address to be loaded.

        Args:
        - key_path: Path to file with API key.
        - addr_path: Path to file with Ethereum address."""

        self.load_key(key_path, addr_path)
        self.session = requests.Session()

    def _sign(self):
        """ Not applicable for Etherscan API """
        pass

    def get_balance(self) -> pd.DataFrame:
        """ Get amount of ETH at address <addr>."""
        params = {
               'module': 'account',
               'action': 'balance',
               'address': self.address,
               'tag': 'latest',
               'apikey': self.key
               }

        response = self.session.post(Etherscan.uri, params)
        if not response.ok:
            response.raise_for_status()

        balance = {}
        balance['ETH'] = [float(json.loads(response.text)['result'])/1e18] + [0, 0]

        self.balance = Api._balance_to_dataframe(balance, 'Etherscan')
        return self.balance
