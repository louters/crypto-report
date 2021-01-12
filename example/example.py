#!/usr/bin/env python3
from pprint import pprint
from portfolio import Portfolio


def main():
    apis = {('Kraken', 'kraken.key'), ('Bitfinex', 'bitfinex.key'),
           ('Etherscan','etherscan.key', 'eth_addr'),
           ('Blockchain', 'btc_addr')}
    base_fiat = 'USD'
    base_crypto = 'BTC'
    ref_api = 'Bitfinex'
    
    p = Portfolio(apis, base_fiat, base_crypto, ref_api)
    p.get_balance()
    p.print_balance()
    p.get_risk()

if __name__ == '__main__':
    main()
