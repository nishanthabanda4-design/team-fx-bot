import requests
import pandas as pd

# Sheetbest URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

# Request Headers
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- KUCOIN API DATA FETCHING ---
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
        print(f"Error fetching symbols from KuCoin: {e}")
    return ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT"]

def fetch_kucoin_klines(symbol, type_interval='15min'):
    url = f"https://api.kucoin.com/api/v1/market/candles?symbol={symbol}&type={type_interval}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        if res.get('code') == '200000':
            raw_data = res['data']
            raw_data.reverse()
            df = pd.DataFrame(raw_data, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
            df['close'] = df['close'].astype(float)
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

def calculate_ema(series, period=200):
    return series.ewm(span=period, adjust=False).mean()

# --- MAIN ENGINE ---
def run_bot():
    symbols = fetch_top_symbols(100)
    print(f"Scanning {len(symbols)} coins from KuCoin with strict rules...")
    
    signals_found = 0
    for symbol in symbols:
        df = fetch_kucoin_klines(symbol)
        # EMA 200 ගණනය කිරීමට අවම වශයෙන් කැන්ඩල් 200ක් අවශ්‍ය වේ
        if df is None or len(df) < 200:
            continue
            
        df['rsi'] = calculate_rsi(df['close'])
        df['ema200'] = calculate_ema(df['close'], period=200)
        
        current_price = df['close'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        last_ema = df['ema200'].iloc[-1]
        
        signal_type = None
        
        # තද කළ නව නීති (Strict Rules)
        # 1. BUY: RSI < 30 සහ මිල EMA 200 ට වඩා වැඩි විය යුතුය (Up-trend filter)
        if last_rsi < 30 and current_price > last_ema:
            signal_type = "BUY 🟢"
        # 2. SELL: RSI > 70 සහ මිල EMA 200 ට වඩා අඩු විය යුතුය (Down-trend filter)
        elif last_rsi > 70 and current_price < last_ema:
            signal_type = "SELL 🔴"
            
        if signal_type:
            signals_found += 1
            formatted_symbol = symbol.replace("-", "")
            decimals = 4 if current_price < 1 else 2
            entry = round(current_price, decimals)
            
            # TP සහ SL ගණනය කිරීම
            if signal_type == "BUY 🟢":
                tp1 = round(entry * 1.02, decimals) # +2%
                tp2 = round(entry * 1.04, decimals) # +4%
                sl  = round(entry * 0.98, decimals) # -2%
            else: # SELL
                tp1 = round(entry * 0.98, decimals) # -2%
                tp2 = round(entry * 0.96, decimals) # -4%
                sl  = round(entry * 1.02, decimals) # +2%
            
            payload = {
                "Pair": formatted_symbol,
                "Type": signal_type,
                "Entry": entry,
                "TP1": tp1,
                "TP2": tp2,
                "SL": sl,
                "Status": "ACTIVE ⏳",
                "Profit": "0%",
                "Key": "VIP2026"
            }
            try:
                res = requests.post(SHEETBEST_URL, json=payload, timeout=10)
                print(f"Sheetbest Status for {formatted_symbol}: {res.status_code} | Response: {res.text}")
            except Exception as e:
                print(f"Failed to send to Sheetbest: {e}")

    print(f"Finished! Total High-Quality Signals Found: {signals_found}")

if __name__ == "__main__":
    run_bot()
