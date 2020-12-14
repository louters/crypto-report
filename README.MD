### Overview
**crypto-report** generates a report for your digital assets balance across different exchanges. In addition, it allows you to query your positions' last price in Fiat and/or Digital Asset base currency.

**crypto-report** addresses two issues:

* positions held across multiple exchanges are not reported through a unique interface; and
* exchanges do not provide a balance using a Digital Asset as Base Currency.

# Requirements
## Config
1. Supported exchanges/protocol addresses:
    * [x] Kraken
    * [x] Bitfinex
    * [] Bitcoin addresses
    * [x] Ethereum addresses
2. Define Base Asset(s) for your report
    * [x] Fiat (mandatory): USD, EUR, GBP
    * [x] Digital Asset (optional): BTC or ETH only.

## Update
1. Get Balance (value and amount) for each and all positions
    * [x] Fiat
    * [x] Digital Asset
    * [x] Tokens

## Report
1. Get Close Price in Base Asset for all positions
    * [x] Fiat
    * [x] Digital Asset
2. Get Balance (value and amount) for each and all positions
    * [x] Fiat
    * [x] Digital Asset
    * [x] Tokens
3. Provide Portfolio Risk Metrics
    * [] Worst-day historical VaR
    * [] 1 and 7-day VaR
    * [] Historical 7-day historical volatility chart

## Other
1. Store report in file
2. Store historical close data
3. Always get ETH and BTC price in Base Asset(s)

# Open questions
## Config
1. Add other exchanges, notably:
    * Binance
    * Huobi Global
    * Coinbase Pro

## Report
1. Which type (historical, parametric) of 1 and 7-day VaR?

