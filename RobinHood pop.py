from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

# create results df
result = pd.DataFrame(np.zeros((1, 4)), columns=['buyDip', 'fear', 'FOMO', 'takeProfit'])

# import saved csv of top 1% popular shares
dfCheck = pd.read_csv('usedStocks.csv')  # extracted from CheckStocks.py

# describe popularity of stocks (use breakpoint)
describe = dfCheck.maxPopul.describe()

# iterate through all shares
for idx, pathName in enumerate(dfCheck.fname):
    shareName = pathName.split('/')[1].split('.')[0]  # get share name
    shareTicker = yf.Ticker(shareName)

    # check if data exists
    if shareTicker.info['regularMarketPrice'] is None:
        continue

    # extract Close price
    hist = shareTicker.history(start="2018-05-02", end="2020-04-30")
    if hist.empty:
        continue
    hist.index = hist.index.date
    price = hist.Close

    # import one csv for popularity
    df = pd.read_csv(pathName)

    # adapt 'timestamp'
    df.timestamp = pd.to_datetime(df.timestamp, format='%Y-%m-%d %H:%M:%S')  # converting to datetime
    df = df.groupby(pd.Grouper(key='timestamp', freq='1d'))['users_holding'].mean(0).round(0).reset_index()  # daily
    df.set_index('timestamp', inplace=True)  # replace index
    df.index = df.index.date

    # JOIN popularity and price data on index. Weekends can be omitted, as no trade occurs there.
    merge = pd.merge(df, price, how='right', left_index=True, right_index=True)

    # explore merge visually to check for outliers
    if shareName == 'AAPL' and False:
        fig, axs = plt.subplots(3)
        axs[0].plot(x=merge.index, y=merge.Close)  # price
        axs[1].plot(x=merge.index, y=merge.users_holding)  # popularity
        axs[2].plt.scatter(x=merge.users_holding, y=merge.Close)  # price/popularity

    # missing values are ok, as consistency of time series is important.
    # else, use "merge = merge.dropna()" to drop missing values or do prediction for NAs.

    # Check for extreme prices changes
    dipParam = 0.03  # extreme change percent
    merge['priceChange'] = (merge['Close'] / merge['Close'].shift(1))-1
    merge.loc[merge.priceChange >= dipParam, 'priceDip'] = 'bullish'
    merge.loc[merge.priceChange <= -dipParam, 'priceDip'] = 'bearish'
    # To check: merge.loc[(merge.priceDip == 'bullish') | (merge.priceDip == 'bearish')]

    # Daily popularity change
    merge['popChange'] = (merge['users_holding'] / merge['users_holding'].shift(1))-1

    # buyDip - price down, pop up  # to check: merge.loc[(merge.userState == 'buyDip')]
    merge.loc[(merge.priceDip == 'bearish') & (merge.popChange >= dipParam), 'userState'] = 'buyDip'
    # fear - price down, pop down
    merge.loc[(merge.priceDip == 'bearish') & (merge.popChange <= -dipParam), 'userState'] = 'fear'
    # FOMO - price up, pop up
    merge.loc[(merge.priceDip == 'bullish') & (merge.popChange >= dipParam), 'userState'] = 'FOMO'
    # Take Profit - price up, pop down
    merge.loc[(merge.priceDip == 'bullish') & (merge.popChange <= -dipParam), 'userState'] = 'takeProfit'

    # Get results by counting
    result.iat[0, 0] = result.iat[0, 0] + merge.userState.str.count(r'buyDip').sum()
    result.iat[0, 1] = result.iat[0, 1] + merge.userState.str.count(r'fear').sum()
    result.iat[0, 2] = result.iat[0, 2] + merge.userState.str.count(r'FOMO').sum()
    result.iat[0, 3] = result.iat[0, 3] + merge.userState.str.count(r'takeProfit').sum()
    if idx == 90:
        break

filepath = Path('userBehaviour.csv')
filepath.parent.mkdir(parents=True, exist_ok=True)
result.to_csv('userBehaviour.csv', index=False)
print('done')
