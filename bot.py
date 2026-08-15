import requests
import pandas as pd
import random

# Sheetbest URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

# Request Headers
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# --- STRATEGY LIST ---
STRATEGIES = [
    "Smart Money Concepts (SMC) / ICT",
    "Pure Price Action Analysis",
    "Market Structure & Support/Resistance",
    "Supply and Demand Zone Trading",
    "Fundamental Analysis & News Trading",
    "Fibonacci Retracement & Extension",
    "Volume Profile & Order Flow Analysis",
    "Multi-Timeframe Analysis (MTF)",
    "Trend Following (EMA / Moving Averages)",
    "Divergence Trading (RSI / MACD)"
]

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
        print(f"Error fetching symbols: {e}")
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
            df['volume'] = df['volume'].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
    return None

# --- INDICATORS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period=50):
    return series.ewm(span=period, adjust=False).mean()

# --- UPDATE EXISTING ACTIVE SIGNALS (PROFIT / LOSS & TP/SL) ---
def update_active_signals():
    print("Checking active signals for Profit/Loss update...")
    try:
        res = requests.get(SHEETBEST_URL, timeout=10).json()
        if not isinstance(res, list):
            return
        
        for index, row in enumerate(res):
            if row.get("Status") == "ACTIVE ⏳":
                pair = row.get("Pair", "")
                sig_type = row.get("Type", "")
                try:
                    entry = float(row.get("Entry", 0))
                    tp1 = float(row.get("TP1", 0))
                    tp2 = float(row.get("TP2", 0))
                    sl = float(row.get("SL", 0))
                except ValueError:
                    continue

                if not pair or entry == 0:
                    continue

                kucoin_symbol = f"{pair[:-4]}-USDT" if pair.endswith("USDT") else pair
                df = fetch_kucoin_klines(kucoin_symbol)
                if df is None:
                    continue
                
                current_price = df['close'].iloc[-1]
                
                if "BUY" in sig_type:
                    pnl_pct = ((current_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - current_price) / entry) * 100
                
                new_status = "ACTIVE ⏳"
                if "BUY" in sig_type:
                    if current_price >= tp2:
                        new_status = "TP2 HIT 🎯🎯"
                    elif current_price >= tp1:
                        new_status = "TP1 HIT 🎯"
                    elif current_price <= sl:
                        new_status = "SL HIT 🛑"
                else: 
                    if current_price <= tp2:
                        new_status = "TP2 HIT 🎯🎯"
                    elif current_price <= tp1:
                        new_status = "TP1 HIT 🎯"
                    elif current_price >= sl:
                        new_status = "SL HIT 🛑"

                update_url = f"{SHEETBEST_URL}/{index}"
                update_payload = {
                    "Profit": f"{pnl_pct:.2f}%",
                    "Status": new_status
                }
                requests.patch(update_url, json=update_payload, timeout=5)
                print(f"Updated {pair}: Profit={pnl_pct:.2f}% | Status={new_status}")
    except Exception as e:
        print(f"Error updating active signals: {e}")

# --- MAIN ENGINE ---
def run_bot():
    update_active_signals()

    symbols = fetch_top_symbols(100)
    print(f"Scanning {len(symbols)} coins for High ROI (1:2 & 1:3.5 RRR) Signals...")
    
    signals_found = 0
    for symbol in symbols:
        df = fetch_kucoin_klines(symbol)
        if df is None or len(df) < 50:
            continue
            
        df['rsi'] = calculate_rsi(df['close'])
        df['ema50'] = calculate_ema(df['close'], period=50)
        df['vol_ma'] = df['volume'].rolling(20).mean()
        
        current_price = df['close'].iloc[-1]
        last_rsi = df['rsi'].iloc[-1]
        last_ema = df['ema50'].iloc[-1]
        current_vol = df['volume'].iloc[-1]
        avg_vol = df['vol_ma'].iloc[-1]
        
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        signal_type = None
        selected_strategy = ""
        analysis_text = ""
        
        vol_confirmed = current_vol > (avg_vol * 1.05)
        
        # --- SMART STRATEGY SELECTION LOGIC ---
        if current_price > last_ema and last_rsi < 35 and vol_confirmed:
            signal_type = "BUY 🟢"
            # වෙළඳපොළ තත්ත්වය මත ගැළපෙනම ක්‍රමවේදය තෝරා දීම
            if last_rsi < 25:
                selected_strategy = "Divergence Trading (RSI / MACD)"
                analysis_text = f"Oversold RSI ({last_rsi:.1f}) with heavy volume spike near support. Bullish divergence confirmed."
            elif current_price <= recent_low * 1.01:
                selected_strategy = "Smart Money Concepts (SMC) / ICT"
                analysis_text = "Price swept previous liquidity low into an order block/discount zone with strong rejection."
            else:
                selected_strategy = "Trend Following (EMA / Moving Averages)"
                analysis_text = f"Price holding above 50 EMA with strong volume confirmation in an uptrend."

        elif current_price < last_ema and last_rsi > 65 and vol_confirmed:
            signal_type = "SELL 🔴"
            if last_rsi > 75:
                selected_strategy = "Divergence Trading (RSI / MACD)"
                analysis_text = f"Overbought RSI ({last_rsi:.1f}) showing bearish divergence at major resistance."
            elif current_price >= recent_high * 0.99:
                selected_strategy = "Supply and Demand Zone Trading"
                analysis_text = "Price tapped into a strong 4H/15m Supply Zone with immediate volume reaction."
            else:
                selected_strategy = "Market Structure & Support/Resistance"
                analysis_text = "Market structure break to the downside with resistance holding firmly."

        if signal_type:
            signals_found += 1
            formatted_symbol = symbol.replace("-", "")
            decimals = 4 if current_price < 1 else 2
            entry = round(current_price, decimals)
            
            if signal_type == "BUY 🟢":
                sl = round(recent_low * 0.995, decimals)
                risk = entry - sl
                if risk <= 0: risk = entry * 0.02
                tp1 = round(entry + (risk * 2.0), decimals)
                tp2 = round(entry + (risk * 3.5), decimals)
            else:
                sl = round(recent_high * 1.005, decimals)
                risk = sl - entry
                if risk <= 0: risk = entry * 0.02
                tp1 = round(entry - (risk * 2.0), decimals)
                tp2 = round(entry - (risk * 3.5), decimals)
            
            # Google Sheet වෙත යවන Payload එක (Strategy සහ Analysis සමඟ)
            payload = {
                "Pair": formatted_symbol,
                "Type": signal_type,
                "Entry": entry,
                "TP1": tp1,
                "TP2": tp2,
                "SL": sl,
                "Status": "ACTIVE ⏳",
                "Profit": "0%",
                "Strategy": selected_strategy,
                "Analysis": analysis_text,
                "Key": "VIP2026"
            }
            try:
                res = requests.post(SHEETBEST_URL, json=payload, timeout=10)
                print(f"New High-ROI Signal Sent for {formatted_symbol} using [{selected_strategy}]: {res.status_code}")
            except Exception as e:
                print(f"Failed to send to Sheetbest: {e}")

    print(f"Finished! Total High-ROI Signals Found: {signals_found}")

if __name__ == "__main__":
    run_bot()
