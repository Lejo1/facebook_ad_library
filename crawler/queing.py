"""
Crawler management of the main crawling process. When to spawn crawlers and where to manage them.
"""

from time import time
from datetime import datetime, timedelta
from pymongo import MongoClient
import config


# Database for the crawler-queue
db = MongoClient(config.DBURL)["facebook_ads_full"]

# Collection for the crawler-queue
# _id: ObjectId (Auto)
# after: String (cursor to start with), default ""
# search: String (extra request headers), default ""
# c_limit: Int (how often to crawl before stopping), default 0 -> infinite

queue = db["crawler_queue"]

def addCrawler(after="", search="", c_limit=0, lang=None):
    """Adds a new crawler to the queue"""
    doc = {"after": after, "search": search, "c_limit": c_limit}
    if lang is not None:
        doc["lang"] = lang
    queue.insert_one(doc)

def mayGetCrawler():
    """Trys to get crawler from the queue"""
    return queue.find_one_and_delete({})

# TODO do this in a nicer more consisten way :)
# it's currently rather like an playground for different crawling methods.
last_spawned = int(time()) - 3590 # start spawning 10 sec, after start
i = 0
past_offset = 0
def mayAddCrawlers():
    """Adds crawlers to the queue based on the time passed.
    Not thread safe! Should only be run on a single thread on a single maschine."""
    global last_spawned, i, past_offset
    now = int(time())
    if now-last_spawned > 3600:
        last_spawned = now
        print("Adding Crawlers to queue, Hour: %i" % i)
        c_limit = config.HOURLY_LIMIT
        if i == 0:
            print("Crawling Completly! Next Complete-Crawl in %s hours." % config.GLOBAL_RECRAWL)
            c_limit = 0

        addCrawler("", "" , c_limit)
        if (i % config.POLITICS_RECRAWL) == 0:
            print("Crawling Political ads, next crawl in %d hours" % config.POLITICS_RECRAWL)
            addCrawler("", "&ad_type=POLITICAL_AND_ISSUE_ADS", 0, ",".join(config.POLITICAL_ADS_COUNTRIES))

        if (i % config.PAST_RECRAWL) == 0:
            months = 14 - past_offset % 14
            new_date = datetime.now() - timedelta(days=months*30)
            str_date = new_date.strftime("%Y-%m-%d")
            print("Crawling in the past, by date-offset: %s" % str_date)
            #addCrawler("", "&ad_delivery_date_max=%s" % str_date)
            past_offset += 3 # To do some funny mixing :) make sure not factor of 14

        print("Waiting 1 hour to spawn the next Thread")
        i = (i+1 % config.GLOBAL_RECRAWL)
