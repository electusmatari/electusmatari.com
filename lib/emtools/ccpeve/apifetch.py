import datetime
import logging

from django.db import transaction

from emtools.ccpeve.models import APIKey, LastUpdated, Division
from emtools.ccpeve.models import Balance, Transaction, Journal
from emtools.ccpeve.models import Asset, MarketOrder, IndustryJob

CORPORATIONS = ['Gradient']

def get_api_data():
    log = logging.getLogger('apifetch')
    for corpname in CORPORATIONS:
        try:
            key = APIKey.objects.get(name=corpname, active=True)
        except APIKey.DoesNotExist:
            log.warning("No active API key for corporation %s found" %
                        corpname)
            continue
        corp = key.corp()
        sheet = corp.CorporationSheet()
        if sheet.corporationName != corpname:
            log.warning("The API key %s is now for corporation %s" %
                        sheet.corporationName)
            continue
        transaction.commit()
        get_divisions(sheet.corporationID, corp, sheet)
        transaction.commit()
        get_balances(sheet.corporationID, corp)
        transaction.commit()
        get_assets(sheet.corporationID, corp)
        transaction.commit()
        get_industry(sheet.corporationID, corp)
        transaction.commit()
        get_market(sheet.corporationID, corp)
        transaction.commit()
        # DON'T fetch the journal/log, we do that in the gradient
        # module.
        continue
        for row in sheet.walletDivisions:
            get_journal(sheet.corporationID, corp, row.accountKey)
            transaction.commit()
            get_transactions(sheet.corporationID, corp, row.accountKey)
            transaction.commit()

def update_last_updated(ownerid, apiresult, apicall):
    timestamp = datetime.datetime.utcfromtimestamp(apiresult._meta.currentTime)
    obj, created = LastUpdated.objects.get_or_create(
        ownerid=ownerid,
        methodname=apicall,
        defaults={'apitimestamp': timestamp})
    if created:
        return timestamp
    elif obj.apitimestamp != timestamp:
        obj.apitimestamp = timestamp
        obj.save()
        return timestamp
    else:
        return None

def get_divisions(corpid, corp, sheet):
    apitimestamp = update_last_updated(corpid, sheet, '/corp/CorporationSheet')
    if apitimestamp is None:
        return
    divisions = dict((row.accountKey, row.description)
                     for row in sheet.divisions)
    wallets = dict((row.accountKey, row.description)
                   for row in sheet.walletDivisions)
    for accountKey in divisions:
        try:
            obj = Division.objects.get(ownerid=corpid, accountKey=accountKey)
        except Division.DoesNotExist:
            obj = Division(ownerid=corpid,
                           accountKey=accountKey)
        obj.apitimestamp = apitimestamp
        obj.hangarname = divisions[accountKey]
        obj.walletname = wallets[accountKey]
        obj.save()

def get_balances(corpid, corp):
    result = corp.AccountBalance()
    apitimestamp = update_last_updated(corpid, result, '/corp/AccountBalance')
    if apitimestamp is None:
        return
    for row in result.accounts:
        Balance.objects.create(apitimestamp=apitimestamp,
                               ownerid=corpid,
                               accountID=row.accountID,
                               accountKey=row.accountKey,
                               balance=str(row.balance))

def get_assets(corpid, corp):
    result = corp.AssetList()
    apitimestamp = update_last_updated(corpid, result, '/corp/AssetList')
    if apitimestamp is None:
        return
    def create_single_asset(row, locid, container):
        return Asset.objects.create(apitimestamp=apitimestamp,
                                    ownerid=corpid,
                                    itemID=row.itemID,
                                    typeID=row.typeID,
                                    locationID=locid,
                                    flag=row.flag,
                                    quantity=row.quantity,
                                    singleton=row.singleton,
                                    container=container,
                                    rawquantity=getattr(row, 'rawQuantity',
                                                        row.quantity))
    def create_assets(assets, locationID=None, container=None):
        for row in assets:
            if hasattr(row, 'locationID'):
                locid = row.locationID
            else:
                locid = locationID
            entry = create_single_asset(row, locid, container)
            if hasattr(row, 'contents'):
                create_assets(row.contents, locid, entry)
    create_assets(result.assets)

