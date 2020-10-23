#!/usr/bin/env python3

BASE_FIATS = {'USD', 'EUR', 'GBP'}
BASE_CRYPTOS = {'BTC', 'ETH'}
API_SOURCES = {'Kraken', 'Bitfinex'}


class Portfolio(object):

    def __init__(self, base_fiat: str, base_crypto: str, api_sources: set):
        base_fiat = base_fiat.upper()
        assert base_fiat in BASE_FIATS
        self.base_fiat = base_fiat

        base_crypto = base_crypto.upper()
        assert base_crypto in BASE_CRYPTOS
        self.base_crypto = base_crypto

        api_sources = {x.capitalize() for x in api_sources}
        assert api_sources in API_SOURCES
        self.api_sources = api_sources

        self.balance = {}

    def _get_balance(self):
        for api_source in self.api_sources:
            self.balance[api_source] = api_source.get_balance()

    def get_last(self):
        pass
