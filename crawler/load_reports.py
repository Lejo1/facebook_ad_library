# Uses selenium to control the Firefox browser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from time import sleep

import os
import config


def load_reports(folder):
    # Accept Downloads
    options = Options()
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", folder)
    # Accept zip files
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk", "application/zip")

    browser = webdriver.Firefox(options=options)

    # Login to prevent later force of the login
    browser.get("https://www.facebook.com/login/")
    input("Please login and press enter.")


    for c in config.AD_COUNTRIES:
        browser.get("https://www.facebook.com/ads/library/report/?country=" + c)

        # Wait for the Data to be rendered
        sleep(1)

        # Click "All Data"
        b = browser.find_element(By.CSS_SELECTOR, 'div._7wau[tabindex="4"]')
        b.click()
        sleep(1)

        # Click Download Report, selenium click somehow didin't work for scrolling reasons
        browser.execute_script(
            'document.querySelectorAll(\'._7vil a[href="#"]\')[0].click()')

        # Wait for the download to trigger
        sleep(3)

    browser.quit()


if __name__ == '__main__':
    load_reports(os.getcwd() + "/newreports")
