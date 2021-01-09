#!/usr/bin/env python3
import pandas as pd

from apis import Kraken, Bitfinex, Etherscan, Blockchain
from datetime import datetime

BASE_FIATS = {'USD', 'EUR'}
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
                self.ref_api = 'Kraken'
                print('WARNING - reference API set to Kraken')
            # Check ref_api exists in dataframe
            else:
                assert ref_api != 'Etherscan'
                assert ref_api != 'Blockchain'
                self.ref_api = ref_api

        if 'Etherscan' in self.balance.index:
            self.set_address_prices('Etherscan', self.ref_api)
        if 'Blockchain' in self.balance.index:
            self.set_address_prices('Blockchain', self.ref_api)

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
        tmp = self.get_simple_balance().copy()

        col_names = ['Amount', 'price_f', 'value_f', 'value_c']
        if not self.base_crypto:
            col_names.pop()
        for col in col_names:
            tmp[col] = self.balance[col].map('{:,.2f}'.format)

        if self.base_crypto:
            tmp['price_c'] = self.balance['price_c'].map('{:,.4f}'.format)

        print(tmp, end=2*'\n')

    def get_simple_balance(self, threshold: float=0.01) -> pd.DataFrame:
        ''' Returns a balance where onlu holdings with a fiat value higher than
        <treshold> are reported.

        Args:
        - threshold: minimum fiat value for asset to be reported
        '''
        if self.balance.empty:
            self.get_balance()

        if not hasattr(self, 'simple_balance'):
            self.simple_balance = self.balance.copy()
            self.simple_balance = self.balance.loc[
                                        self.balance['value_f'] >= threshold]
        return self.simple_balance

    def set_address_prices(self, api: str, ref_api: str) -> None:
        ''' Set ETH or BTC address price(s)

        Args:
        - api: Either 'Etherscan' or 'Blockchain' (explorer)
        - ref_api: the API from which the price will be used
        '''
        if api == 'Etherscan':
            crypto = 'ETH'
        elif api == 'Blockchain':
            crypto = 'BTC'
        else:
            raise Exception(f'{api} is not implemented.')

        try:
            self.balance.loc[(api, crypto)]['price_f'] = self.balance.loc[(ref_api, crypto)]['price_f']
            if self.base_crypto == crypto:
                    self.balance.loc[(api, crypto)]['price_c'] = 1
            else:
                    self.balance.loc[(api, crypto)]['price_c'] = self.balance[(ref_api, crypto)]['price_c']
        except KeyError:
            ref_api_session = eval(ref_api)()
            price_f, price_c = ref_api_session.get_price(crypto, self.base_fiat, self.base_crypto)
            self.balance.loc[(api, crypto)]['price_f'] = price_f
            self.balance.loc[(api, crypto)]['price_c'] = price_c

    def get_risk(self, ref_api: str) -> None:
        ''' Print a set of risk measures of portfolio.

        N.B.: No backfilling is performed.
        Args:
        - ref_api: for non-exchange APIs, the API from which history will
        downloaded from
        '''

        # Checks for ref api
        if ref_api and not hasattr(self, 'ref_api'):
            self.ref_api = ref_api
        elif ref_api and self.ref_api != ref_api:
            print(f'ref_api is already set as {self.ref_api} and will not be changed')
        elif not ref_api and not hasattr(self, 'ref_api'):
            self.ref_api = 'Kraken'
            print('WARNING - reference API set to Kraken')

        # Check simple balance exists
        if not hasattr(self, 'simple_balance'):
            self.get_simple_balance()

        df = pd.DataFrame()
        # Get historical close data
        for api, asset in self.simple_balance.index:
            if api != 'Etherscan' and api != 'Blockchain' \
            and asset not in BASE_FIATS:
                ticker = asset + self.base_fiat
                method = f"{api}()"
                df[api + '-' + asset] = eval(method).get_history(ticker)['close']

        # DROP NA fo same length of time series (no backfilling)
        print()
        df.dropna(inplace=True)
        print(f'History\'s length: {len(df.index)} days', end=2*'\n')

        # Compute ret in % (not log returns!) and fiat
        ret = df.pct_change().dropna()
        ret_7d = df.pct_change(periods=7).dropna()

        # Compute 20-days daily volatility, not annualized
        index = pd.MultiIndex.from_tuples((
                                        idx.split('-') for idx in ret.columns
                                        ), names = ['API', 'Asset'])
        vols = pd.DataFrame(ret.iloc[-21:-1].std().copy(), columns=['vol_pct'])
        vols.index = index

        # Compute 20-days daily volatility in fiat value
        if 'Etherscan' in self.simple_balance.index:
            vols.loc[('Etherscan', 'ETH'), :] = vols.loc[(ref_api, 'ETH'), :]
        if 'Blockchain' in self.simple_balance.index:
            vols.loc[('Blockchain', 'BTC'), :] = vols.loc[(ref_api, 'BTC'), :]

        vols['vol_fiat'] = vols['vol_pct'] * self.simple_balance['value_f']
        print(f'Daily volatility over last 20 days: ', end='')
        print(f'{vols["vol_fiat"].sum():,.2f}', end=2*'\n')
        print(vols, end=2*'\n')

        # Set return values for non-exchange holdings
        if 'Etherscan' in self.simple_balance.index:
            ret['Etherscan-ETH'] = ret[self.ref_api + '-ETH']
            ret_7d['Etherscan-ETH'] = ret_7d[self.ref_api + '-ETH']
        if 'Blockchain' in self.simple_balance.index:
            ret['Blockchain-BTC'] = ret[self.ref_api + '-BTC']
            ret_7d['Blockchain-BTC'] = ret_7d[self.ref_api + '-BTC']

        # Compute 1-day and 7-days portfolio fiat p&l
        tmp = ret.copy()
        tmp_7d = ret_7d.copy()
        for idx in self.simple_balance.index:
            idx_ret = '-'.join(idx)
            tmp[idx_ret] = ret[idx_ret] * self.simple_balance.loc[idx, 'value_f']
            tmp_7d[idx_ret] = ret_7d[idx_ret] * self.simple_balance.loc[idx, 'value_f']

        # Worst/Best days/weeks
        totals = tmp.sum(axis=1).sort_values()
        print(f'Worst day ', end='')
        print(f'({totals.iloc[[0]].index[0]:%d/%m/%Y}): ', end='')
        print(f'{totals.iloc[0]:,.2f} {self.base_fiat}')
        print(f'Best day ', end='')
        print(f'({totals.iloc[[-1]].index[0]:%d/%m/%Y}): ', end='')
        print(f'{totals.iloc[-1]:,.2f} {self.base_fiat}', end=2*'\n')

        totals_7d = tmp_7d.sum(axis=1).sort_values()
        print(f'Worst week ', end='')
        print(f'({totals_7d.iloc[[0]].index[0]:%d/%m/%Y}): ', end='')
        print(f'{totals_7d.iloc[0]:,.2f} {self.base_fiat}')
        print(f'Best week ', end='')
        print(f'({totals_7d.iloc[[-1]].index[0]:%d/%m/%Y}): ', end='')
        print(f'{totals_7d.iloc[-1]:,.2f} {self.base_fiat}', end=2*'\n')
        
        # Expected Shortfall 1-day & 7-days at 97.5%
        es_1d = totals.iloc[:int(len(totals) * 0.025)].mean()
        print(f'1-day Expected Shortfall @ 97.5%: {es_1d:,.2f}')
        es_7d = totals_7d.iloc[:int(len(totals_7d) * 0.025)].mean()
        print(f'7-day Expected Shortfall @ 97.5%: {es_7d:,.2f}', end=2*'\n')

        return totals, totals_7d
