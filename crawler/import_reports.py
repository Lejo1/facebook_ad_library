from zipfile import ZipFile
import csv
import io
from pymongo import MongoClient, errors

import config

db = MongoClient(config.DBURL)["facebook_ads_full"]
todo = db["todo"]

# The zip-folders containing the reports are here:
REPORTPATH = "reports/"
BASEPATH = "FacebookAdLibraryReport_2022-01-16_"
ZIPEND = "_lifelong.zip"
CSVEND = "_lifelong_advertisers.csv"

total_count = 0
total_number = 0
total_updates = 0
zero_count = 0

# Looping through all countries we got reports for and adding them to the db
for lang in config.AD_COUNTRIES:
    print("Reading %s" % config.COUNTRIES[lang])
    with ZipFile(REPORTPATH + BASEPATH + lang + ZIPEND) as zip:
        with io.TextIOWrapper(zip.open(BASEPATH + lang + CSVEND), encoding="utf-8") as file:
            csv_file = csv.reader(file)
            count = 0
            number = 0
            updates = 0

            for row in csv_file:
                if count != 0:
                    id = row[0]
                    if id == "0":
                        # We can't crawl these...
                        zero_count += 1
                        continue

                    number_of_ads = int(row[4])
                    number += number_of_ads
                    # We add it to db or update the entry
                    # spend/amount is per lang
                    query = {"_id": id}
                    action = {"$set": {
                        "page_name": row[1],
                        "disclaimer": row[2],
                        ("spent.%s" % lang): row[3],
                        ("amount.%s" % lang): number_of_ads
                    }}

                    res = todo.update_one(query, action, upsert=True)
                    if res.modified_count >= 1:
                        # If the number_of_ads changed we set status to "todo"
                        todo.update_one(query, {"$set": {"status": "todo"}})
                        updates += 1

                count += 1

            count -= 1
            print("Got %i pages" % count)
            print("Got %i ads in report" % number)
            print("Got %i page updates" % updates)
            total_count += count
            total_number += number
            total_updates += updates

print("Got total %i pages" % total_count)
print("Got total %i ads in reports" % total_number)
print("Got total %i page updates" % total_updates)
print("Got %i uncrawlable with id=0" % zero_count)
