# -*- coding: utf-8 -*-
"""
Created on Mon Aug 29 13:27:05 2022

@author: mimus
"""

import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.trades as trades
import pandas as pd
import matplotlib.pyplot as plt
import time
import decimal

#initiating API connection and defining trade parameters
token_path = "C:\\Users\\mimus\Desktop\Programming\\Algo tests\\oandademotoken.txt"
client = oandapyV20.API(access_token=open(token_path,'r').read(),environment="practice")
account_id = "101-002-22704369-001"


#defining strategy parameters
pairs = ['EUR_USD','GBP_USD','USD_CHF','AUD_USD','USD_CAD'] #currency pairs to be included in the strategy
#pairs = ['EUR_JPY','USD_JPY','AUD_JPY','AUD_USD','AUD_NZD','NZD_USD']
pos_size = 100
upward_sma_dir = {}
dnward_sma_dir = {}
for i in pairs:
    upward_sma_dir[i] = False
    dnward_sma_dir[i] = False


def stochastic(df,a,b,c):
    df['k']=((df['c'] - df['l'].rolling(a).min())/(df['h'].rolling(a).max()-df['l'].rolling(a).min()))*100
    df['K']=df['k'].rolling(b).mean() 
    df['D']=df['K'].rolling(c).mean()
    return df

def SMA(df,a,b):
    df['sma_fast']=df['c'].rolling(a).mean() 
    df['sma_slow']=df['c'].rolling(b).mean() 
    return df

def candles(instrument):
    params = {"count": 800,"granularity": "M5"} #granularity can be in seconds S5 - S30, minutes M1 - M30, hours H1 - H12, days D, weeks W or months M
    candles = instruments.InstrumentsCandles(instrument=instrument,params=params)
    client.request(candles)
    ohlc_dict = candles.response["candles"]
    ohlc = pd.DataFrame(ohlc_dict)
    ohlc_df = ohlc.mid.dropna().apply(pd.Series)
    ohlc_df["volume"] = ohlc["volume"]
    ohlc_df.index = ohlc["time"]
    ohlc_df = ohlc_df.apply(pd.to_numeric)
    return ohlc_df

def market_order(instrument,units,sl):
    account_id = "101-002-22704369-001"
    data = {
            "order": {
            "price": "",
            "stopLossOnFill": {
            "trailingStopLossOnFill": "GTC",
            "distance": str(sl)
                              },
            "timeInForce": "FOK",
            "instrument": str(instrument),
            "units": str(units),
            "type": "MARKET",
            "positionFill": "DEFAULT"
                    }
            }
    r = orders.OrderCreate(accountID=account_id, data=data)
    client.request(r)
    
