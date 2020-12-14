#!/usr/bin/env python3
from apis import Kraken, Bitfinex, Etherscan
from datetime import datetime

BASE_FIATS = {'USD', 'EUR', 'GBP'}
BASE_CRYPTOS = {'BTC', 'ETH'}
API_SOURCES = {'Kraken', 'Bitfinex', 'Etherscan'}


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

        # Initialize each API
        api_sources = [eval(api[0].capitalize())(api[1]) for api in apis if len(api) == 2]

        # Case where constructor has two files
        for api in apis:
            if len(api) == 3:
                api_sources.append(eval(api[0].capitalize())(api[1], api[2]))
        self.api_sources = api_sources

        self.balance = {}

    def get_balance(self) -> None:
        ''' Get balance of holdings from different APIs.'''
        for api_source in self.api_sources:
            if type(api_source).__name__ != 'Etherscan':
                self.balance[type(api_source).__name__] = (
                    api_source.get_balance(self.base_fiat, self.base_crypto))
            else:
                self.balance[type(api_source).__name__] = (
                    api_source.get_balance())

    def get_totals(self, ref_api: str='') -> None:
        ''' Get totals in base fiat and base digital asset.

        Args:
        - ref_api: For non-exchange APIs, the price from ref_api will be used.
        '''
        self.total_fiat = self.total_crypto = 0

        assert self.balance
        for api, holdings in self.balance.items():
            if api != 'Etherscan':
                for holding in holdings:
                    self.total_fiat += holdings[holding][1][1][0]

                    if self.base_crypto:
                        self.total_crypto += holdings[holding][1][1][1]
 
            else:
                self.total_fiat += (holdings['ETH'][0]
                                   * self.balance[ref_api]['ETH'][1][0][0])

                if self.base_crypto:
                    self.total_crypto += holdings['ETH'][0]
        return self.total_fiat, self.total_crypto


    def print_balance(self, ref_api: str=''):
        ''' Print a pretty balance. 

        Args:
        - ref_api: For non-exchange APIs, the price from ref_api will be used.
        '''
        format = ',.2f'

        # Checks
        if 'Etherscan' in self.balance.keys():
            assert ref_api

        if ref_api:
            ref_api = ref_api.capitalize()
            assert ref_api in self.balance

        if not hasattr(self, 'total_fiat'):
            self.get_totals(ref_api)

        # Print balance
        print()
        print(f'Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', end='\n\n')

        print(f'Total in {self.base_fiat}: {self.total_fiat:{format}}')
        if self.base_crypto:
            print(f'Total in {self.base_crypto}: {self.total_crypto:{format}}')

            if not ref_api:
                ref_api = 'Kraken'
                print('WARNING - setting Kraken as reference API', end='\n\n')
            print(f'{self.base_crypto} price: {self.balance[ref_api][self.base_crypto][1][0][0]:{format}}')

        for api, holding in self.balance.items():
            pass



