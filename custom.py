from dwm import _CollectHistory_, _CollectHistoryAgg_
import re

## Define custom functions here

#################################
## TEMPLATE

def __TEMPLATEFCN__(data, histObj):

    # data is a single record (dict)
    # do transformations to data
    # capture value changes
    change = _CollectHistory_(lookupType='__TEMPLATEFCN__', fromVal='oldvalue', toVal='newvalue')

    histObjUpd = _CollectHistoryAgg_(contactHist=histObj, fieldHistObj=change, fieldName='fieldThatWasChanged')

    # return data and history
    return data, histObj

#################################
## CleanZipcodeUS

## This function is for cleaning the zipPostalCode field where country == 'US'
# It gets the first string of numbers ('20194-2245' becomes '20194')
# then strips down to the first 5 digits ('123456788' becomes '12345')
# then adds any leading 0s, usually removed due to excel formatting ('223' becomes '00223')

def CleanZipcodeUS(data, histObj):

    if 'zipPostalCode' not in data.keys():
        return data, histObj

    zipOld = data['zipPostalCode']

    zipNew = zipOld

    if data['country']=='US' and zipNew!='':

        zipNew = re.split('[^0-9]', zipNew)[0]
        zipNew = zipNew[:5]
        zipNew = zipNew.zfill(5)

        data['zipPostalCode'] = zipNew

    change = _CollectHistory_(lookupType='UDF-CleanZipcodeUS', fromVal=zipOld, toVal=zipNew)

    histObjUpd = _CollectHistoryAgg_(contactHist=histObj, fieldHistObj=change, fieldName='zipPostalCode')

    return data, histObj

#################################
## CleanAnnualRevenue
# 1. Try converting string to int
#   - if successful, group into one of the buckets
# 2. Try replacing any words with spaces , then see how many strings of numbers there are
#   - if 2 number strings, round into the closest upper bucket

def CleanAnnualRevenue(data, histObj):

    annualRevenueOld = data['annualRevenue']

    annualRevenueNew = annualRevenueOld

    argood = ['Less than $1 mil', '$1 mil to less than $5 mil', '$5 mil to less than $10 mil', '$10 mil to less than $25 mil', '$25 mil to less than $50 mil',
              '$50 mil to less than $100 mil', '$100 mil to less than $250 mil', '$250 mil to less than $500 mil', '$500 mil to less than $1 bil', '$1 bil and above']

    if annualRevenueNew not in argood and annualRevenueNew!='':

        try:
            annualRevenueNew = int(annualRevenueNew.replace(',', '').replace('$', ''))
            if annualRevenueNew < 1000000:
                annualRevenueNew = 'Less than $1 mil'
            elif annualRevenueNew >= 1000000 and annualRevenueNew < 5000000:
                annualRevenueNew = '$1 mil to less than $5 mil'
            elif annualRevenueNew >= 5000000 and annualRevenueNew < 10000000:
                annualRevenueNew = '$5 mil to less than $10 mil'
            elif annualRevenueNew >= 10000000 and annualRevenueNew < 25000000:
                annualRevenueNew = '$10 mil to less than $25 mil'
            elif annualRevenueNew >= 25000000 and annualRevenueNew < 50000000:
                annualRevenueNew = '$25 mil to less than $50 mil'
            elif annualRevenueNew >= 50000000 and annualRevenueNew < 100000000:
                annualRevenueNew = '$50 mil to less than $100 mil'
            elif annualRevenueNew >= 100000000 and annualRevenueNew < 250000000:
                annualRevenueNew = '$100 mil to less than $250 mil'
            elif annualRevenueNew >= 250000000 and annualRevenueNew < 500000000:
                annualRevenueNew = '$250 mil to less than $500 mil'
            elif annualRevenueNew >= 500000000 and annualRevenueNew < 1000000000:
                annualRevenueNew = '$500 mil to less than $1 bil'
            else:
                annualRevenueNew = '$1 bil and above'
        except:
            pass

        data['annualRevenue'] = annualRevenueNew

    change = _CollectHistory_(lookupType='UDF-CleanAnnualRevenue', fromVal=annualRevenueOld, toVal=annualRevenueNew)

    histObjUpd = _CollectHistoryAgg_(contactHist=histObj, fieldHistObj=change, fieldName='annualRevenue')

    # return data and history
    return data, histObj
