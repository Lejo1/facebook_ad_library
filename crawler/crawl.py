import json
import requests
from pymongo import MongoClient, UpdateOne
import time
import datetime
from threading import Thread
import math
import sys

import config

lang = ",".join(config.COUNTRIES.keys())

# Database for the pages and ads
db = MongoClient(config.DBURL)["facebook_ads_full"]

# contains the page_id from the reports
pages = db["pages"]

# Ads will be saved to this collection:
ads = db["ads"]

# Global telling the threads if they should continue their work
_RUN = True


class Crawler(Thread):
    """One Crawling proccess (to be threaded).
    Allows specifing a range of tokens to use"""

    def __init__(self, state="todo", min=0, max=len(config.TOKENS)):
        Thread.__init__(self)
        self.state = state
        self.min = min
        self.max = max
        self.delayed = [0 for a in range(max)]
        self.tround = min

    # Checks the x-business-use-case-usage for the usage values.
    # If one of them reaches 100 we are getting rate limited.
    # This function just switches to the next key if the usage is above 95 or if the key is already limited
    def cooldown(self, headers):
        if "x-business-use-case-usage" in headers:
            raw_usage = json.loads(headers["x-business-use-case-usage"])
            usage = raw_usage[list(raw_usage.keys())[0]][0]
            print("Current usage: %s" % str(usage))
            time_access = usage["estimated_time_to_regain_access"]
            total_time = usage["total_time"]
            total_cputime = usage["total_cputime"]
            curr_time = int(time.time())
            if total_time > 95 or total_cputime > 95 or time_access != 0:
                self.delayed[self.tround] = curr_time + \
                    max(time_access * 60, 600)
                print("High Usage, Rotating keys...")
                self.tround = self.min

                while self.delayed[self.tround] > curr_time:
                    self.tround += 1
                    if self.tround == self.max:
                        print("All keys are delayed! Sleeping 10min.")
                        time.sleep(600)
                        curr_time = int(time.time())
                        self.tround = self.min

                print("Switched to key n=%i" % self.tround)

    # Does the actual downloading of the page
    def pull_page(self, page_id, after):
        limit = config.LIMIT
        while True:
            print("Running link... After: %s" % after)
            firsturl = config.URL + "?access_token=%s&search_page_ids=%s&ad_reached_countries=%s&ad_active_status=ALL&fields=%s&limit=%i" % (
                config.TOKENS[self.tround], page_id, lang, config.FIELDS, limit)
            if after != "":
                firsturl += "&after=%s" % after

            response = requests.get(firsturl)
            # Checking the usage header:
            self.cooldown(response.headers)

            if response.status_code != 200:
                err = "Status: %i Response: %s" % (
                    response.status_code, response.content)
                print("Something went wrong... %s" % err)
                out = response.json()
                if out and "error" in out:
                    if response.status_code == 500:
                        if "message" in out["error"]:
                            if out["error"]["message"] == "Please reduce the amount of data you\'re asking for, then retry your request":
                                # We just try it again with half the amount of data
                                limit = int(limit * 0.5)
                                print(
                                    "Got too much data, Retring with half the amount(%i)" % limit)
                                continue

                    if out["error"]["code"] == 1 or out["error"]["code"] == 2:
                        # These just occur sometimes and we don't want the whole script to stop.
                        print("Unexpected error! Watiting 1min...")
                        time.sleep(60)
                        continue

                    elif out["error"]["code"] == 33:
                        print("INVALID PAGE ID")

                    elif out["error"]["code"] == 190:
                        # stop the script to prevent error-spaming
                        print("INVALID Token!")
                        _RUN = False

                    elif out["error"]["code"] == 613:
                        # the cooldown function has already switched to the next key so we can just retry
                        print("Got Rate limited!")
                        continue

                # This error will be stored in the msg field page will be status="error"
                return [False, err]

            out = response.json()
            data = out["data"]
            amount = len(data)
            if "paging" in out:
                # This is the pointer to get results of the next page
                # The last one poiting to the next empty page will be saved in the msg field
                after = out["paging"]["cursors"]["after"]

            if amount > 0:
                for i, entrie in enumerate(data):
                    # Data is saved to a mongodb, so we use the primary key _id
                    data[i]["_id"] = entrie["id"]
                    del data[i]["id"]

                # Create bulk of upsert updates to allow key-duplicates
                upserts = [UpdateOne({'_id': x['_id']}, {
                                     '$set': x}, upsert=True) for x in data]
                result = ads.bulk_write(upserts)

                print("Inserted %i items" % amount)

            if not "paging" in out:
                break

        print("Finished page!")
        return [True, after]

    # Pulls a id from the db and starts the download process
    # Repeats it until no items are left or the process gets interrupted
    def run(self):
        while _RUN:
            # Pull one item from the pages collection and queue it so other threads don't work on it as well
            x = pages.find_one_and_update({"status": self.state},
                                         {"$set": {"status": "crawling"}})
            if x == None:
                print("No items left!")
                break

            page_id = x["_id"]
            name = "NONE"
            if "page_name" in x:
                name = x["page_name"]

            print("Crawling %s..." % name)
            after = ""
            if self.state == "crawlcursor" and "after" in x:
                after = x["after"]

            newvalues = {}
            try:
                suc, msg = self.pull_page(page_id, after)
                if suc:
                    newvalues = {
                        "$set": {"status": "done", "after": msg, "timestamp": datetime.datetime.now()}}
                else:
                    newvalues = {
                        "$set": {"status": "error", "msg": msg, "timestamp": datetime.datetime.now()}}

            except Exception as e:
                print("Error while trying to pull %s: %s" % (name, str(e)))
                print(e)
                newvalues = {"$set": {"status": "error", "msg": "Exception: %s" % str(
                    e), "timestamp": datetime.datetime.now()}}

            pages.update_one({"_id": page_id}, newvalues)


# Spawn multiple crawling threads
if __name__ == "__main__":
    threads = []
    # Grant each threads min 7 keys
    state = "todo"
    if len(sys.argv) >= 2:
        state = sys.argv[1]
    print("Checking for state %s" % state)
    amount = math.floor(len(config.TOKENS) / config.KEYS_PER_THREAD)
    print("Spawning %i Crawler-Threads" % amount)
    for a in range(amount):
        t = Crawler(state, a * config.KEYS_PER_THREAD,
                    (a + 1) * config.KEYS_PER_THREAD)
        t.start()
        threads.append(t)

    try:
        for t in threads:
            t.join()

    except KeyboardInterrupt:
        print("Got Interrupt, Stopping...")
        # Setting global var to false-> all threads should stop after their page
        _RUN = False

        for t in threads:
            t.join()

    print("STOP")
