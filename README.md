# Facebook Ad Library Copy

This Project aims to provide a searchable and complete copy of the political ads on the [Facebook Ad Library](https://www.facebook.com/ads/library/)  
Facebook already provides all this data via their web interface. The Problem with this is that it's hardly searchable and therefore no real use for Analysis of political advertisement. In Addition to this the [API](https://www.facebook.com/ads/library/api/) is hard to access and limited in many ways.  
This data is already meant to be public so this dataset is just helping to provide the transparency ~~Facebook~~ Meta wants to provide.

**Site to Live access the Data: https://ad-archive.nexxxt.cloud**

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
- id("_id" in the table)
- ad_creation_time
- ad_creative_bodies
- ad_creative_link_captions
- ad_creative_link_descriptions
- ad_creative_link_titles
- ad_delivery_start_time
- ad_delivery_stop_time
- bylines
- currency
- delivery_by_region
- demographic_distribution
- estimated_audience_size
- impressions
- languages
- page_id
- page_name
- publisher_platforms
- spend
- rendered (defines if the rendered version available)
- lost (True, if the ad wasn't found while rendering)

The field `ad_snapshot_url` is not crawled as it's just a combination of the id and your access token:  
`https://www.facebook.com/ads/archive/render_ad/?id=<id>&access_token=<token>`  
To get to the ad if you don't have any access token you can use this link:  
`https://www.facebook.com/ads/library/?id=<id>`  
To actually render the ad without a access token you can use my cloudflare worker to proxy the data:
`https://render-facebook-ad.lejo.workers.dev/<id>`
You might need to disabled some privacy settings as browsers (like Firefox) block cross-site Facebook requests.

For more information have a look at the `example.json` file or the description of the fields on the official [API](https://www.facebook.com/ads/library/api/).

### Rendered Previews

The script from the `preview_renderer` folder is used to take a screeshot of the relevant elements from the `ad_snapshot_url` of each ad. The rendered field defines whether the rendered image is available. The `rendering_started` field is used for queuing the ads for rendering.
After rendering you can view them here: `https://facebook-ad-previews.nexxxt.cloud/<id>.jpg`

### Available Data-Downloads

#### V4
Downloading the database into a JSON file and compressing it took me increasingly long. That's why I switched to compressed [BSON](https://en.wikipedia.org/wiki/BSON) files (bson.gz). These are native to mongodb and can be created way faster and more reliable.  
These are created using the [mongodump](https://www.mongodb.com/docs/database-tools/mongodump/) tool and can be loaded into your own mongodb using [mongorestore](https://www.mongodb.com/docs/database-tools/mongorestore/). You can also convert them into normal json files using their [bsondump](https://www.mongodb.com/docs/database-tools/bsondump/) tool.  
In addition to this you can use the metadata file to restore the indices used in my database.  
Some of these datasets are also available on kaggle.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full4/ads.bson.gz) [Metadata](https://b2.nexxxt.cloud/facebook_ads/full4/ads.metadata.json.gz) (07.09.2022)  
[Download](https://b2.nexxxt.cloud/facebook_ads/full4.1/ads.bson.gz) [Metadata](https://b2.nexxxt.cloud/facebook_ads/full4.1/ads.metadata.json.gz) (22.10.2022) [kaggle](https://www.kaggle.com/datasets/lejo11/facebook-ad-library/versions/6)  
[Download](https://b2.nexxxt.cloud/facebook_ads/full4.2/ads.bson.gz) [Metadata](https://b2.nexxxt.cloud/facebook_ads/full4.2/ads.metadata.json.gz) (30.12.2022) [kaggle](https://www.kaggle.com/datasets/lejo11/facebook-ad-library/versions/7)  



#### V3
Ads have been crawled using the empty query (*) across all countries. Should in theory now contain all ads in the library.  
Field `rendered` added for the previews.  
No `todo.json` collection file as the stats are wrong and weren't relevant for this crawl.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full3.zip) (09.02.2022)  
[Download](https://b2.nexxxt.cloud/facebook_ads/full3.1.zip) (03.04.2022)  
[Download](https://b2.nexxxt.cloud/facebook_ads/full3.2.zip) (26.05.2022)

#### V2
**V2 and older:**  
`todo.json`-File: based on the [Ad-reports](https://www.facebook.com/ads/library/report/) and contains all pages crawled from with the timestamp of the last crawl and the paging cursor (after)  

Also contains page stats for multiple disclaimers and countries. Large pages should be complete now. Multiple reports from different dates were used for updating.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full2.zip)

#### V1
I first crawled the German and US Library and then decided to create a full crawl.

##### Full Crawl of all countries from all reports:
For this crawl `todo.json` contains a `lang` field specifying the report the page came from.
The reports were all automatically loaded into the db using the `import_reports.py` script.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full.zip) [Reports](https://b2.nexxxt.cloud/facebook_ads/reports_full.zip)

##### Individual countries crawled from:
The data of these countries is also available on [kaggle.com](https://www.kaggle.com/datasets/lejo11/facebook-ad-library/versions/2)
- Germany (DE) [Download](https://b2.nexxxt.cloud/facebook_ads/de.zip) [Report](https://b2.nexxxt.cloud/facebook_ads/report_de.csv)
- USA (US) [Download](https://b2.nexxxt.cloud/facebook_ads/us.zip) [Report](https://b2.nexxxt.cloud/facebook_ads/report_us.csv)

## Crawling

Previously crawling was done based on the offical [reports](https://www.facebook.com/ads/library/report/) from Facebook. I loaded them into a mongodb and the `crawl.py` script pulled the data from the Api and added it into the ads collection. Now I'm just using the empty query (*) trick to download ads from all pages across all countries, see: `crawlall.py`  
To do so you need a (or better multiple) access token. The script will automatically handle rate limiting but you might not be able to pull on multiple threads if you don't have enough tokens.  
For more information just have a look at the `crawl.py`/`crawlall.py` file.

## Contact

If you've got any more information regarding Facebook's API/Library or believe there are any legal issues with the distribution of this data please contact me: <ad-archive@nexxxt.cloud> or open an Issue!
