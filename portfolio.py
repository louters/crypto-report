#!/usr/bin/env python3

BASE_FIATS = {'USD', 'EUR', 'GBP'}
BASE_CRYPTOS = {'BTC', 'ETH'}
API_SOURCES = {'Kraken', 'Bitfinex'}


class Portfolio(object):

    def __init__(self, base_fiat: str, base_crypto: str, api_sources: set):
        assert base_fiat in BASE_FIATS
        self.base_fiat = base_fiat

        assert base_crypto in BASE_CRYPTOS
        self.base_crypto = base_crypto

        assert api_sources in API_SOURCES
        self.api_sources = api_sources

        self.balance = {}

    def _get_balance(self):
        pass

    def get_last(self):
        pass