def get_industry(corpid, corp):
    result = corp.IndustryJobs()
    apitimestamp = update_last_updated(corpid, result, '/corp/IndustryJobs')
    if apitimestamp is None:
        return
    for row in result.jobs:
        job = IndustryJob(ownerid=corpid, apitimestamp=apitimestamp)
        for field in ['jobID',
                      'assemblyLineID', 'containerID', 'installedItemID',
                      'installedItemLocationID', 'installedItemQuantity',
                      'installedItemProductivityLevel',
                      'installedItemMaterialLevel',
                      'installedItemLicensedProductionRunsRemaining',
                      'outputLocationID', 'installerID', 'runs',
                      'licensedProductionRuns', 'installedInSolarSystemID',
                      'containerLocationID', 'materialMultiplier',
                      'charMaterialMultiplier', 'timeMultiplier',
                      'charTimeMultiplier', 'installedItemTypeID',
                      'outputTypeID', 'containerTypeID', 'installedItemCopy',
                      'completed', 'completedSuccessfully',
                      'installedItemFlag', 'outputFlag', 'activityID',
                      'completedStatus']:
            setattr(job, field, getattr(row, field))
        for field in ['installTime', 'beginProductionTime',
                      'endProductionTime', 'pauseProductionTime']:
            setattr(job, field,
                    datetime.datetime.utcfromtimestamp(getattr(row, field)))
        job.save()

def get_market(corpid, corp):
    result = corp.MarketOrders()
    apitimestamp = update_last_updated(corpid, result, '/corp/MarketOrders')
    if apitimestamp is None:
        return
    for row in result.orders:
        order = MarketOrder(ownerid=corpid, apitimestamp=apitimestamp)
        order.price = str(row.price)
        for field in ['orderID',
                      'charID', 'stationID', 'volEntered', 'volRemaining',
                      'minVolume', 'orderState', 'typeID', 'range',
                      'accountKey', 'duration', 'escrow', 'bid']:
            setattr(order, field, getattr(row, field))
        for field in ['issued']:
            setattr(order, field,
                    datetime.datetime.utcfromtimestamp(getattr(row, field)))
        order.save()

def get_journal(corpid, corp, accountKey):
    result = corp.WalletJournal(accountKey=accountKey,
                                rowCount=2560)
    apitimestamp = update_last_updated(corpid, result, '/corp/WalletJournal')
    if apitimestamp is None:
        return
    add_journal_entries(apitimestamp, corpid, accountKey, result.entries)
    while len(result.entries) == 2560:
        fromID = min(row.refID for row in result.entries)
        result = corp.WalletJournal(accountKey=accountKey,
                                    rowCount=2560,
                                    fromID=fromID)
        add_journal_entries(apitimestamp, corpid, accountKey, result.entries)
    
def add_journal_entries(apitimestamp, ownerid, accountKey, entries):
    for row in entries:
        try:
            Journal.objects.get(refID=row.refID)
            continue
        except Journal.DoesNotExist:
            Journal.objects.create(
                apitimestamp=apitimestamp,
                ownerid=ownerid,
                accountKey=accountKey,
                date=datetime.datetime.utcfromtimestamp(row.date),
                refID=row.refID,
                refTypeID=row.refTypeID,
                ownerName1=row.ownerName1,
                ownerID1=row.ownerID1,
                ownerName2=row.ownerName2,
                ownerID2=row.ownerID2,
                argName1=row.argName1,
                argID1=row.argID1,
                amount=str(row.amount),
                balance=str(row.balance),
                reason=row.reason,
                taxReceiverID=getattr(row, 'taxReceiverID', None),
                taxAmount=str(row.taxAmount) if hasattr(row, 'taxAmount') else None,
                )

def get_transactions(corpid, corp, accountKey):
    result = corp.WalletTransactions(accountKey=accountKey,
                                     rowCount=2560)
    apitimestamp = update_last_updated(corpid, result,
                                       '/corp/WalletTransactions')
    if apitimestamp is None:
        return
    add_transactions(apitimestamp, corpid, accountKey, result.transactions)
    while len(result.transactions) == 2560:
        fromID = min(row.transactionID for row in result.transactions)
        result = corp.WalletTransactions(accountKey=accountKey,
                                         rowCount=2560,
                                         fromID=fromID)
        add_transactions(apitimestamp, corpid, accountKey, result.transactions)

def add_transactions(apitimestamp, ownerid, accountKey, entries):
    for row in entries:
        try:
            Transaction.objects.get(transactionID=row.transactionID)
            continue
        except Transaction.DoesNotExist:
            Transaction.objects.create(
                apitimestamp=apitimestamp,
                ownerid=ownerid,
                accountKey=accountKey,
                transactionDateTime=datetime.datetime.utcfromtimestamp(
                    row.transactionDateTime),
                transactionID=row.transactionID,
                quantity=row.quantity,
                typeName=row.typeName,
                typeID=row.typeID,
                price=str(row.price),
                clientID=row.clientID,
                clientName=row.clientName,
                stationID=row.stationID,
                stationName=row.stationName,
                transactionType=row.transactionType,
                transactionFor=row.transactionFor,
                journalTransactionID=row.journalTransactionID)


        
