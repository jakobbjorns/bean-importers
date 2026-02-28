from enum import Flag, auto
import logging
import datetime
from beancount.core import amount, data
from beancount.core.number import D
from dateutil.parser import parse
import beangulp

# import json
import pandas

logger = logging.getLogger(__name__)
logging.basicConfig(filename="amex_importer.log", encoding="utf-8", level=logging.DEBUG)


class Amex_Modes(Flag):
    BOOKED = auto()
    PENDING = auto()
    BOOKED_BALANCE = auto()
    PENDING_BALANCE = auto()
    ALL = BOOKED | PENDING | BOOKED_BALANCE | PENDING_BALANCE


class AmexXlxsImporter(beangulp.Importer):
    """An importer for xlsx files downladed by amex_downloader.py"""

    def __init__(
        self,
        account_name: str,
        mode: Amex_Modes = Amex_Modes.BOOKED | Amex_Modes.BOOKED_BALANCE,
        currency: str = "SEK",
    ):
        self.account_name = account_name
        self.mode = mode
        self.currency = currency

    def identify(self, file: str):
        if not file.endswith(".xlsx"):
            return False

        # with open(file, "r") as f:
        df = pandas.read_excel(file, engine="openpyxl")
        # js = json.load(f)

        return df.iloc[0, 0] == "Förberedd för"

    def account(self, file):
        return self.account_name

    def file_account(self, file):
        logging.debug("file_account %s", file)
        return self.account(file)

    def deduplicate(self, entries: data.Entries, existing: data.Entries) -> None:

        existing_id_dict = self.generate_id_dict(existing)

        for entry in data.filter_txns(entries):
            entry_id = entry.meta["referens"]

            if entry_id in existing_id_dict:
                entry.meta[beangulp.extract.DUPLICATE] = existing_id_dict[entry_id]

    def generate_id_dict(self, existing_entries: data.Entries):
        d = {}
        existing_transactions = data.filter_txns(existing_entries)
        for trx in existing_transactions:
            if "referens" in trx.meta:
                d[trx.meta["referens"]] = trx
            # if "transactionId" in trx.meta:
            #     d[trx.meta["transactionId"]] = trx
        return d

    def _extract_metadata(self, trx, key, meta_key, metakv):
        metadata = trx[key]
        if not (metadata != metadata):  # not nan
            metakv[meta_key] = metadata.replace("\n", " ")

    def _extract_booked_transactions(self, filepath, assetAccount):
        # transactions = sorted(
        #     js["transactions"]["transactions"]["booked"], key=lambda trx: trx["bookingDate"]
        # )
        df = pandas.read_excel(
            filepath, skiprows=[0, 1, 2, 3, 4], header=1, engine="openpyxl"
        )
        entries = []
        for row in df.iterrows():
            trx = row[1]
            index = row[0]
            metakv = {}
            # if "Referens" in trx:
            self._extract_metadata(trx, "Referens", "referens", metakv)
            self._extract_metadata(trx, "Beskrivning", "beskrivning", metakv)
            self._extract_metadata(trx, "Adress", "adress", metakv)
            self._extract_metadata(trx, "Land", "land", metakv)
            self._extract_metadata(trx, "Utökade specifikationer", "utokadBeskrivning", metakv)
            
            meta = data.new_metadata(filepath, index, metakv)
            trxDate = parse(trx["Datum"]).date()
            narration = trx["Visas på ditt kontoutdrag som"]

            # if "remittanceInformationUnstructured" in trx:
            #     narration += trx["remittanceInformationUnstructured"]
            #     metakv["remittanceInformationUnstructured"] = trx["remittanceInformationUnstructured"]
            # if "creditorName" in trx:
            #     narration = trx["creditorName"].strip()
            # if "remittanceInformationUnstructuredArray" in trx:
            #     narration += " ".join(
            #         trx["remittanceInformationUnstructuredArray"])
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
                            -D(str(trx["Belopp"])),
                            self.currency,
                        ),
                        None,
                        None,
                        None,
                        None,
                    ),
                ],
            )
            entries.append(entry)
        return entries

    def _extract_pending_transactions(self, filepath, assetAccount, js):
        # TODO: implement pending transactions extraction
        transactions = js["transactions"]["transactions"]["pending"]

        entries = []
        for index, trx in enumerate(transactions):
            metakv = {}

            meta = data.new_metadata(filepath, index, metakv)
            trxDate = parse(trx["valueDate"]).date()
            narration = ""

            if "remittanceInformationUnstructured" in trx:
                narration += trx["remittanceInformationUnstructured"]
                metakv["remittanceInformationUnstructured"] = trx[
                    "remittanceInformationUnstructured"
                ]
            if "creditorName" in trx:
                narration = trx["creditorName"].strip()
            if "remittanceInformationUnstructuredArray" in trx:
                narration += " ".join(trx["remittanceInformationUnstructuredArray"])
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
                ],
            )
            entries.append(entry)
        return entries

    def _extract_pending_balance(self, filepath, assetAccount, js):
        # TODO: implement pending balance extraction

        bal_js = js["balances"]["balances"]

        for bal in bal_js:
            if bal["balanceType"] == "interimAvailable":
                balance = bal
                break

        bal_amount = amount.Amount(
            D(str(balance["balanceAmount"]["amount"])),
            balance["balanceAmount"]["currency"],
        )
        try:
            bal_date = parse(balance["referenceDate"]).date()

        except KeyError:
            bal_date = datetime.date.today()

        bal_date += datetime.timedelta(1)

        meta = data.new_metadata(filepath, 0)
        baltx = data.Balance(meta, bal_date, assetAccount, bal_amount, None, None)

        return baltx

    def _extract_booked_balance(self, filepath, assetAccount, js):
        # TODO: implement booked balance extraction
        sum_pending = amount.Amount(D("0"), "SEK")

        for pendning_transaction in js["transactions"]["transactions"]["pending"]:

            am = amount.Amount(
                D(str(pendning_transaction["transactionAmount"]["amount"])),
                pendning_transaction["transactionAmount"]["currency"],
            )
            sum_pending = amount.add(sum_pending, am)

        bal_js = js["balances"]["balances"]

        for bal in bal_js:
            if bal["balanceType"] == "interimAvailable":
                balance = bal
                break

        bal_amount = amount.Amount(
            D(str(balance["balanceAmount"]["amount"])),
            balance["balanceAmount"]["currency"],
        )
        bal_amount = amount.add(bal_amount, -sum_pending)
        try:
            bal_date = parse(balance["referenceDate"]).date()

        except KeyError:
            bal_date = datetime.date.today()

        bal_date += datetime.timedelta(1)

        meta = data.new_metadata(filepath, 0)
        baltx = data.Balance(meta, bal_date, assetAccount, bal_amount, None, None)

        return baltx

    def extract(self, filepath: str, existing_entries: data.Entries) -> data.Entries:

        assetAccount = self.account(filepath)

        # data = pandas.read_excel(filepath, skiprows=[0, 1, 2, 3, 4], header=1)

        entries = []

        if Amex_Modes.BOOKED in self.mode:
            transactions = self._extract_booked_transactions(filepath, assetAccount)
            entries.extend(transactions)

        if Amex_Modes.BOOKED_BALANCE in self.mode:
            raise NotImplementedError("Booked balance extraction not implemented yet")
            transactions = self._extract_booked_balance(
                filepath, assetAccount, js
            )  # Transaktionssammanfattning
            entries.append(transactions)

        if Amex_Modes.PENDING_BALANCE in self.mode:
            raise NotImplementedError("Pending balance extraction not implemented yet")
            transactions = self._extract_pending_balance(filepath, assetAccount, js)
            entries.append(transactions)

        if Amex_Modes.PENDING in self.mode:
            raise NotImplementedError("Pending transactions extraction not implemented yet")
            transactions = self._extract_pending_transactions(
                filepath, assetAccount, js
            )
            entries.extend(transactions)

        return entries
