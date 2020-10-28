#!/usr/bin/env python3
from abc import ABC, abstractmethod
import base64
import json
import hashlib
import hmac
import time
import urllib.parse

import numpy as np
import requests


class Api(ABC):
    def __init__(self, path: str = '') -> None:
        """ Initialize session w/ API and load optional keys.

        Args:
        - path: Path to file with key and secret, each on a line
        """
        self.load_key(path)
        self.session = requests.Session()
        self.balance = {}

    def load_key(self, path: str) -> None:
        """ Load key and secret from file."""
        try:
            with open(path) as f:
                self.key = f.readline().strip()
                self.secret = f.readline().strip()
        except FileNotFoundError:
            print('Warning: File with key/secret not found')
            self.key = self.secret = ''

    @abstractmethod
    def get_balance(self, base_fiat: str = '', base_crypto: str = '') -> None:
        """ Get balance of holdings from an API source.

        Args:
        - base_fiat: currency in which the holdings are reported
        - base_crypto: digital asset in which the holdings are reported
        """
        pass

    def _nonce(self) -> int:
        """ Nonce counter."""
        return int(10000 * time.time())

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

    def get_balance(self, base_fiat: str = '', base_crypto: str = '') -> None:
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
            print('Kraken - Getting tickers...')
            for ticker in balance:
                # Get prices
                prices = self.get_price(
                                        ticker,
                                        self.base_fiat,
                                        self.base_crypto
                                        )
                prices = [float(price) for price in prices]
                # Convert holding to fiat/crypto amount
                balance[ticker].append([
                                      prices,
                                      list(np.array(balance[ticker]) *
                                           prices)
                                      ])

        self.balance = balance

    def get_price(
                 self, ticker: str, base_fiat: str, base_crypto: str = ''
                 ) -> tuple:
        """ Return last trade price of ticker in base fiat or crypto.

        Note: Potential issues when multiple pairs in one query, so base_fiat
        and base_crypto queries are called separately.
        """
        # Handle when ticker is fiat
        print(f'Ticker {ticker} with {base_fiat} and {base_crypto}')
        if ticker in ('EUR', 'USD'):
            if base_crypto:
                return 1, 1
            else:
                return 1,

        # Clean staking tickers
        if ticker.endswith('.S'):
            ticker = ticker[:-2]

        data = {'pair': ticker + base_fiat}
        res = self.query('Ticker', data)
        fiat_price = res[list(res.keys())[0]]['c'][0]

        # Just fiat value asked
        if not base_crypto:
            return fiat_price,

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
    """ Maintain a single session betwen this machine and Kraken."""
    pub_url = "https://api-pub.bitfinex.com/v2/"
    priv_url = "https://api.bitfinex.com/v2/"
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

    def _sign(self, data: dict, urlpath: str) -> str:
        """ Return signature digest according to Bitfinex's scheme.

        Args:
        - data: API request parameters
        - urlpath: API URL path w/o uri
        """
        pass