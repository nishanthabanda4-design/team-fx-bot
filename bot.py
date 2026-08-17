import requests
import pandas as pd

# Sheetbest URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- KUCOIN DATA FETCHING ---
def fetch_top_symbols(limit=100):
    url = "https://api.kucoin.com/api/v1/market/allTickers"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('code') == '200000':
            ticker_list = res['data']['ticker']
            usdt_pairs = [item for item in ticker_list if item['symbol'].endswith('-USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('volValue', 0)), reverse=True)
            return [item['symbol'] for item in usdt_pairs[:limit]]
    except Exception as e:
        print(f"Error: {e}")
    return ["BTC-USDT", "ETH-USDT", "SOL-USDT"]

def fetch_kucoin_klines(symbol, type_interval='15min'):
    url = f"https://api.kucoin.com/api/v1/market/candles?symbol={symbol}&type={type_interval}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('code') == '200000':
            raw_data = res['data']
            raw_data.reverse()
            df = pd.DataFrame(raw_data, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
            df[['close', 'high', 'low', 'volume']] = df[['close', 'high', 'low', 'volume']].astype(float)
            return df
    except Exception as e:
        return None
    return None

# --- INDICATORS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- MAIN ENGINE ---
def run_bot():
    symbols = fetch_top_symbols(50)
    
    for symbol in symbols:
        df = fetch_kucoin_klines(symbol)
        if df is None or len(df) < 50: continue
            
        df['rsi'] = calculate_rsi(df['close'])
        df['ema_short'] = df['close'].ewm(span=20).mean()
        df['ema_long'] = df['close'].ewm(span=50).mean()
        
        current_price = df['close'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        
        # Stricter Entry Logic
        signal_type = None
        strategy = ""
        analysis = ""
        
        # BUY Logic: Trend is UP + RSI < 35 (Oversold)
        if df['ema_short'].iloc[-1] > df['ema_long'].iloc[-1] and last_rsi < 35:
            signal_type = "BUY 🟢"
            strategy = "Smart Money Concepts (SMC) / ICT"
            analysis = "Price in uptrend, showing oversold conditions and liquidity sweep at recent low."
        
        # SELL Logic: Trend is DOWN + RSI > 65 (Overbought)
        elif df['ema_short'].iloc[-1] < df['ema_long'].iloc[-1] and last_rsi > 65:
            signal_type = "SELL 🔴"
            strategy = "Supply and Demand Zone Trading"
            analysis = "Price in downtrend, showing overbought RSI at resistance zone."

        if signal_type:
            # WIDER SL: Using 1.5% buffer for safety
            decimals = 4 if current_price < 1 else 2
            entry = round(current_price, decimals)
            
            if "BUY" in signal_type:
                sl = round(entry * 0.985, decimals) # 1.5% SL
                tp1 = round(entry * 1.03, decimals)  # 3% TP
                tp2 = round(entry * 1.05, decimals)  # 5% TP
            else:
                sl = round(entry * 1.015, decimals) # 1.5% SL
                tp1 = round(entry * 0.97, decimals)  # 3% TP
                tp2 = round(entry * 0.95, decimals)  # 5% TP
            
            payload = {
                "Pair": symbol.replace("-", ""),
                "Type": signal_type,
                "Entry": entry, "TP1": tp1, "TP2": tp2, "SL": sl,
                "Status": "ACTIVE ⏳", "Strategy": strategy, "Analysis": analysis,
                "Key": "VIP2026"
            }
            requests.post(SHEETBEST_URL, json=payload, timeout=10)
            print(f"Sent {signal_type} for {symbol} | Strategy: {strategy}")

if __name__ == "__main__":
    run_bot()
