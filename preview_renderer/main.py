from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image
import io
import os
from time import sleep
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from pymongo import MongoClient
import threading

# Secrets from enviroment variables
TOKEN = os.getenv("TOKEN")
RENDER_ALL = os.getenv("RENDER_ALL")

# Auth to Backblaze
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", os.getenv(
    "APPLICATION_KEY_ID"), os.getenv("APPLICATION_KEY"))
bucket = b2_api.get_bucket_by_name(os.getenv("BUCKET_NAME"))

# Connect to selenium/standalone-firefox docker container
browser = webdriver.Remote(command_executor=os.getenv("BROWSER_URL"))

# Database for the queue
# Uses an partial index on the ads collection created using:
# db.ads.createIndex({"rendered": 1}, { partialFilterExpression: {rendered: { $eq: false } } })
# So when an ad contains the field {rendered: false} it will be rendered and the field changes to true
# The rendered image will then be uploaded to a storage bucket
db = MongoClient(os.getenv("DBURL"))["facebook_ads_full"]
ads = db["ads"]

# Upload the saved file to the Backblaze bucket
def upload_file(id):
    filename = "%s.jpg" % id
    path = "/out/" + filename
    bucket.upload_local_file(
        local_file=path,
        file_name=filename,
    )
    print("Added %s to storage bucket" % id)

# Load the preview of the image per id
def load_preview(id):
    print("Rendering id=%s" % id)
    # Load ad_snapshot_url (can be returned by Facebook API)
    browser.get(
        "https://www.facebook.com/ads/archive/render_ad/?id=%s&access_token=%s" % (id, TOKEN))

    # Click cookie accept if the element exists
    a = browser.find_elements(
        By.CSS_SELECTOR, 'button[data-testid="cookie-policy-dialog-accept-button"]')
    if len(a) > 0:
        a[0].click()

    # Click text to extend it
    # We use the javascript way to prevent clicking links in the text
    b = browser.find_elements(By.CSS_SELECTOR, '._7jyr div[role="button"]')
    if len(b) > 0:
        # This happens mostly when ads are age restricted
        browser.execute_script('arguments[0].click();', b[0])

    filename = "%s.jpg" % id
    path = "/out/" + filename
    image = None

    # Select element
    c = browser.find_elements(By.CLASS_NAME, "_8n-d")
    if len(c) > 0:
        # Take screenshot and convert to jpg
        image = c[0].screenshot_as_png
    else:
        # Rendering may fail in someway, we do a full screenshot
        print("Ad %s seems to be corrupted, we take a full browser screenshot" % id)
        image = browser.get_screenshot_as_png()

    # Convert image to JPEG
    image = Image.open(io.BytesIO(image)).convert("RGB")
    image.save(path, "JPEG")

    # Upload to Backblaze bucket in the background
    print("Uploading preview...")
    threading.Thread(target=upload_file, args=[id]).start()


if __name__ == "__main__":
    x = None
    try:
        print("All initalized, watching queue... RENDER_ALL=%s" % RENDER_ALL)
        while True:
            # Pull one item from the queue (partial index on the ads collection) and remove it from there
            x = ads.find_one_and_update(
                {"rendered": False}, {"$set": {"rendered": True}})

            if x == None:
                # Is this worker supposed to just render everything?
                if RENDER_ALL == "true":
                    # Getting ad with nonexisting renderer field (not queued)
                    x = ads.find_one_and_update(
                        {"rendered": {"$exists": False}}, {"$set": {"rendered": True}})

            if x != None:
                load_preview(x["_id"])

            else:
                sleep(10)
                continue

            # Sleeping is important for RAM cleaning on the browser
            sleep(1)

    except KeyboardInterrupt:
        print("Stopping and quiting browser...")
    except Exception as e:
        print("Error occured: %s" % str(e))

    if x != None:
        ads.update_one({"_id": x["_id"]}, {"$set": {"rendered": False}})
        print("Queuing %s for redo" % x["_id"])

    try:
        browser.quit()
    except Exception as e:
        print("Browser seems to be dead already, Err: %s" % str(e))

    print("Waiting (5sec) for all upload-threads to finish...")
    sleep(5)
    print("STOP")
