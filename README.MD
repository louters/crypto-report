### Overview
**crypto-report** generates a report for your digital assets balance across different exchanges. In addition, it produces a number of risk metrics with regards to the portfolio.

**crypto-report** addresses two issues:

* positions held across multiple exchanges are not reported through a unique interface; and
* exchanges do not provide a balance using a Digital Asset as Base Currency.

# Requirements
## Config
1. Supported exchanges/protocol addresses:
    * [x] Kraken
    * [x] Bitfinex
    * [x] Bitcoin addresses
    * [x] Ethereum addresses
2. Define Base Asset(s) for your report
    * [x] Fiat (mandatory): USD, EUR, GBP
    * [x] Digital Asset (optional): BTC or ETH only.

## Report
1. Get Amount for each and all positions
    * [x] Fiat
    * [x] Digital Asset
    * [x] Tokens
2. Get Price(s) in Base Asset(s) for all positions
    * [x] Fiat
    * [x] Digital Asset
3. Get Value(s) in Base Asset(s) for all positions
4. Provide Portfolio Risk Metrics
    * [] Worst-day historical VaR
    * [] 1 and 7-day historical VaR
    * [] 20-days moving average volatility for portfolio and per holding in fiat
    * [] Chart of 20-days moving average volatility per holding in percent

# Open questions
## Config
1. Add other exchanges, notably:
    * Binance
    * Huobi Global
    * Coinbase Pro
