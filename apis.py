#!/usr/bin/env python3
from abc import ABC, abstractmethod
import base64
import json
import hashlib
import hmac
import requests
import time
import urllib.parse


class Api(ABC):
    def __init__(self, path: str = '') -> None:
        """ Initialize session w/ API and load optional keys.

        Args:
        - path: Path to file with key and secret, each on a line
        """
        self.load_key(path)
        self.session = requests.Session()

    def load_key(self, path: str) -> None:
        """ Load key and secret from file."""
        try:
            with open(path) as f:
                self.key = f.readline().strip()
                self.secret = f.readline().strip()
        except FileNotFoundError:
            print('Warning: File with key/secret not found')
            self.key = self.secret = ''

    def _nonce(self) -> int:
        """ Nonce counter."""
        return int(10000 * time.time())

    @abstractmethod
    def _sign(self, data, urlpath) -> str:
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
                raise Exception("At one of key or secret is not set.")
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

        return response.json()

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
