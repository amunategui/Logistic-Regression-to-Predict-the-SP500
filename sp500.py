from scipy import stats
import urllib
import ystockquote
import pandas as pd
import numpy as np
import statsmodels.api as sm
              
def GetAndPrepareMasterIndex(symbolname, startdate, enddate):
	marketdata = ystockquote.get_historical_prices(symbolname.upper(),startdate.replace('-',''), enddate.replace('-',''))
	data = pd.DataFrame(marketdata[1:],columns=marketdata[0])
	data['Close'] = data['Close'].astype(float)
	data['Date'] = data['Date'].astype(str)
	rows_list = []
	for x in reversed(range(0,len(data)-1)):
		direction = 0
		if data['Close'][x+1] < data['Close'][x]:
			direction = 1
																																																	   
		thelist = []
		thelist = [data['Date'][x+1],direction]
		rows_list.append(thelist)
																																																																   
	data =  pd.DataFrame(rows_list, columns = ['Date','Direction'])
	data = data.set_index('Date')
	return data
                              
def GetAndTransformSymbol(symbols, startdate, enddate, masterdata, BUFFER = 50, ROUNDING = 4):
                symindex = 0
                rows_list = []
                               
                for sym in symbols:
                                print (sym)
                                symindex += 1
                                buffercounter = 0
                 
                                try:
                                                marketdata = ystockquote.get_historical_prices(sym.upper(),startdate.replace('-',''), enddate.replace('-',''))
                                except urllib.error.HTTPError:
                                                print('HTTPError: HTTP Error 404: Not Found for', sym)
                                                continue
                                               
                                data = pd.DataFrame(marketdata[1:],columns=marketdata[0])
                                data['Open'] = data['Open'].astype(float)
                                data['High'] = data['High'].astype(float)
                                data['Low'] = data['Low'].astype(float)
                                data['Close'] = data['Close'].astype(float)
                                data['Date'] = data['Date'].astype(str)
                                data['Volume'] = data['Volume'].astype(int)
                                data = data.sort(['Date'],ascending=False)
                 
                                openarray = []
                                higharray = []   
                                lowarray = []
                                closearray = []
                                volumearray = []
                 
                                missingdate = False
                                # don't get last entry as data will not have a predicted result
                                for x in reversed(range(1,len(data)-1)):
                                                buffercounter += 1
                                                if data['Date'][x] not in masterdata.index:
                                                                print('Missing date %s for %s' % (data['Date'][x], sym))
                                                                missingdate = True
                                                                break
 
                                                openval = data['Open'][x] - data['Open'][x+1]
                                                openarray.append(openval)
                                 
                                                highval = data['High'][x] - data['High'][x+1]
                                                higharray.append(highval)
                                 
                                                lowval = data['Low'][x] - data['Low'][x+1]
                                                lowarray.append(lowval)
                                 
                                                closeval = data['Close'][x] - data['Close'][x+1]
                                                closearray.append(closeval)
                                               
                                                # scaled 1 to 4 ==> 1 for less than half, 2 less than previous, 4 more than last, 5 twice more than last, 3 equal
                                                last = data['Volume'][x+1]
                                                curr = data['Volume'][x]
                                                volumeval = 3
                                                if (curr * 2) < last:
                                                                volumeval = 1
                                                elif curr < last:
                                                                volumeval = 2
                                                elif curr > (last * 2):
                                                                volumeval = 4
                                                elif curr > last:
                                                                volumeval = 5
                                                               
                                                #print (data['Date'][x], curr, data['Date'][x+1], last, volumeval)
                                                #volumeval = 0 if (data['Volume'][x] - data['Volume'][x+1]) < 0 else 1
                                                #volumearray.append(volumeval)
                                               
                                                resultAtNextMarket = masterdata.ix[data['Date'][x]]['Direction']
                                 
                                                # let the std and z values build with enough data before learning
                                                if buffercounter < 20:
                                                                continue
                                                                                                 
                                                openchange = round(stats.zscore(openarray[-BUFFER:])[-1],ROUNDING)
                                                highchange = round(stats.zscore(higharray[-BUFFER:])[-1],ROUNDING)
                                                lowchange = round(stats.zscore(lowarray[-BUFFER:])[-1],ROUNDING)
                                                closechange = round(stats.zscore(closearray[-BUFFER:])[-1],ROUNDING)
                                                               
                                                thelist = []
                                                thelist = [data['Date'][x], symindex, openchange, highchange, lowchange, closechange, volumeval, resultAtNextMarket]
                                                rows_list.append(thelist)
 
                if not missingdate:
                                print('printing data')
                                data =  pd.DataFrame(rows_list, columns = ['Date','Symbol','O', 'H', 'L', 'C', 'V', 'R'])
                                #data = data.sort(['Date'],ascending=False)
                                #data = data.set_index('Date')
                                return data
                              
