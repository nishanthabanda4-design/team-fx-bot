import requests
import pandas as pd
import numpy as np
import ta

SHEETBEST_URL = "https://api.sheetbest.com/sheets/3d6fa76e-4f3b-46f9-befd-a0339fbd4af8"

# 150 Coins Fallback List
FALLBACK_150_COINS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'SUIUSDT', 'LINKUSDT',
    'PEPEUSDT', 'NEARUSDT', 'SHIBUSDT', 'SUIUSDT', 'LTCUSDT', 'DOTUSDT', 'APTUSDT', 'BCHUSDT', 'UNIUSDT', 'ICPUSDT',
    'FETUSDT', 'RENDERUSDT', 'TAOUSDT', 'ARBUSDT', 'OPUSDT', 'FLOKIUSDT', 'TIAUSDT', 'WIFUSDT', 'SEIUSDT', 'INJUSDT',
    'STXUSDT', 'FILUSDT', 'TRXUSDT', 'GALAUSDT', 'ETCUSDT', 'RUNEUSDT', 'ORDIUSDT', 'BONKUSDT', 'ATOMUSDT', 'CRVUSDT',
    'FTMUSDT', 'IMXUSDT', 'GRTUSDT', 'LDOUSDT', 'EGLDUSDT', 'THETAUSDT', 'JUPUSDT', 'AAVEUSDT', 'KASUSDT', 'PYTHUSDT',
    'PENDLEUSDT', 'ENSUSDT', 'NOTUSDT', 'ONDOUSDT', 'WLDUSDT', 'STRKUSDT', 'POCATUSDT', 'STRKUSDT', 'AXSUSDT', 'SANDUSDT',
    'MANAUSDT', 'EOSUSDT', 'FLOWUSDT', 'SNXUSDT', 'NEOUSDT', 'XMRUSDT', 'MKRUSDT', 'COMPUSDT', 'DYDXUSDT', 'CHZUSDT',
    'MINAUSDT', 'GMXUSDT', 'KAVAUSDT', 'ZECUSDT', 'IOTAUSDT', 'DASHUSDT', '1INCHUSDT', 'HOTUSDT', 'AUDIOUSDT', 'BATUSDT',
    'QTUMUSDT', 'OMGUSDT', 'ZILUSDT', 'ANKRUSDT', 'RVNUSDT', 'ENJUSDT', 'ALGOUSDT', 'ONEUSDT', 'WAVESUSDT', 'ONTUSDT',
    'ICXUSDT', 'SKLUSDT', 'CELOUSDT', 'BANDUSDT', 'STORJUSDT', 'KSMUSDT', 'BLZUSDT', 'GLMRUSDT', 'WOOUSDT', 'MAGICUSDT',
    'ASTRUSDT', 'API3USDT', 'SSVUSDT', 'CFXUSDT', 'ACHUSDT', 'IDUSDT', 'ARBUSDT', 'RDNTUSDT', 'EDUUSDT', 'SUIUSDT',
    'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT', 'WLDUSDT', 'SEIUSDT', 'CYBERUSDT', 'BIGTIMEUSDT', 'MEMEUSDT', 'TOKENUSDT', 'BEAMXUSDT',
    'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT', 'DYMUSDT', 'RONUSDT',
    'PIXELUSDT', 'STRKUSDT', 'PORTALUSDT', 'AXLUSDT', 'AEVOUSDT', 'NEARUSDT', 'BOMEUSDT', 'ETHFIUSDT', 'ENAUSDT', 'WUSDT',
    'TNSRUSDT', 'SAGAUSDT', 'OMNIUSDT', 'REZUSDT', 'BBUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'LISTAUSDT'
]

def get_top_volume_usdt_pairs(limit=150):
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).json()
        
        if isinstance(res, list):
            usdt_pairs = [
                item for item in res 
                if isinstance(item, dict) and item.get('symbol', '').endswith('USDT') 
                and not any(x in item.get('symbol', '') for x in ['UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT'])
            ]
            usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            fetched_symbols = [item['symbol'] for item in usdt_pairs[:limit]]
            if len(fetched_symbols) >= limit:
                return fetched_symbols
    except Exception as e:
        print(f"Fetch error: {e}")
        
    print("Using Fallback 150 Coins List...")
    return FALLBACK_150_COINS[:limit]

SYMBOLS = get_top_volume_usdt_pairs(150)

def get_binance_data(symbol, interval='15m', limit=150):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers, timeout=10)
    data = res.json()
    
    if not isinstance(data, list) or len(data) < 50:
        return None
        
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', '_', '_', '_', '_', '_', '_'])
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def analyze_institutional_setup():
    print(f"Scanning {len(SYMBOLS)} Most Traded Coins...")
    
    for symbol in SYMBOLS:
        try:
            # 1H Trend Data
            df_1h = get_binance_data(symbol, interval='1h', limit=150)
            if df_1h is None or len(df_1h) < 100:
                continue
                
            df_1h['ema200'] = ta.trend.ema_indicator(df_1h['close'], window=100)
            trend_1h = "BULLISH" if df_1h['close'].iloc[-1] > df_1h['ema200'].iloc[-1] else "BEARISH"

            # 15m Execution Data
            df = get_binance_data(symbol, interval='15m', limit=100)
            if df is None or len(df) < 30:
                continue
            
            df['vol_ma'] = df['volume'].rolling(window=20).mean()

            recent_high = df['high'].iloc[-20:-2].max()
            recent_low = df['low'].iloc[-20:-2].min()

            last = df.iloc[-1]
            prev = df.iloc[-2]

            sweep_buy = (df['low'].iloc[-3:-1].min() < recent_low) and (prev['close'] > recent_low)
            choch_buy = last['close'] > prev['high']
            
            sweep_sell = (df['high'].iloc[-3:-1].max() > recent_high) and (prev['close'] < recent_high)
            choch_sell = last['close'] < prev['low']

            volume_spike = last['volume'] > (last['vol_ma'] * 1.2)

            fib_0618_buy = last['close'] <= (recent_high - (recent_high - recent_low) * 0.382)
            fib_0618_sell = last['close'] >= (recent_low + (recent_high - recent_low) * 0.382)

            # BUY Signal
            if (trend_1h == "BULLISH") and sweep_buy and choch_buy and volume_spike and fib_0618_buy:
                entry = round(last['close'], 4 if last['close'] < 1 else 2)
                sl = round(recent_low * 0.998, 4 if last['close'] < 1 else 2)
                risk = max(entry - sl, 0.0001)
                
                tp1 = round(entry + (risk * 2.0), 4 if last['close'] < 1 else 2)
                tp2 = round(entry + (risk * 3.5), 4 if last['close'] < 1 else 2)

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
                print(f"SUCCESS: Buy Signal Generated for {symbol}!")

            # SELL Signal
            elif (trend_1h == "BEARISH") and sweep_sell and choch_sell and volume_spike and fib_0618_sell:
                entry = round(last['close'], 4 if last['close'] < 1 else 2)
                sl = round(recent_high * 1.002, 4 if last['close'] < 1 else 2)
                risk = max(sl - entry, 0.0001)
                
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
                print(f"SUCCESS: Sell Signal Generated for {symbol}!")

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

if __name__ == "__main__":
    analyze_institutional_setup()
