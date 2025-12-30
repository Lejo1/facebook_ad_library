# Facebook Ad Library Copy

This Project aims to provide a searchable and complete copy of the political ads on the [Facebook Ad Library](https://www.facebook.com/ads/library/)  
Since 17.08.2023 it also contains ads run in the EU not older than that date. You can see the extra fields below.  
Facebook already provides all this data via their web interface. The Problem with this is that it's hardly searchable and therefore no real use for Analysis of political advertisement. In Addition to this the [API](https://www.facebook.com/ads/library/api/) is hard to access and limited in many ways.  
This data is already meant to be public so this dataset is just helping to provide the transparency ~~Facebook~~ Meta wants to provide.

**Site to Live access the Data: https://ad-archive.nexxxt.cloud**

## Disagreements with Facebook

This project is **not** authorized or associated by Facebook in any way. Following a mail to me on the 16.10.2024 I've been told that the datasets are used for alleged malicious behaviour by other actors. I've been asked to take down the public access to the datasets. As I've been told, the data may only be provided to people who themselves have verified to access the Facebook Ad Library API. See the Live access site on how to access the data!
Specifically, the kaggle datasets have been removed completely.  
For clarification: I don't believe the datasets have been used or are useful for bad actors in the by Facebook described way. I've been told by multiple researchers that this dataset helped them with their work. As all this data is published by Facebook completely public on their [Facebook Ad Library](https://www.facebook.com/ads/library/) site, I don't think this project is enabling malicious behaviours by third-party.

All of this wouldn't be that much of a problem for this project. What really irritates me is their rule of a maximum of 15 apps. This drastically reduced the rate limit I can utilise for crawling the Ad Library. I'm not sure if I will still be able to provide complete coverage of the Ad Library with this limitation. Therefore I would be deeply grateful if you could donate your access tokens to be used for crawling! You can do this after you got yourself verified on the website!

## About the Data

The data is loaded directly from their official [API](https://www.facebook.com/ads/library/api/).

Since V3 the ads are crawled using an empty query (*) across all countries. This query turned out to be quiet reliable and returns all ads of all pages

Previously the data was downloaded by page_id obtained from the [Ad-reports](https://www.facebook.com/ads/library/report/). These should only include pages related to politics or issues of political importance but not all are clearly flagged.  
Cause these reports contain user generated page_names and disclaimers some names or disclaimers might be corrupted by strange characters.

Another thing I realized is that some ads (or whole pages?) are temporarily (or permanently?) not searchable by the page_id which published them. You can identify them by checking the specified amount of Ads from the report vs. the actual loaded amount of ads in the dataset. Often this also results in pages seemingly having 0 ads. You can identify them by the msg field being empty (msg="").   
One more problem is that advertisements from page_id=0 pages are not crawlable by their page_id. These often just refer to a "Instagram User of some id" or other Facebook-Platform users. Have a look at the reports I used for more information. UPDATE: They are crawled using the empty query trick.
Also I later realized that when crawling very huge sites are empty although they should contain ads.

~~In the end this resulted in the ads in this dataset being less than it should be according to the reports.~~ Should be pretty accurate now.

### Fields of the ads.json file
#### Default fields
- id("_id" in the table)
- ad_creation_time
- ad_creative_bodies
- ad_creative_link_captions
- ad_creative_link_descriptions
- ad_creative_link_titles
- ad_delivery_start_time
- ad_delivery_stop_time
- languages
- page_id
- page_name
- publisher_platforms

#### Fields only for political ads
- bylines
- currency
- delivery_by_region
- demographic_distribution
- estimated_audience_size
- impressions
- spend

#### Fields only for ads run in the EU
- target_locations
- target_gender
- target_ages
- eu_total_reach
- beneficiary_payers
- age_country_gender_reach_breakdown

#### Extra (non fb) fields
- rendered (defines if the rendered version is available) (DEPRECATED since V5!)
- rendering_started (used for queing the ads for rendering) (DEPRECATED since V5!)
- lost (True, if the ad wasn't found while rendering) (DEPRECATED since V5!)
- _last_updated (contains the date the ad was last crawled/updated)

The field `ad_snapshot_url` is not crawled as it's just a combination of the id and your access token:  
`https://www.facebook.com/ads/archive/render_ad/?id=<id>&access_token=<token>`  
To get to the ad if you don't have any access token you can use this link:  
`https://www.facebook.com/ads/library/?id=<id>`  

For more information have a look at the `example.json` file or the description of the fields on the official [API](https://www.facebook.com/ads/library/api/).

### Individual Ad-Data

You can access the current data stored for an ad at any time at: `https://ad-archive.nexxxt.cloud/ad/<AD_ID>`. This endpoint may also be used for automated downloads of ad-information and allows cross-origin requests. Please note that it might take some time for new ads to be crawled and added to the database.

### Available Dataset-Dumps

**Only accessable to people who themselves can access the Facebook Ad Archive API!** See above section "Disagreements with Facebook" for more information why. Sorry for the inconvenience!  
To allow access restrictions, the Links have been moved to the website: **https://ad-archive.nexxxt.cloud**  
To receive access please complete the Steps under "Get Access" on the site.

**For scientific organizations or press, I provide custom exports on request.**

#### V6
Since V6 there is a _last_updated field. It's automatically updated to the current time whenever the ad crawled from the Facebook ad library. It doesn't matter if the data actually changed. This aims to allow knowledge of the persistence of ads inside the database. Older ads may not have the field, but still exist in the ad library.
#### V5
On the 17.08.2023 all EU ads since that date appeared in the database. It's now more than double the size before. EU ads contain extra fields as specificed above.  
The fields used for rendering have been removed and are now handled separately. The `lost` field is deprecated and not set for new ads anymore but still exists for older ads.  

#### V4
Downloading the database into a JSON file and compressing it took me increasingly long. That's why I switched to compressed [BSON](https://en.wikipedia.org/wiki/BSON) files (bson.gz). These are native to mongodb and can be created way faster and more reliable.  
These are created using the [mongodump](https://www.mongodb.com/docs/database-tools/mongodump/) tool and can be loaded into your own mongodb using [mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/). You can also convert them into normal json files using their [bsondump](https://www.mongodb.com/docs/database-tools/bsondump/) tool.  
In addition to this you can use the metadata file to restore the indices used in my database.  

#### V3
Ads have been crawled using the empty query (*) across all countries. Should in theory now contain all ads in the library.  
Field `rendered` added for the previews.  
No `todo.json` collection file as the stats are wrong and weren't relevant for this crawl.  

#### V2
**V2 and older:**  
`todo.json`-File: based on the [Ad-reports](https://www.facebook.com/ads/library/report/) and contains all pages crawled from with the timestamp of the last crawl and the paging cursor (after)  

Also contains page stats for multiple disclaimers and countries. Large pages should be complete now. Multiple reports from different dates were used for updating.  

#### V1
I first crawled the German and US Library and then decided to create a full crawl.

##### Full Crawl of all countries from all reports:
For this crawl `todo.json` contains a `lang` field specifying the report the page came from.
The reports were all automatically loaded into the db using the `import_reports.py` script.  

##### Individual countries crawled from:
- Germany (DE)
- USA (US)

## Crawling

Previously crawling was done based on the offical [reports](https://www.facebook.com/ads/library/report/) from Facebook. I loaded them into a mongodb and the old `crawl.py` script pulled the data from the Api and added it into the ads collection. Now I'm just using the empty query (*) trick to download ads from all pages across all countries, see: `crawlall.py`  
To do so you need a (or better multiple) access token. The script will automatically handle rate limiting but you might not be able to pull on multiple threads if you don't have enough tokens.  
For more information just have a look at the `crawlall.py` file.

## Contact

If you've got any more information regarding Facebook's API/Library or believe there are any legal issues with the distribution of this data please contact me: <ad-archive@nexxxt.cloud> or open an Issue!
