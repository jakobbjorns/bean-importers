import click
import json
import os

from dotenv import load_dotenv

from nordigen import NordigenClient


@click.command()
@click.option('--output_dir', '-o',
              type=click.Path(file_okay=False, dir_okay=True, exists=True),
              default='.',
              help='Output directory.')
def main(output_dir):
    load_dotenv()

    client = NordigenClient(
        secret_id=os.getenv("NORDIGEN_SECRET_ID"),
        secret_key=os.getenv("NORDIGEN_SECRET_KEY")
    )

    # Generate access & refresh token
    client.generate_token()

    client.requisition.get_requisitions()

    account_list = json.loads(os.getenv("NORDIGEN_ACCOUNTS"))
    accounts_data = []
    for accountId in account_list:
        account = client.account_api(accountId)

        metadata = account.get_metadata()
        transactions = account.get_transactions()
        details = account.get_details()
        balances = account.get_balances()

        data = {
            "metadata": metadata,
            "details": details,
            "balances": balances,
            "transactions": transactions,
        }

        accounts_data.append(
            data
        )
        dest_filename = os.path.join(output_dir, f"{accountId}.json")

        with open(dest_filename, "w") as testfil:
            json.dump(data, testfil)


if __name__ == "__main__":
    main()
