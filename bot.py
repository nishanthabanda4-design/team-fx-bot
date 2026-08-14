import os
import requests
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- GOOGLE SHEETS SETUP ---
SPREADSHEET_ID = '14G42hY2e7oK7fT_S1wYqG_R8A6pT_x-fX5u3g2_Z-8'
SHEET_NAME = 'Signals'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds_json = os.environ.get('GCP_SA_KEY')

if creds_json:
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
else:
    print("WARNING: GCP_SA_KEY is missing!")
    sheet = None

# --- BYBIT API DATA FETCHING ---
def fetch_top_symbols(limit=150):
    """Bybit එකෙන් Volume එක වැඩිම USDT Pairs 150 ලබාගැනීම"""
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get('retCode') == 0:
            list_data = res['result']['list']
            # Turnover (Volume) එක අනුව Sort කිරීම
            usdt_pairs = [item for item in list_data if item['symbol'].endswith('USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('turnover24h', 0)), reverse=True)
            return [item['symbol'] for item in usdt_pairs[:limit]]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
    return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def fetch_bybit_klines(symbol, interval='15', limit=100):
    """Candle Data ලබාගැනීම"""
    url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get('retCode') == 0:
            list_data = res['result']['list']
            list_data.reverse()
            df = pd.DataFrame(list_data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df[['close', 'high', 'low', 'volume']] = df[['close', 'high', 'low', 'volume']].astype(float)
            return df
    except Exception as e:
        print(f"Error fetching candles for {symbol}: {e}")
    return None

# --- INDICATORS & STRATEGY ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

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
        
        # Simple Signal logic (RSI Oversold/Overbought)
        signal_type = None
        if last_rsi < 35:
            signal_type = "BUY"
        elif last_rsi > 65:
            signal_type = "SELL"
            
        if signal_type:
            signals_found += 1
            print(f"SUCCESS: {signal_type} Signal for {symbol} | Price: {current_price} | RSI: {round(last_rsi, 2)}")
            
            if sheet:
                try:
                    sheet.append_row([symbol, signal_type, float(current_price), round(float(last_rsi), 2)])
                except Exception as e:
                    print(f"Failed to append to Google Sheet: {e}")

    print(f"Finished! Total Signals Found: {signals_found}")

if __name__ == "__main__":
    run_bot()