def ATR(DF,n):
    df = DF.copy()
    df['H-L']=abs(df['h']-df['l'])
    df['H-PC']=abs(df['h']-df['c'].shift(1))
    df['L-PC']=abs(df['l']-df['c'].shift(1))
    df['TR']=df[['H-L','H-PC','L-PC']].max(axis=1,skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    #df['ATR'] = df['TR'].ewm(span=n,adjust=False,min_periods=n).mean()
    df2 = df.drop(['H-L','H-PC','L-PC'],axis=1)
    return round(df2["ATR"][-1],2)

def decimals(num):
    d = decimal.Decimal(str(num))
    if (abs(d.as_tuple().exponent)) == 2:
        return 2
    elif (abs(d.as_tuple().exponent)) == 3:
        return 3
    elif (abs(d.as_tuple().exponent)) == 4:
        return 4
    elif (abs(d.as_tuple().exponent)) == 5:
        return 5

def MACD(DF,a=26,b=12,c=9):
    df = DF.copy()
    df["ma_fast"] = df["c"].ewm(span=a, min_periods=a).mean()
    df["ma_slow"] = df["c"].ewm(span=b, min_periods=b).mean()
    df["macd"] = df["ma_fast"] - df["ma_slow"]
    df["signal"] = df["macd"].ewm(span=c, min_periods=c).mean()
    return df.loc[:,["macd","signal"]]

def ema(DF,a=9, b=21, c=50):
    df = DF.copy()
    df["EMA_9"] = df["c"].ewm(span=a, min_periods=a).mean()
    df["EMA_21"] = df["c"].ewm(span=b, min_periods=b).mean()
    df["EMA_50"] = df["c"].ewm(span=c, min_periods=c).mean()
    return df.loc[:,['EMA_9','EMA_21','EMA_50']]

def MACD_divergence(MACD, SIGNAL):
    if MACD < SIGNAL:
        if abs(MACD[-3]-SIGNAL[-3])>abs(MACD[-2]-SIGNAL[-2]) and\
            abs(MACD[-2]-SIGNAL[-2])>abs(MACD[-1]-SIGNAL[-1]):
            return True
    return False

def Boll_Band(DF, n=14):
    df = DF.copy()
    df["MB"] = df["c"].rolling(n).mean()
    df["UB"] = df["MB"] + 3*df["c"].rolling(n).std(ddof=0)
    df["LB"] = df["MB"] - 3*df["c"].rolling(n).std(ddof=0)
    df["BB_Width"] = df["UB"] - df["LB"]
    return df[["MB","UB","LB","BB_Width"]]

def trade_signal(df,curr):
    global upward_sma_dir, dnward_sma_dir
    signal = ""
    if df['sma_fast'][-1] > df['sma_slow'][-1] and df['sma_fast'][-2] < df['sma_slow'][-2] and\
        df["c"][-1] < df["UB"][-2] and\
        MACD_divergence(df['MACD'],df['SIGNAL']) == True:
        upward_sma_dir[curr] = True
        dnward_sma_dir[curr] = False
    if df['sma_fast'][-1] < df['sma_slow'][-1] and df['sma_fast'][-2] > df['sma_slow'][-2] and\
        df["c"][-1] > df["LB"][-2] and\
        MACD_divergence(df['MACD'],df['SIGNAL']) == True:
        upward_sma_dir[curr] = False
        dnward_sma_dir[curr] = True  
    if upward_sma_dir[curr] == True and min(df['K'][-1],df['D'][-1]) > 25 and max(df['K'][-2],df['D'][-2]) < 25:
        signal = "Buy"
    if dnward_sma_dir[curr] == True and min(df['K'][-1],df['D'][-1]) < 75 and max(df['K'][-2],df['D'][-2]) > 75:
        signal = "Sell"

    return signal

def main():
    global pairs
    try:
        r = trades.OpenTrades(accountID=account_id)
        open_trades = client.request(r)['trades']
        curr_ls = []
        for i in range(len(open_trades)):
            curr_ls.append(open_trades[i]['instrument'])
        pairs = [i for i in pairs if i not in curr_ls]
        for currency in pairs:
            print("analyzing ",currency)
            data = candles(currency)
            
            ohlc_df = stochastic(data,14,3,3)
            ohlc_df = SMA(ohlc_df,100,200)
            ohlc_df[["EMA_9","EMA_21","EMA_50"]] = ema(ohlc_df)
            ohlc_df[["MACD","SIGNAL"]] = MACD(ohlc_df)
            ohlc_df[["MB","UB","LB","BB_Width"]] = Boll_Band(ohlc_df)
            ohlc_df["ATR"] = ATR(ohlc_df,60)
            ohlc_df.dropna(inplace=True)
            
            
            signal = trade_signal(ohlc_df,currency)
            if signal == "Buy":
                market_order(currency,pos_size,ATR(ohlc_df,60))
                print("New long position initiated for ", currency)
            elif signal == "Sell":
                market_order(currency,-1*pos_size,ATR(ohlc_df,60))
                print("New short position initiated for ", currency)
    except:
        print("error encountered....skipping this iteration")


# Continuous execution        
starttime=time.time()
timeout = time.time() + 20*2*1  
while time.time() <= timeout:
    try:
        print("passthrough at ",time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        main()
        time.sleep(20 - ((time.time() - starttime) % 20.0)) # 20s interval between each new execution
    except KeyboardInterrupt:
        print('\n\nKeyboard exception received. Exiting.')
        exit()
