#!/usr/bin/env python3
from pprint import pprint
from portfolio import Portfolio


def main():
    apis = {('Kraken', 'kraken.key'), ('Bitfinex', 'bitfinex.key'),
           ('Etherscan','etherscan.key', 'eth_addr'),
           ('Blockchain', 'btc_addr')}
    base_fiat = 'USD'
    base_crypto = 'BTC'
    p = Portfolio(apis, base_fiat, base_crypto)
    p.get_balance(ref_api='Kraken')
    p.print_balance()

if __name__ == '__main__':
    main()
