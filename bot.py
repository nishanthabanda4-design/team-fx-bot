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
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
    return None

# --- TECHNICAL ANALYSIS ENGINE ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period=50):
    return series.ewm(span=period, adjust=False).mean()

# --- MAIN ENGINE ---
def run_bot():
    symbols = fetch_top_symbols(100)
    print(f"Scanning {len(symbols)} coins with Price Action & Market Structure...")
    
    signals_found = 0
    for symbol in symbols:
        df = fetch_kucoin_klines(symbol)
        if df is None or len(df) < 50:
            continue
            
        df['rsi'] = calculate_rsi(df['close'])
        df['ema50'] = calculate_ema(df['close'], period=50)
        
        current_price = df['close'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        last_ema = df['ema50'].iloc[-1]
        
        # Swing Highs & Swing Lows (Support / Resistance / Market Structure)
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        signal_type = None
        
        # 1. Price Action & Trend Confirmation Rules
        # BUY: Oversold RSI (<38) AND Price Above EMA 50 OR Near Strong Support Zone
        if (last_rsi < 38 and current_price > last_ema) or (last_rsi < 30):
            signal_type = "BUY 🟢"
        # SELL: Overbought RSI (>62) AND Price Below EMA 50 OR Near Resistance Zone
        elif (last_rsi > 62 and current_price < last_ema) or (last_rsi > 70):
            signal_type = "SELL 🔴"
            
        if signal_type:
            signals_found += 1
            formatted_symbol = symbol.replace("-", "")
            decimals = 4 if current_price < 1 else 2
            entry = round(current_price, decimals)
            
            # --- MARKET STRUCTURE DYNAMIC TP & SL ---
            if signal_type == "BUY 🟢":
                sl = round(recent_low * 0.995, decimals)  # Support එකට පොඩ්ඩක් යටින් SL
                risk = entry - sl
                if risk <= 0: risk = entry * 0.015 # Safety fallback
                tp1 = round(entry + (risk * 1.5), decimals) # 1:1.5 Risk to Reward
                tp2 = round(entry + (risk * 2.5), decimals) # 1:2.5 Risk to Reward
            else: # SELL
                sl = round(recent_high * 1.005, decimals) # Resistance එකට පොඩ්ඩක් උඩින් SL
                risk = sl - entry
                if risk <= 0: risk = entry * 0.015
                tp1 = round(entry - (risk * 1.5), decimals)
                tp2 = round(entry - (risk * 2.5), decimals)
            
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

    print(f"Finished! Total Smart Signals Found: {signals_found}")

if __name__ == "__main__":
    run_bot()
