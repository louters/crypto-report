#!/usr/bin/env python3
from apis import Kraken, Bitfinex

BASE_FIATS = {'USD', 'EUR', 'GBP'}
BASE_CRYPTOS = {'BTC', 'ETH'}
API_SOURCES = {'Kraken', 'Bitfinex'}


class Portfolio(object):

    def __init__(self, apis: set, base_fiat: str, base_crypto: str = ''):
        ''' Initialize Portfolio with basic information and checking.

        Args:
        - apis: {(<API Source>, <path to key>)} eg {('Kraken', 'kraken.key')}
        - base_fiat: currency in which holdings are reported
        - base_crypto: digital asset in which holdings are reported
        '''

        base_fiat = base_fiat.upper()
        assert base_fiat in BASE_FIATS
        self.base_fiat = base_fiat

        base_crypto = base_crypto.upper()
        assert base_crypto in BASE_CRYPTOS
        self.base_crypto = base_crypto

        for api_source in apis:
            assert api_source[0].capitalize() in API_SOURCES
        api_sources = [eval(x[0].capitalize())(x[1]) for x in apis]
        self.api_sources = api_sources

        self.balance = {}

    def get_balance(self):
        ''' Get balance of holdings from different APIs.'''
        for api_source in self.api_sources:
            self.balance[type(api_source).__name__] = api_source.get_balance(
                                       self.base_fiat, self.base_crypto)

    def get_last(self):
        pass
