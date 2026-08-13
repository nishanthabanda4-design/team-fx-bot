import requests
import pandas as pd
import ta

# SheetBest API URL
SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

# Scan කරන Crypto Coins
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT']

def get_binance_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', '_', '_', '_', '_', '_', '_'])
    df['close'] = df['close'].astype(float)
    return df

def analyze_and_signal():
    for symbol in SYMBOLS:
        try:
            df = get_binance_data(symbol)
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)

            last = df.iloc[-1]

            # High Accuracy Condition (EMA 200 Trend + RSI Oversold)
            if last['close'] > last['ema200'] and last['rsi'] < 30:
                entry = round(last['close'], 2)
                sl = round(entry * 0.985, 2)  # 1.5% SL
                tp1 = round(entry * 1.02, 2)  # 2.0% TP1
                tp2 = round(entry * 1.04, 2)  # 4.0% TP2

                payload = {
                    "Pair": symbol,
                    "Type": "BUY",
                    "Entry": entry,
                    "TP1": tp1,
                    "TP2": tp2,
                    "SL": sl,
                    "Status": "ACTIVE ⏳",
                    "Profit": "0%",
                    "Key": "VIP2026"
                }

                # Auto Push to SheetBest
                requests.post(SHEETBEST_URL, json=payload)
                print(f"Signal Generated for {symbol}!")
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

if __name__ == "__main__":
    analyze_and_signal()