def GetFit(datatrains):
                train_cols = datatrain.columns[1:7]
                logit = sm.Logit(datatrain['R'], datatrain[train_cols])
                result = logit.fit()
                return result
 
totalfound = 0
totalattempts = 0
def MeasurePredictions(thefit, dataset):
	global totalfound, totalattempts
																	 
	found = 0.0
	missed = 0.0
   
	predictedtally = 0
	predictedcount = 0
	actualresult = 0
   
	count = 0
   
	dataset = dataset.sort('Date')
	olddatetomeasure = dataset['Date'][0]
	for p in dataset.iterrows():
		datetomeasure = p[1]['Date']
		#predicted = round(thefit.predict([p[1]['Symbol'], p[1]['O'], p[1]['H'], p[1]['L'], p[1]['C'], p[1]['V']]))
		predicted = round(thefit.predict([p[1]['Symbol'], p[1]['O'], p[1]['H'], p[1]['L'], p[1]['C'], p[1]['V']]))
	   
		if olddatetomeasure != datetomeasure:
			if predictedcount > 0:
				finalvotefordate = predictedtally / predictedcount
				#print (actualresult, finalvotefordate)
				if finalvotefordate >= abs(0.9):
					count += 1
					if (round(finalvotefordate) >= 0.75 and actualresult == 1) or (round(finalvotefordate) <= 0.75 and actualresult == 0):
						found += 1
					else:
						missed += 1
														   
			predictedtally = 0
			predictedcount = 0

		predictedtally += predicted
		predictedcount += 1
		actualresult =  p[1]['R']
					   
		olddatetomeasure = datetomeasure
	 
	if (found + missed) > 0: print ("%s accuracy:%f count:%f" % (datetomeasure, found/(found + missed), count))
	#print(("Matched = %f, Missed = %f, percent found: %f") % (found, missed, found/(found+missed)))
	#return result
 
if __name__ == '__main__':
                TRAINING_START_DATE = '1995-01-01'
                TRAINING_END_DATE = '2008-12-31'
                TRADING_START_DATE = '2009-01-01'
                TRADING_END_DATE = '2013-12-31'
                SYMBOLS_LIST_FILE = "sp5002012.txt"
                #symbols = ['INTC','MSFT','AAPL','SPY','ALTR']
                with open(SYMBOLS_LIST_FILE, 'r') as input:
                                symbols = (input.read().splitlines())
                symbols.append('SPY')
 
                masterdatatraining = GetAndPrepareMasterIndex('SPY',TRAINING_START_DATE,TRAINING_END_DATE)
                masterdatatrading = GetAndPrepareMasterIndex('SPY',TRADING_START_DATE,TRADING_END_DATE)
                datatrain = GetAndTransformSymbol(symbols,TRAINING_START_DATE,TRAINING_END_DATE, masterdatatraining)
                datatrading = GetAndTransformSymbol(symbols,TRADING_START_DATE,TRADING_END_DATE, masterdatatrading)
 
                thefit = GetFit(datatrain)
 
                MeasurePredictions(thefit, datatrading)