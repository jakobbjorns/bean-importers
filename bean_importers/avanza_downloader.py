import click
from avanza import Avanza
import os
import json
from dotenv import load_dotenv

from avanza.constants import HttpMethod

import datetime


class Avanza_jabs(Avanza):

    def get_positions_gdpr(self):
        """Get investment positions for all account"""
        ACCOUNTS_POSITIONS_PATH = "/_api/account-overview/gdpr/export/positions"
        return self._Avanza__call(HttpMethod.GET, ACCOUNTS_POSITIONS_PATH, return_content=True)


@click.command()
@click.option('--output_dir', '-o',
              type=click.Path(file_okay=False, dir_okay=True, exists=True),
              default='.',
              help='Output directory.')
@click.option('--from_date', '-f',
              type=click.DateTime(),
              default=None,
              help='Fetch transactions from this date.')
def main(output_dir, from_date):
    if from_date:
        from_date = from_date.date()
    load_dotenv()
    avanza = Avanza_jabs({
        'username': os.getenv("avanza_username"),
        'password': os.getenv("avanza_password"),
        'totpSecret': os.getenv("avanza_totpSecret")
    })
    download_transactions(avanza, output_dir, from_date)
    download_positions(avanza, output_dir)


def download_positions(avanza: Avanza_jabs, output_dir):
    s = avanza.get_positions_gdpr()

    datum = datetime.date.isoformat(datetime.date.today())

    pos_file = os.path.join(output_dir, f"{datum}_positioner.csv")

    with open(pos_file, "wb") as testfil:
        testfil.write(s)

def download_transactions(avanza: Avanza_jabs, output_dir, transactions_from=None):
    b = avanza.get_transactions_details(transactions_from=transactions_from,max_elements=100000)
    trx_file = os.path.join(output_dir, "ava_transactions.json")
    with open(trx_file, "w") as testfil:
        json.dump(b, testfil)


if __name__ == "__main__":
    main()
