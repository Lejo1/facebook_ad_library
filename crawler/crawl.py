import json
import requests
from pymongo import MongoClient, errors
import time
import datetime
from threading import Thread
import math

import config

lang = "US"

# Database for the pages and ads
db = MongoClient(config.DBURL)["facebook_ads_" + lang.lower()]

# contains the page_id from the reports
todo = db["todo"]

# Ads will be saved to this collection:
ads = db["ads"]

# Global telling the threads if they should continue their work
_RUN = True


class Crawler(Thread):
    """One Crawling proccess (to be threaded).
    Allows specifing a range of tokens to use"""

    def __init__(self, min=0, max=len(config.TOKENS)):
        Thread.__init__(self)
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
    def pull_page(self, page_id):
        limit = config.LIMIT
        after = ""
        while True:
            print("Running link...")
            firsturl = config.URL + "?access_token=%s&search_page_ids=%s&ad_reached_countries=%s&ad_active_status=ALL&fields=%s&limit=%i" % (
                config.TOKENS[self.tround][1], page_id, lang, config.FIELDS, limit)
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
                    if "message" in out["error"]:
                        if response.status_code == 500:
                            if out["error"]["message"] == "Please reduce the amount of data you\'re asking for, then retry your request":
                                # We just try it again with half the amount of data
                                limit = int(limit * 0.5)
                                print(
                                    "Got too much data, Retring with half the amount(%i)" % limit)
                                continue

                            if out["error"]["message"] == "An unexpected error has occurred. Please retry your request later.":
                                # These just occur sometimes and we don't want the whole script to stop.
                                print("Unexpected error! Watiting 1min...")
                                time.sleep(60)
                                continue

                    if "type" in out["error"]:
                        if out["error"]["code"] == 613:
                            # the cooldown function has already switched to the next key so we can just retry
                            print("Got Rate limited!")
                            continue

                        if out["error"]["type"] == "OAuthException":
                            # All other OAuthException-errors will stop the script to prevent error-spaming
                            print("INVALID Token")
                            exit()

                print("Something went wrong...")
                # This error will be stored in the msg field page will be status="error"
                return [False, err]

            out = response.json()
            data = out["data"]
            amount = len(data)
            if "paging" in out:
                # This is the pointer to get results of the next page
                # The last one poiting to the next empty page will be saved in the msg field
                after = out["paging"]["cursors"]["after"]

            if amount <= 0:
                break

            for i, entrie in enumerate(data):
                # Data is saved to a mongodb, so we use the primary key _id
                data[i]["_id"] = entrie["id"]
                del data[i]["id"]

            try:
                ads.insert_many(data)
            except errors.BulkWriteError:
                # This only happens when the script was stopped while crawling a page
                print("Ignoring duplicates...")

            print("Inserted %i items" % amount)

            if amount < limit or not "paging" in out:
                break

        print("Finished page!")
        return [True, after]

    # Pulls a id from the db and starts the download process
    # Repeats it until no items are left or the process gets interrupted
    def run(self):
        while _RUN:
            # Pull one item from the todo collection and queue it so other threads don't work on it as well
            x = todo.find_one_and_update({"status": "todo"},
                                         {"$set": {"status": "queued"}})
            if x == None:
                print("No items left!")
                break

            page_id = x["_id"]
            name = "NONE"
            if "Page name" in x:
                name = x["Page name"]

            print("Crawling %s..." % name)
            newvalues = {}
            try:
                suc, msg = self.pull_page(page_id)
                newvalues = {"$set": {"status": (
                    "done" if suc else "error"), "msg": msg, "timestamp": datetime.datetime.now()}}
            except Exception as e:
                print("Error while trying to pull %s: %s" % (name, str(e)))
                print(e)
                newvalues = {"$set": {"status": "error", "msg": "Exception: %s" % str(
                    e), "timestamp": datetime.datetime.now()}}

            todo.update_one({"_id": page_id}, newvalues)


# Spawn multiple crawling threads
if __name__ == "__main__":
    threads = []
    # Grant each threads min 5 keys
    for a in range(math.floor(len(config.TOKENS) / 5)):
        t = Crawler(a * 5, (a + 1) * 5)
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
