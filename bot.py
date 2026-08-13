import requests
import pandas as pd
import numpy as np
import ta

# SheetBest API URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

def get_top_volume_usdt_pairs(limit=50):
    """
    Binance එකේ ඒ මොහොතේ Trade Volume එක වැඩිම (Traders ලා වැඩිපුරම Trade කරන)
    Top USDT Pairs auto-fetch කරගැනීම.
    """
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=10).json()
        
        # USDT Pairs පමණක් තෝරාගැනීම (Leveraged tokens අයින් කරයි)
        usdt_pairs = [
            item for item in res 
            if item['symbol'].endswith('USDT') 
            and not any(x in item['symbol'] for x in ['UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT'])
        ]
        
        # 24h Quote Volume එක අනුව Sort කිරීම
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        # Top 50 highest volume symbols
        top_symbols = [item['symbol'] for item in usdt_pairs[:limit]]
        return top_symbols
    except Exception as e:
        print(f"Error fetching top pairs: {e}")
        # Default Coins Fallback List
        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'LINKUSDT', 'SUIUSDT']

# Binance එකේ Trade Volume එක වැඩිම Top 50 Coins Auto Fetch වෙයි
SYMBOLS = get_top_volume_usdt_pairs(limit=50)

def get_binance_data(symbol, interval='15m', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url, timeout=10).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', '_', '_', '_', '_', '_', '_'])
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def analyze_institutional_setup():
    print(f"Scanning Top {len(SYMBOLS)} Most Traded Coins...")
    
    for symbol in SYMBOLS:
        try:
            # 1. Multi-Timeframe Analysis (MTF) - 1H Trend Direction
            df_1h = get_binance_data(symbol, interval='1h', limit=100)
            df_1h['ema200'] = ta.trend.ema_indicator(df_1h['close'], window=200)
            trend_1h = "BULLISH" if df_1h['close'].iloc[-1] > df_1h['ema200'].iloc[-1] else "BEARISH"

            # 2. 15m Execution Timeframe Data
            df = get_binance_data(symbol, interval='15m', limit=100)
            
            # Indicators Calculation
            df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['macd_diff'] = ta.trend.macd_diff(df['close'])
            df['vol_ma'] = df['volume'].rolling(window=20).mean()

            # Market Structure (Swing Highs / Lows)
            recent_high = df['high'].iloc[-20:-2].max()
            recent_low = df['low'].iloc[-20:-2].min()

            last = df.iloc[-1]
            prev = df.iloc[-2]

            # Strategy Calculations
            # A. SMC & Price Action: Liquidity Sweep + CHoCH
            sweep_buy = (df['low'].iloc[-3:-1].min() < recent_low) and (prev['close'] > recent_low)
            choch_buy = last['close'] > prev['high']
            
            sweep_sell = (df['high'].iloc[-3:-1].max() > recent_high) and (prev['close'] < recent_high)
            choch_sell = last['close'] < prev['low']

            # B. Volume & Order Flow: Volume Spike
            volume_spike = last['volume'] > (last['vol_ma'] * 1.3)

            # C. Supply / Demand Zone + Fib Retracement Confirmation
            fib_0618_buy = last['close'] <= (recent_high - (recent_high - recent_low) * 0.382)
            fib_0618_sell = last['close'] >= (recent_low + (recent_high - recent_low) * 0.382)

            # --- 🟢 HIGH ACCURACY BULLISH ENTRY (BUY) ---
            if (trend_1h == "BULLISH") and sweep_buy and choch_buy and volume_spike and fib_0618_buy:
                entry = round(last['close'], 4 if last['close'] < 1 else 2)
                sl = round(recent_low * 0.998, 4 if last['close'] < 1 else 2)
                risk = entry - sl
                
                # Fibonacci Extensions for Targets
                tp1 = round(entry + (risk * 2.0), 4 if last['close'] < 1 else 2)  # 1:2 R:R
                tp2 = round(entry + (risk * 3.5), 4 if last['close'] < 1 else 2)  # 1:3.5 R:R

                payload = {
                    "Pair": symbol,
                    "Type": "BUY 🟢 (SMC/ICT)",
                    "Entry": entry,
                    "TP1": tp1,
                    "TP2": tp2,
                    "SL": sl,
                    "Status": "ACTIVE ⏳",
                    "Profit": "0%",
                    "Key": "VIP2026"
                }
                requests.post(SHEETBEST_URL, json=payload)
                print(f"Institutional Buy Signal Generated for {symbol}!")

            # --- 🔴 HIGH ACCURACY BEARISH ENTRY (SELL) ---
            elif (trend_1h == "BEARISH") and sweep_sell and choch_sell and volume_spike and fib_0618_sell:
                entry = round(last['close'], 4 if last['close'] < 1 else 2)
                sl = round(recent_high * 1.002, 4 if last['close'] < 1 else 2)
                risk = sl - entry
                
                tp1 = round(entry - (risk * 2.0), 4 if last['close'] < 1 else 2)
                tp2 = round(entry - (risk * 3.5), 4 if last['close'] < 1 else 2)

                payload = {
                    "Pair": symbol,
                    "Type": "SELL 🔴 (SMC/ICT)",
                    "Entry": entry,
                    "TP1": tp1,
                    "TP2": tp2,
                    "SL": sl,
                    "Status": "ACTIVE ⏳",
                    "Profit": "0%",
                    "Key": "VIP2026"
                }
                requests.post(SHEETBEST_URL, json=payload)
                print(f"Institutional Sell Signal Generated for {symbol}!")

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

if __name__ == "__main__":
    analyze_institutional_setup()
