# src/agents/impact_analysis.py
from src.schemas.state import NewsState

# Rule-based mapping dictionaries
COMPANY_TICKERS = {
    "HDFC Bank": "HDFCBANK",
    "ICICI Bank": "ICICIBANK",
    "Tata Motors": "TATAMOTORS"
}

SECTOR_TICKERS = {
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN"],
    "Automobile": ["TATAMOTORS", "M&M", "MARUTI"],
    "Financial Services": ["HDFCBANK", "ICICIBANK", "BAJFINANCE"]
}

def analyze_impact(state: NewsState) -> NewsState:
    print(f"\n📈 Analyzing stock impact for: '{state['title']}'")
    
    impacted = []
    seen_symbols = set() # To prevent duplicate tickers

    # 1. Map Direct Companies (Confidence: 1.0)
    for company in state.get('companies', []):
        if company in COMPANY_TICKERS:
            ticker = COMPANY_TICKERS[company]
            if ticker not in seen_symbols:
                impacted.append({"symbol": ticker, "confidence": 1.0, "type": "direct"})
                seen_symbols.add(ticker)

    # 2. Map Sectors (Confidence: 0.7)
    for sector in state.get('sectors', []):
        if sector in SECTOR_TICKERS:
            for ticker in SECTOR_TICKERS[sector]:
                if ticker not in seen_symbols:
                    impacted.append({"symbol": ticker, "confidence": 0.7, "type": "sector"})
                    seen_symbols.add(ticker)

    # 3. Map Regulators (Confidence: 0.8)
    for regulator in state.get('regulators', []):
        if regulator.upper() == "RBI":
            # RBI impacts the whole banking index
            if "BANKNIFTY" not in seen_symbols:
                impacted.append({"symbol": "BANKNIFTY", "confidence": 0.8, "type": "regulatory"})
                seen_symbols.add("BANKNIFTY")

    state['impacted_stocks'] = impacted
    print(f"✅ Impacted Stocks: {state['impacted_stocks']}")
    
    return state