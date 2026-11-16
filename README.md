# Simple Funding Arbitrage Calculator API

This API calculates paired funding-arbitrage P&L using only:
- Both exchanges' entry and exit prices
- Long/short side for each exchange
- Margin allocated to each exchange
- Leverage for each exchange
- Funding rate for each exchange
- Trading fee percentage for each exchange

It does not fetch market data, connect to accounts, or place orders.

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `/docs` on the running server for interactive API testing.

## Endpoint

`POST /v1/calculate`

`GET /health`

## Input units

- Prices: quote currency per base asset (e.g. USDT per KAVA)
- Margin: quote currency (e.g. USDT), entered separately for each exchange
- Leverage: multiplier (e.g. 5 for 5x)
- Funding rate: percent (0.01 means 0.01%, not 1%)
- Trading fee: percent per fill (0.05 means 0.05% on entry and again on exit)

## Formula

For each exchange:

- Position notional = margin × leverage
- Quantity = position notional ÷ entry price
- Long price P&L = (exit − entry) × quantity
- Short price P&L = (entry − exit) × quantity
- Funding cashflow = −notional × funding rate for a long; +notional × funding rate for a short
- Fees = entry notional × fee + exit notional × fee
- Net P&L = price P&L + funding cashflow − fees

Combined net P&L is the sum of both exchange legs.

A positive funding rate conventionally means longs pay and shorts receive. Verify the sign convention and funding eligibility for the specific contract/exchange. This model assumes one funding settlement and that both positions qualify for it.

Leverage is used to derive position notional from margin. Do not multiply the resulting P&L by leverage a second time.

## Example

See `sample_request.json`.

This is a simple calculation API, not a live trading bot or a complete execution simulator. It excludes slippage, spread, borrow costs, liquidation costs, and partial fills.
