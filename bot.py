import requests
import pandas as pd

# Sheetbest URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

# Request Headers (Bybit Block වීම වැළැක්වීමට)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- BYBIT API DATA FETCHING ---
def fetch_top_symbols(limit=150):
    """Bybit එකෙන් 24h Turnover (Volume) එක වැඩිම USDT Pairs ලබාගැනීම"""
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('retCode') == 0:
            list_data = res['result']['list']
            usdt_pairs = [item for item in list_data if item['symbol'].endswith('USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
            return [item['symbol'] for item in usdt_pairs[:limit]]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]

def fetch_bybit_klines(symbol, interval='15', limit=100):
    """Bybit එකෙන් Candle Data ලබාගැනීම"""
    url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('retCode') == 0:
            list_data = res['result']['list']
            list_data.reverse()
            df = pd.DataFrame(list_data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df[['close', 'high', 'low', 'volume']] = df[['close', 'high', 'low', 'volume']].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
    return None

# --- TECHNICAL INDICATORS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- MAIN ENGINE ---
def run_bot():
    symbols = fetch_top_symbols(150)
    print(f"Scanning {len(symbols)} coins from Bybit...")
    
    signals_found = 0
    for symbol in symbols:
        df = fetch_bybit_klines(symbol)
        if df is None or len(df) < 50:
            continue
            
        df['rsi'] = calculate_rsi(df['close'])
        current_price = df['close'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        
        signal_type = None
        if last_rsi < 35:
            signal_type = "BUY 🟢"
        elif last_rsi > 65:
            signal_type = "SELL 🔴"
            
        if signal_type:
            signals_found += 1
            entry = round(current_price, 4 if current_price < 1 else 2)
            
            print(f"SUCCESS: {signal_type} Signal for {symbol} | Price: {entry} | RSI: {round(last_rsi, 2)}")
            
            payload = {
                "Pair": symbol,
                "Type": signal_type,
                "Entry": entry,
                "RSI": round(float(last_rsi), 2),
                "Status": "ACTIVE ⏳",
                "Key": "VIP2026"
            }
            try:
                requests.post(SHEETBEST_URL, json=payload, timeout=10)
            except Exception as e:
                print(f"Failed to send to Sheetbest: {e}")

    print(f"Finished! Total Signals Found: {signals_found}")

if __name__ == "__main__":
    run_bot()
