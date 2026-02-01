import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import time

from dotenv import load_dotenv
import os

from xvfbwrapper import Xvfb
from pathlib import Path
import click


@click.command()
@click.option(
    "--output_dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    default=".",
    help="Output directory.",
)
def main(output_dir):

    with Xvfb():

        downloads_path = str(Path.home() / "Downloads")

        download_dir_files = os.listdir(downloads_path)

        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--start-maximized")
        options.add_argument("--user-data-dir=selenum-amex")
        # options.add_argument("--headless=new")
        prefs = {"download.default_directory": "import_files"}
        options.add_experimental_option("prefs", prefs)

        driver = uc.Chrome(options=options, version_main=144)

        load_dotenv()
        try:
            # Gå till Amex inloggningssida
            driver.get("https://www.americanexpress.com/sv-se/")

            # Vänta lite så att sidan laddar
            time.sleep(1)
            try:
                driver.find_element(
                    By.ID, "user-consent-management-granular-banner-accept-all-button"
                ).click()

            except NoSuchElementException:
                pass

            # input()
            driver.find_element(By.ID, "gnav_login").click()

            time.sleep(5)

            # Hitta fält för användarnamn
            username_field = driver.find_element(By.ID, "eliloUserID")  # Exempel-ID
            username_field.send_keys(os.getenv("amex_username"))

            # Hitta fält för lösenord
            password_field = driver.find_element(By.ID, "eliloPassword")  # Exempel-ID
            password_field.send_keys(os.getenv("amex_password"))

            # Klicka på logga in-knappen
            login_button = driver.find_element(By.ID, "loginSubmit")  # Exempel-ID
            login_button.click()
            login_button = driver.find_element(By.ID, "loginSubmit")  # Exempel-ID
            login_button.click()
            # input()
            time.sleep(5)
            driver.get(
                f"https://global.americanexpress.com/api/servicing/v1/financials/documents?file_format=excel&limit=100&status=posted&additional_fields=true&itemized_transactions=true&account_key={os.getenv("amex_account_key")}&client_id=AmexAPI"
            )
            time.sleep(5)

            diff = set(os.listdir(downloads_path)) - set(download_dir_files)
            # print("Nedladdade filer:", diff)
            os.rename(
                os.path.join(downloads_path, diff.pop()),
                os.path.join(output_dir, "amex_transactions.xlsx"),
            )

        finally:

            driver.quit()


if __name__ == "__main__":
    main()
