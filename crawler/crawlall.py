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

# Database for the  ads
db = MongoClient(config.DBURL)["facebook_ads_full"]

# Ads will be saved to this collection:
ads = db["ads"]

# Global telling the threads if they should continue their work
_RUN = True


class Crawler(Thread):
    """One Crawling proccess (to be threaded).
    Allows specifing a range of tokens to use
    This one doesn't crawl per page_id but accross the whole library
    using an empty query (*)"""

    def __init__(self, after="", min=0, max=len(config.TOKENS)):
        Thread.__init__(self)
        self.after = after
        self.min = min
        self.max = max
        self.delayed = [0 for a in range(max)]
        self.tround = min

    # Checks the x-business-use-case-usage for the usage values.
    # If one of them reaches 100 we are getting rate limited.
    # This function just switches to the next key if the usage is above 95 or if the key is already limited
    def cooldown(self, headers):
        if "x-business-use-case-usage" in headers:
            usage = json.loads(
                headers["x-business-use-case-usage"])[config.TOKENS[self.tround][0]][0]
            print("Current usage: %s" % str(usage))
            time_access = usage["estimated_time_to_regain_access"]
            count_pct = usage["object_count_pct"]
            total_time = usage["total_time"]
            total_cputime = usage["total_cputime"]
            curr_time = int(time.time())
            if count_pct > 95 or total_time > 95 or total_cputime > 95 or time_access != 0:
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
    def run(self):
        limit = config.LIMIT
        retried = 0
        global _RUN
        while _RUN:
            print("Running link... After: %s" % self.after)
            firsturl = config.URL + "?access_token=%s&search_terms=*&ad_reached_countries=%s&ad_active_status=ALL&fields=%s&limit=%i" % (
                config.TOKENS[self.tround][1], lang, config.FIELDS, limit)
            if self.after != "":
                firsturl += "&after=%s" % self.after

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

                    elif out["error"]["code"] == 190:
                        # stop the script to prevent error-spaming
                        print("INVALID Token!")
                        _RUN = False

                    elif out["error"]["code"] == 613:
                        # the cooldown function has already switched to the next key so we can just retry
                        print("Got Rate limited!")
                        continue

                # We can't handle this error
                return False

            out = response.json()
            data = out["data"]
            amount = len(data)
            if "paging" in out:
                # This is the pointer to get results of the next page
                # The last one poiting to the next empty page will be saved in the msg field
                self.after = out["paging"]["cursors"]["after"]

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
                limit = config.LIMIT

            if not "paging" in out:
                print("Got no new paging cursor!")
                retried +=1
                if retried > 3:
                    # We retried the same after pointer for 3 times.
                    # We can be quiet sure it's really the end
                    break

            else:
                retried = 0

        print("Finished, last Pointer: %s" % self.after)
        return True

# Spawn multiple crawling threads
if __name__ == "__main__":
    after = ""
    if len(sys.argv) >= 2:
        after = sys.argv[1]

    threads = []
    try:
        while True:
            print("Spawning Crawling Thread")
            t = Crawler(after, 0, len(config.TOKENS))
            t.start()
            threads.append(t)
            print("Waiting 1 day to spawn the next Thread")
            time.sleep(86400)

    except KeyboardInterrupt:
        print("Got Interrupt, Stopping...")
        # Setting global var to false-> thread should stop after their crawl
        _RUN = False

        for t in threads:
            t.join()

    print("STOP")
