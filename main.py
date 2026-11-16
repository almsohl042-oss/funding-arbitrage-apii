from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

app = FastAPI(
    title="Simple Funding Arbitrage Calculator API",
    version="1.1.0",
    description="Calculates paired long/short P&L from prices, fees, funding rates, margin and leverage."
)

class ExchangeInput(BaseModel):
    exchange: str
    side: Literal["long", "short"]
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    margin: float = Field(gt=0, description="Margin allocated to this exchange, in quote currency")
    leverage: float = Field(gt=0)
    funding_rate_pct: float = Field(default=0, description="Funding rate as percent; 0.01 means 0.01%")
    trading_fee_pct: float = Field(ge=0, description="Fee per fill as percent; 0.05 means 0.05%")

    def calculate(self):
        # Margin x leverage determines position notional.
        entry_notional = self.margin * self.leverage
        quantity = entry_notional / self.entry_price
        exit_notional = quantity * self.exit_price

        if self.side == "long":
            price_pnl = (self.exit_price - self.entry_price) * quantity
            funding_cashflow = -entry_notional * self.funding_rate_pct / 100
        else:
            price_pnl = (self.entry_price - self.exit_price) * quantity
            funding_cashflow = entry_notional * self.funding_rate_pct / 100

        entry_fee = entry_notional * self.trading_fee_pct / 100
        exit_fee = exit_notional * self.trading_fee_pct / 100
        total_fees = entry_fee + exit_fee
        net_pnl = price_pnl + funding_cashflow - total_fees

        return {
            "exchange": self.exchange,
            "side": self.side,
            "margin": round(self.margin, 8),
            "leverage": self.leverage,
            "position_notional": round(entry_notional, 8),
            "quantity": round(quantity, 12),
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_notional": round(entry_notional, 8),
            "exit_notional": round(exit_notional, 8),
            "price_pnl": round(price_pnl, 8),
            "funding_rate_pct": self.funding_rate_pct,
            "funding_cashflow": round(funding_cashflow, 8),
            "trading_fee_pct_per_fill": self.trading_fee_pct,
            "entry_fee": round(entry_fee, 8),
            "exit_fee": round(exit_fee, 8),
            "total_fees": round(total_fees, 8),
            "net_pnl": round(net_pnl, 8)
        }

class CalculatorRequest(BaseModel):
    symbol: str = "KAVAUSDT"
    quote_currency: str = "USDT"
    exchange_a: ExchangeInput
    exchange_b: ExchangeInput

    @model_validator(mode="after")
    def validate_hedge(self):
        if self.exchange_a.side == self.exchange_b.side:
            raise ValueError("The two exchange sides must be opposite: one long and one short.")
        return self

@app.get("/health")
def health():
    return {"status": "ok", "service": "simple-funding-arbitrage-calculator-api"}

@app.post("/v1/calculate")
def calculate(request: CalculatorRequest):
    a = request.exchange_a.calculate()
    b = request.exchange_b.calculate()

    price_pnl = a["price_pnl"] + b["price_pnl"]
    funding = a["funding_cashflow"] + b["funding_cashflow"]
    fees = a["total_fees"] + b["total_fees"]
    net = price_pnl + funding - fees
    total_margin = a["margin"] + b["margin"]

    return {
        "symbol": request.symbol,
        "quote_currency": request.quote_currency,
        "exchange_results": [a, b],
        "summary": {
            "combined_price_pnl": round(price_pnl, 8),
            "combined_funding_cashflow": round(funding, 8),
            "total_trading_fees": round(fees, 8),
            "net_profit_loss": round(net, 8),
            "total_margin": round(total_margin, 8),
            "roi_on_total_margin_pct": round(net / total_margin * 100, 8),
            "result": "PROFIT" if net > 0 else "LOSS" if net < 0 else "BREAK_EVEN"
        },
        "calculation_notes": [
            "Position notional = margin multiplied by leverage.",
            "Quantity = position notional divided by entry price.",
            "Trading fees are charged on entry and exit notional for each exchange.",
            "Positive funding rate means longs pay and shorts receive; negative rates reverse this.",
            "Funding is assumed to be received or paid once, and assumes the position qualifies at settlement.",
            "Leverage determines position size from margin; it does not multiply P&L again."
        ]
    }
