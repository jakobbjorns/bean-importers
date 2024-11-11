from enum import Flag, auto
import logging
import datetime
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.parser import parse
import beangulp
import json

logger = logging.getLogger(__name__)
logging.basicConfig(filename='nordigen_importer.log',
                    encoding='utf-8', 
                    level=logging.DEBUG)


class Modes(Flag):
    BOOKED = auto()
    PENDING = auto()
    BOOKED_BALANCE = auto()
    PENDING_BALANCE = auto()
    ALL = BOOKED | PENDING | BOOKED_BALANCE | PENDING_BALANCE


class NordigenJSONImporter(beangulp.Importer):
    """An importer for json files downladed by nordigen_downloader.py"""

    def __init__(self, iban_dict: dict, mode: Modes = Modes.BOOKED | Modes.BOOKED_BALANCE):
        self.iban_dict = iban_dict
        self.mode = mode

    def identify(self, file: str):
        if not file.endswith(".json"):
            return False

        with open(file, "r") as f:
            js = json.load(f)
        return "metadata" in js and "details" in js and "balances" in js and "transactions" in js

    def account(self, file):
        with open(file, "r") as f:
            js = json.load(f)

        iban = js['metadata']['iban']
        asset_account = self.iban_dict[iban]
        return asset_account

    def file_account(self, file):
        logging.debug("file_account %s", file)
        return self.account(file)

    def deduplicate(self, entries: data.List[data.NamedTuple], existing: data.List[data.NamedTuple]) -> None:

        existing_id_dict = self.generate_id_dict(existing)

        for entry in data.filter_txns(entries):
            try:
                entry_id = entry.meta["transactionId"]
            except KeyError:
                try:
                    entry_id = entry.meta["internalTransactionId"]
                except KeyError:
                    continue

            if entry_id in existing_id_dict:
                entry.meta[beangulp.extract.DUPLICATE] = existing_id_dict[entry_id]

    def generate_id_dict(self, existing_entries: data.Entries):
        d = {}
        existing_transactions = data.filter_txns(existing_entries)
        for trx in existing_transactions:
            if ("internalTransactionId" in trx.meta):
                d[trx.meta["internalTransactionId"]] = trx
            if ("transactionId" in trx.meta):
                d[trx.meta["transactionId"]] = trx
        return d

    def _extract_booked_transactions(self, filepath, assetAccount, js):
        transactions = sorted(
            js["transactions"]["transactions"]["booked"], key=lambda trx: trx["bookingDate"]
        )
        entries = []
        for index, trx in enumerate(transactions):
            metakv = {}
            if "transactionId" in trx:
                metakv["transactionId"] = trx["transactionId"]
            if "entryReference" in trx:
                metakv["entryReference"] = trx["entryReference"]
            if "creditorName" in trx:
                metakv["creditorName"] = trx["creditorName"]
            if "debtorName" in trx:
                metakv["debtorName"] = trx["debtorName"]
            if "internalTransactionId" in trx:
                internalTransactionId = trx["internalTransactionId"]
                metakv["internalTransactionId"] = internalTransactionId

            meta = data.new_metadata(filepath, index, metakv)
            trxDate = parse(trx["bookingDate"]).date()
            narration = ""

            if "remittanceInformationUnstructured" in trx:
                narration += trx["remittanceInformationUnstructured"]
                metakv["remittanceInformationUnstructured"] = trx["remittanceInformationUnstructured"]
            if "creditorName" in trx:
                narration = trx["creditorName"].strip()
            if "remittanceInformationUnstructuredArray" in trx:
                narration += " ".join(
                    trx["remittanceInformationUnstructuredArray"])
            entry = data.Transaction(
                meta,
                trxDate,
                "*",
                None,
                narration,
                data.EMPTY_SET,
                data.EMPTY_SET,
                [
                    data.Posting(
                        assetAccount,
                        amount.Amount(
                            D(str(trx["transactionAmount"]["amount"])),
                            trx["transactionAmount"]["currency"],
                        ),
                        None,
                        None,
                        None,
                        None,
                    ),
                ]
            )
            entries.append(entry)
        return entries

    def _extract_pending_transactions(self, filepath, assetAccount, js):
        transactions = js["transactions"]["transactions"]["pending"]

        entries = []
        for index, trx in enumerate(transactions):
            metakv = {}

            meta = data.new_metadata(filepath, index, metakv)
            trxDate = parse(trx['valueDate']).date()
            narration = ""

            if "remittanceInformationUnstructured" in trx:
                narration += trx["remittanceInformationUnstructured"]
                metakv["remittanceInformationUnstructured"] = trx["remittanceInformationUnstructured"]
            if "creditorName" in trx:
                narration = trx["creditorName"].strip()
            if "remittanceInformationUnstructuredArray" in trx:
                narration += " ".join(
                    trx["remittanceInformationUnstructuredArray"])
            entry = data.Transaction(
                meta,
                trxDate,
                "*",
                None,
                narration,
                {"PENDING"},
                data.EMPTY_SET,
                [
                    data.Posting(
                        assetAccount,
                        amount.Amount(
                            D(str(trx["transactionAmount"]["amount"])),
                            trx["transactionAmount"]["currency"],
                        ),
                        None,
                        None,
                        None,
                        None,
                    ),
                ]
            )
            entries.append(entry)
        return entries

    def _extract_pending_balance(self, filepath, assetAccount, js):

        bal_js = js["balances"]["balances"]

        for bal in bal_js:
            if bal["balanceType"] == "interimAvailable":
                balance = bal
                break

        bal_amount = amount.Amount(
            D(str(balance["balanceAmount"]["amount"])), balance["balanceAmount"]["currency"])
        try:
            bal_date = parse(balance['referenceDate']).date()

        except KeyError:
            bal_date = datetime.date.today()

        bal_date += datetime.timedelta(1)

        meta = data.new_metadata(filepath, 0)
        baltx = data.Balance(
            meta, bal_date, assetAccount, bal_amount, None, None)

        return baltx

    def _extract_booked_balance(self, filepath, assetAccount, js):
        sum_pending = amount.Amount(D("0"), "SEK")

        for pendning_transaction in js["transactions"]["transactions"]["pending"]:

            am = amount.Amount(
                D(str(
                    pendning_transaction["transactionAmount"]["amount"])),
                pendning_transaction["transactionAmount"]["currency"],
            )
            sum_pending = amount.add(sum_pending, am)

        bal_js = js["balances"]["balances"]

        for bal in bal_js:
            if bal["balanceType"] == "interimAvailable":
                balance = bal
                break

        bal_amount = amount.Amount(
            D(str(balance["balanceAmount"]["amount"])), balance["balanceAmount"]["currency"])
        bal_amount = amount.add(bal_amount, -sum_pending)
        try:
            bal_date = parse(balance['referenceDate']).date()

        except KeyError:
            bal_date = datetime.date.today()

        bal_date += datetime.timedelta(1)

        meta = data.new_metadata(filepath, 0)
        baltx = data.Balance(
            meta, bal_date, assetAccount, bal_amount, None, None)

        return baltx

    def extract(self, filepath: str, existing_entries: data.Entries) -> data.Entries:

        assetAccount = self.account(filepath)

        with open(filepath, "r") as f:
            js = json.load(f)

        entries = []

        if Modes.BOOKED in self.mode:
            transactions = self._extract_booked_transactions(
                filepath, assetAccount, js)
            entries.extend(transactions)

        if Modes.BOOKED_BALANCE in self.mode:
            transactions = self._extract_booked_balance(
                filepath, assetAccount, js)
            entries.append(transactions)

        if Modes.PENDING_BALANCE in self.mode:
            transactions = self._extract_pending_balance(
                filepath, assetAccount, js)
            entries.append(transactions)

        if Modes.PENDING in self.mode:
            transactions = self._extract_pending_transactions(
                filepath, assetAccount, js)
            entries.extend(transactions)

        return entries
