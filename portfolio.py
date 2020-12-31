#!/usr/bin/env python3
import pandas as pd

from apis import Kraken, Bitfinex, Etherscan, Blockchain
from datetime import datetime

BASE_FIATS = {'USD', 'EUR', 'GBP'}
BASE_CRYPTOS = {'BTC', 'ETH'}
API_SOURCES = {'Kraken', 'Bitfinex', 'Etherscan', 'Blockchain'}


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
        if base_crypto:
            assert base_crypto in BASE_CRYPTOS
        self.base_crypto = base_crypto

        for api_source in apis:
            assert api_source[0].capitalize() in API_SOURCES

        # Initialize each API (one file only)
        api_sources = [eval(api[0].capitalize())(api[1]) for api in apis if len(api) == 2]

        # Case where constructor has two files
        for api in apis:
            if len(api) == 3:
                api_sources.append(eval(api[0].capitalize())(api[1], api[2]))
        self.api_sources = api_sources

        self.balance = pd.DataFrame(columns = ['Asset', 'Amount', 'price_f', 'price_c'])

    def get_balance(self, ref_api: str='') -> pd.DataFrame:
        ''' Get balance of holdings from different APIs.

        Args:
        - ref_api: For non-exchange APIs, the prices from ref_api will be used.
        '''
        
        # Get balance for different APIs
        for api_source in self.api_sources:
            # Case for exchanges
            if api_source.__class__.__name__ != 'Etherscan' \
            and api_source.__class__.__name__ != 'Blockchain':
                self.balance = pd.merge(
                        api_source.get_balance(self.base_fiat, self.base_crypto),
                        self.balance, how='outer')
            # Case for BTC/ETH addresses
            else:
                self.balance = pd.merge(api_source.get_balance(), self.balance,
                                        how='outer')

        # Set multi-index: API, Asset
        self.balance.set_index(['API', 'Asset'], inplace=True)

        # Setting price_c & price_f for Etherscan & Blockchain Explorer
        if 'Etherscan' in self.balance.index \
        or 'Blockchain' in self.balance.index:
            if not ref_api:
                ref_api = 'Kraken'
                print('WARNING - reference API set to Kraken')
            # Check ref_api exists in dataframe
            else:
                assert ref_api in self.balance.index
                assert ref_api != 'Etherscan'
                assert ref_api != 'Blockchain'

        if 'Etherscan' in self.balance.index:
            self.balance.loc[('Etherscan', 'ETH')]['price_f'] = self.balance.loc[(ref_api, 'ETH')]['price_f']
            if self.base_crypto == 'ETH':
                self.balance.loc[('Etherscan', 'ETH')]['price_c'] = 1
            else:
                self.balance.loc[('Etherscan', 'ETH')]['price_c'] = self.balance.loc[(ref_api, 'ETH')]['price_c']

        if 'Blockchain' in self.balance.index:
            self.balance.loc[('Blockchain', 'BTC')]['price_f'] = self.balance.loc[(ref_api, 'BTC')]['price_f']
            if self.base_crypto == 'BTC':
                self.balance.loc[('Blockchain', 'BTC')]['price_c'] = 1
            else:
                self.balance.loc[('Blockchain', 'BTC')]['price_c'] = self.balance.loc[(ref_api, 'BTC')]['price_c']

        # Add Fiat and Crypto Values columns
        self.balance['value_f'] = self.balance['Amount'] * self.balance['price_f']
        if self.base_crypto:
            self.balance['value_c'] = self.balance['Amount'] * self.balance['price_c']
        else:
            del self.balance['price_c']

        # Get total value in base fiat and digital asset
        self.total_fiat = self.balance['value_f'].sum()
        if self.base_crypto:
            self.total_crypto = self.balance['value_c'].sum()

        return self.balance

    def print_balance(self, ref_api: str='') -> None:
        ''' Print a pretty balance. 

        Args:
        - ref_api: For non-exchange APIs, the price from ref_api will be used.
        '''
        format = ',.2f'

        # Check balance exists
        if self.balance.empty:
            self.get_balance(ref_api)

        # Print totals
        print()
        print(f'Date: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', end='\n\n')
        print(f'Total in {self.base_fiat}: {self.total_fiat:{format}}')
        if self.base_crypto:
            print(f'Total in {self.base_crypto}: {self.total_crypto:{format}}')
        print()

        # Desc Sort
        self.balance.sort_values('value_f', ascending=False, inplace=True)

        # Format
        tmp = self.balance.copy()
        tmp = tmp.loc[tmp['value_f'] > 0.01] # Remove small values

        col_names = ['Amount', 'price_f', 'value_f', 'value_c']
        if not self.base_crypto:
            col_names.pop()
        for col in col_names:
            tmp[col] = self.balance[col].map('{:,.2f}'.format)

        if self.base_crypto:
            tmp['price_c'] = self.balance['price_c'].map('{:,.4f}'.format)

        print(tmp, end=2*'\n')
