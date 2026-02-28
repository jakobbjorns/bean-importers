# Source https://github.com/tarioch/beancounttools/blob/master/src/tariochbctools/importers/nordigen/importer.py

#from datetime import date
#import datetime
from os import path

#import requests
import yaml
from splitwise import Splitwise

from beancount.core import amount, data
from beancount.core.number import D
# from beancount.ingest import importer
from dateutil.parser import parse
import beangulp

class HttpServiceException(Exception):
    pass


class SplitwiseImporter(beangulp.Importer):
    """An importer for Nordigen API (e.g. for Revolut)."""

    def identify(self, filepath:str):
        return filepath.endswith("splitwise.yaml")

    def account(self, filepath:str):
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        return config["asset_account"]

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        
        sObj = Splitwise(consumer_key=config["consumer_key"],consumer_secret=config["consumer_secret"],api_key=config["api_key"])

        entries = []

        current = sObj.getCurrentUser()
        print(current)
        gropus = sObj.getGroups()
        print(gropus)

        for group in config["groups"]:
            group_id = group["id"]
            assetAccount = group["asset_account"]
            if "tags" in group:
                tag = set(group["tags"])
            else:
                tag = data.EMPTY_SET

            group = sObj.getGroup(id=group_id)
            # print(group)
            expences = sObj.getExpenses(group_id=group_id,limit=1000,friend_id=current.id,visible=True)

            # print(expences)
            
            for index,expence in enumerate(expences):
                for user in expence.users:
                    if user.id == current.id:
                        break
                trxDate=parse(expence.date).date()
                currency = expence.currency_code
                paid_share = user.paid_share
                owed_share = user.owed_share
                net_balance = user.net_balance
                narration = expence.description
                meta = data.new_metadata(filepath, index)     
                entry = data.Transaction(
                    meta,
                    trxDate,
                    "*",
                    None,
                    narration,
                    tag,
                    data.EMPTY_SET,
                    [
                        data.Posting(
                            assetAccount,
                            amount.Amount(
                                -D(paid_share),
                                currency,
                            ),
                            None,
                            None,
                            None,
                            None,
                        ),
                        data.Posting(
                            assetAccount,
                            amount.Amount(
                                D(net_balance),
                                currency,
                            ),
                            None,
                            None,
                            None,
                            None,
                        )
                    ]
                )
                entries.append(entry)

        return entries
if __name__ == "__main__":
    
    # imp = apply_hooks(importer=SvkImporter(iban_dict))

    main = beangulp.Ingest(importers=[SplitwiseImporter()])
    main()