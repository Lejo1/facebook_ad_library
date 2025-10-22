import json
import requests
from pymongo import MongoClient, UpdateOne
from time import sleep
from threading import Thread
import sys

import config
import tokens
import queing

LANG = ",".join(config.COUNTRIES.keys())

# Database for the ads
db = MongoClient(config.DBURL)["facebook_ads_full"]

# Ads will be saved to this collection:
ads = db["ads"]


class Crawler(Thread):
    """One Crawling proccess (to be threaded).
    Tokens are requested directly from the tokens collection
    This one doesn't crawl per page_id but accross the whole library
    using an empty query (*)
    after specifies the cursor to start with
    search allows to narrow the search
    c-limit specifies how often to crawl before stopping"""

    def __init__(self, after="", search="", c_limit=0, lang=LANG):
        Thread.__init__(self)
        self.after = after
        self.search = search
        self.c_limit = c_limit
        self.lang = lang
        self.stop = False
        self.token = tokens.getNewToken()

    # Checks the x-business-use-case-usage for the usage values.
    # If one of them reaches 100 we are getting rate limited.
    # This function delays the tokens and requests new ones
    def cooldown(self, headers):
        if "x-business-use-case-usage" in headers:
            raw_usage = json.loads(headers["x-business-use-case-usage"])
            id = list(raw_usage.keys())[0]
            usage = raw_usage[id][0]
            print("Current usage: %s" % str(usage))
            time_access = usage["estimated_time_to_regain_access"]
            total_time = usage["total_time"]
            total_cputime = usage["total_cputime"]
            max_time = max(total_time, total_cputime)
            if max_time > 97 or time_access != 0:
                delay = max(time_access * 60, (max_time-97) * 600)
                tokens.delayToken(id, delay)
                print("High Usage, Key delayed for %s seconds, Rotating keys..." % delay)
                self.token = tokens.getNewToken()

    # Does the actual downloading of the page
    def run(self):
        limit = config.LIMIT
        retried = 0
        error_retries = 0
        count = 0
        while not self.stop and (self.c_limit == 0 or self.c_limit > count):
            count += 1
            try:
                print("Running link... After: %s" % self.after)
                firsturl = config.URL + "?access_token=%s&search_terms=*&ad_reached_countries=%s&ad_active_status=ALL&unmask_removed_content=true&fields=%s&limit=%i%s" % (
                    self.token, self.lang, config.FIELDS, limit, self.search)
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
                            sleep(60)
                            raise Exception(out["error"]["message"])

                        elif out["error"]["code"] == 190 or out["error"]["code"] == 10:
                            print("INVALID Token!")
                            # We should delete the token from the database
                            tokens.deleteToken(self.token)
                            self.token = tokens.getNewToken()
                            print("Using new token: %s" % self.token)
                            continue


                        elif out["error"]["code"] == 613:
                            # the cooldown function has already switched to the next key so we can just retry
                            print("Got Rate limited!")
                            continue

                        elif out["error"]["code"] == 100:
                            # A super weird error where waiting might help?
                            # wait 10 min
                            print("Got the code=100 error, make sure to use tokens with ads_read permission!")
                            sleep(600)
                            continue

                    # We can't handle this error
                    raise Exception("Uncatched Error")

                error_retries = 0
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
                        '$set': x,
                        '$currentDate': {'_last_updated': True}
                    }, upsert=True) for x in data]
                    result = ads.bulk_write(upserts)

                    print("Inserted %i items" % amount)
                    limit = config.LIMIT

                if not "paging" in out:
                    print("Got no new paging cursor, sleeping %ds" % config.END_RETRY_SLEEP)
                    sleep(config.END_RETRY_SLEEP)
                    retried += 1
                    if retried > config.END_RETRIES:
                        # We retried the same after pointer for END_RETRIES times.
                        # We can be quiet sure it's really the end
                        break

                else:
                    retried = 0
            except Exception as e:
                print("Unexpected Error while crawling try=%d, Error: %s" % (error_retries, str(e)))
                if error_retries >= config.ERROR_RETRIES:
                    print("Uncatched Error, STOPPING!")
                    return False

                error_retries += 1
                print("Sleeping 10s...")
                sleep(10)

        if self.stop:
            print("Requeing task, after: %s" % self.after)
            c_limit = 0
            if self.c_limit != 0:
                c_limit = self.c_limit-count
            queing.addCrawler(self.after, self.search, c_limit, self.lang)
        else:
            print("Finished, last Pointer: %s" % self.after)
        return True

# Spawn multiple crawling threads
if __name__ == "__main__":
    threads = []
    try:
        print("Starting crawler-spawner...")
        while True:
            new = queing.mayGetCrawler()
            if new:
                print("Spawning crawler, after=%s, search=%s, c_limit=%d" % (new["after"], new["search"] ,new["c_limit"]))
                t = Crawler(new["after"], new["search"] , new["c_limit"], new.get("lang", LANG))
                t.start()
                threads.append(t)

            queing.mayAddCrawlers()
            sleep(3)

    except KeyboardInterrupt:
        print("Got Interrupt, Stopping...")
        # Setting run vars to false -> thrads should stop
        for t in threads:
            t.stop = True

        for t in threads:
            t.join()

    print("STOP")
