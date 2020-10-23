#!/usr/bin/env python3


class Portfolio(object):
    base_fiats = ['USD', 'EUR', 'GBP']
    base_cryptos = ['BTC', 'ETH']
    api_sources = ['Kraken', 'Bitfinex']

    def __init__(self, base_fiat: str, base_crypto: str, apis_source: str):
        self.base_fiat = base_fiat
        self.base_crypto = base_crypto
        self.apis_source = apis_source
        self.balance = {}

    def _get_balance(self):
        pass

    def get_last(self):
        pass
