from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from PIL import Image
import io
import os
from time import time, sleep
from b2sdk.v2 import B2Api, SqliteAccountInfo, AuthInfoCache
from pymongo import MongoClient
import threading
from random import randrange

# Secrets from enviroment variables
TOKENS = os.getenv("TOKEN").split(",")
TOKEN = TOKENS[randrange(0, len(TOKENS))]

# Auth to Backblaze
info = SqliteAccountInfo()
cache = AuthInfoCache(info)
b2_api = B2Api(info, cache=cache)
if not info.is_same_key(os.getenv("APPLICATION_KEY_ID"), "production"):
    b2_api.authorize_account("production", os.getenv(
    "APPLICATION_KEY_ID"), os.getenv("APPLICATION_KEY"))

bucket = b2_api.get_bucket_by_name(os.getenv("BUCKET_NAME"))
# Connect to selenium/standalone-firefox docker container
options = Options()
browser = webdriver.Remote(
    command_executor=os.getenv("BROWSER_URL"), options=options)

# Database for the queue
# The queue is done by the capped render_queue database
# contains fields with the _id field and rendering_started with index
# db.render_queue.createIndex({"rendering_started": 1})
# if the value is lower then the current unix time-300 then the ad will be rendered.
# This allows queuing by setting rendering_started=0 and handles automated rendering failture
# The rendered image will then be uploaded to a storage bucket
db = MongoClient(os.getenv("DBURL"))["facebook_ads_full"]
ads = db["ads"]
queue = db["render_queue"]

# Upload the saved file to the Backblaze bucket


def upload_file(id):
    filename = "%s.jpg" % id
    path = "/out/" + filename
    bucket.upload_local_file(
        local_file=path,
        file_name=filename,
    )
    print("Added %s to storage bucket" % id)
    queue.delete_one({"_id": id})
    ads.update_one({"_id": id}, {"$unset": {"lost": ""}})

# Load the preview of the image per id


def load_preview(id):
    print("Rendering id=%s" % id)
    # Load ad_snapshot_url (can be returned by Facebook API)
    browser.get(
        "https://www.facebook.com/ads/archive/render_ad/?id=%s&access_token=%s" % (id, TOKEN))

    # Click cookie accept if the element exists
    a = browser.find_elements(
        By.CSS_SELECTOR, 'div[aria-label="Allow all cookies"][tabindex="0"]')
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
    if len(c) > 0 and c[0].get_attribute("innerHTML") != "" and c[0].get_attribute("innerHTML") != "<!-- react-mount-point-unstable -->":
        # Take screenshot and convert to jpg
        image = c[0].screenshot_as_png
        # Convert image to JPEG
        image = Image.open(io.BytesIO(image)).convert("RGB")
        image.save(path, "JPEG")

        # Upload to Backblaze bucket in the background
        print("Uploading preview...")
        threading.Thread(target=upload_file, args=[id]).start()
        return True

    # Something must have went wrong!
    print("Something went wrong! Page source: %s" % browser.page_source)
    temporilyBlocked = browser.find_elements(By.CLASS_NAME, "uiInterstitialContent")
    if (len(temporilyBlocked) > 0 and temporilyBlocked[0].get_attribute("innerHTML") == "It looks like you were misusing this feature by going too fast. You’ve been temporarily blocked from using it.") or browser.page_source.lower() == "<html><head></head><body><h1>blocked from searching or viewing the ad library</h1><p>you have been temporarily blocked from searching or viewing the ad library due to too many requests. please try again later.</p></body></html>":
        # We have got rate limited!
        print("We've got temporarily blocked! Sleeping 1h")
        sleep(3600)

    d = browser.find_elements(By.CLASS_NAME, "_50f6")
    e = browser.find_elements(By.CSS_SELECTOR, ".core h1")
    if (len(c) > 0 and (c[0].get_attribute("innerHTML") == "" or c[0].get_attribute("innerHTML") == "<!-- react-mount-point-unstable -->")) or (len(d) > 0 and d[0].text.lower() == "error: invalid id") or (len(e) > 0 and e[0].text == "Sorry, something went wrong.") or (browser.page_source == "<html><head></head><body>Sorry, this content isn't available right now</body></html>") or (browser.page_source == "<html><head></head><body><h1>profile is not linked to delegate page</h1><p>profile should always be linked to delegate page</p></body></html>"):
        # This ad seems to be lost!
        # Marking the ad as lost...
        print("Ad %s seems to be lost, marking..." % id)
        ads.update_one({"_id": id}, {"$set": {"lost": True}})
        queue.delete_one({"_id": id})
        return True

    return False


if __name__ == "__main__":
    x = None
    try:
        print("All initalized, watching queue...")
        while True:
            now = int(time())
            # Pull one item from the queue
            x = queue.find_one_and_update(
                {"rendering_started": {"$lt": now - 300}}, {"$set": {"rendering_started": now}})

            if x != None:
                load_preview(x["_id"])

            else:
                sleep(10)
                continue

            # Sleeping is important for RAM cleaning of the browser
            sleep(1)

    except KeyboardInterrupt:
        print("Stopping and quiting browser...")
    except Exception as e:
        print("Error occured: %s" % str(e))

    if x != None:
        queue.update_one({"_id": x["_id"]}, {
                       "$set": {"rendering_started": 0}})
        print("Queuing %s for redo" % x["_id"])

    try:
        browser.quit()
    except Exception as e:
        print("Browser seems to be dead already, Err: %s" % str(e))

    print("Waiting (5sec) for all upload-threads to finish...")
    sleep(5)
    print("STOP")
