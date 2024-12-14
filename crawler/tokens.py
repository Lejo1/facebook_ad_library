"""
This file defines functions for token management
The database contains a collection "tokens" with the following scheme:
_id: APP_ID (rates are per App so it makes no sense to have multiple tokens per App)
token: ACCESS_TOKEN (the actual token)
expiresAt: DATE
freshAt: TIME (in secs)

there is a TTL index on the expiresAt field:
db.tokens.createIndex({"expiresAt": 1}, {expireAfterSeconds: 0})
and a normal one on the freshAt field:
db.tokens.createIndex({freshAt: 1})
"""
from time import time, sleep
from pymongo import MongoClient
import config

# Database for the tokens
db = MongoClient(config.DBURL)["facebook_ads_full"]
tokens = db["tokens"]

def requenstToken():
    now = int(time())
    return tokens.find_one_and_update({"freshAt": {"$lt": now}},
    {"$set": {"freshAt": now+300}}, # Prevent usage of the same key for multiple crawlers
    ["token"],
    ("sort", ("freshAt", 1)))

# Gets a new token for the crawler
def getNewToken():
    x = requenstToken()
    while x == None:
        print("All keys are delayed! Sleeping 10min.")
        sleep(600)
        x = requenstToken()

    print("Using token, id="+x["_id"])
    return x["token"]

# Used to add additional delay to the token (especially for rate limiting)
def delayToken(id, delay):
    now = int(time())
    tokens.update_one({"_id": id}, {"$set": {"freshAt": now+delay}})
