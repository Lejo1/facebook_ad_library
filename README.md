# Facebook Ad Library Copy

This Project aims to provide a searchable and complete copy of the political ads on the [Facebook Ad Library](https://www.facebook.com/ads/library/)  
Facebook already provides all this data via their web interface. The Problem with this is that it's hardly searchable and therefore no real use for Analysis of political advertisement. In Addition to this the [API](https://www.facebook.com/ads/library/api/) is hard to access and limited in many ways.  
This data is already meant to be public so this dataset is just helping to provide the transparency ~~Facebook~~ Meta wants to provide.

## About the Data

The data is loaded directly from their official [API](https://www.facebook.com/ads/library/api/).

The data is downloaded by country and page_id obtained from the [Ad-reports](https://www.facebook.com/ads/library/report/). These should only include pages related to politics or issues of political importance but not all are clearly flagged.  
Cause these reports contain user generated page_names and disclaimers some names or disclaimers might be corrupted by strange characters.

Another thing I realized is that some ads (or whole pages?) are temporarily (or permanently?) not searchable by the page_id which published them. You can identify them by checking the specified amount of Ads from the report vs. the actual loaded amount of ads in the dataset. Often this also results in pages seemingly having 0 ads. You can identify them by the msg field being empty (msg="").   
One more problem is that advertisements from page_id=0 pages are not searchable. These often just refer to a "Instagram User of some id" or other Facebook-Platform users. Have a look at the reports I used for more information.  
Also I later realized that when crawling very huge sites are empty although they should contain ads. That's the reason why the V1 might not contain all (especially older) ads.

In the end this resulted in the ads in this dataset being less than it should be according to the reports.

### There are two json files per zip-file download:

`todo.json`: based on the [Ad-reports](https://www.facebook.com/ads/library/report/) and contains all pages crawled from with the timestamp of the last crawl and the paging cursor (after)  
`ads.json`: Contains the actual ads with the following fields:

### Fields
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

The field `ad_snapshot_url` is not crawled as it's just a combination of the id and your access token:  
`https://www.facebook.com/ads/archive/render_ad/?id=<id>&access_token=<token>`  
Alternatively you can use this link if you don't have any access token:  
`https://www.facebook.com/ads/library/?id=<id>`

For more information have a look at the `example.json` file or the description of the fields on the official [API](https://www.facebook.com/ads/library/api/).

### Available Countries

#### V2
Also contains page stats for multiple disclaimers and countries. Large pages should be complete now. Multiple reports from different dates were used for updating.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full2.zip)

#### V1

I first crawled the German and US Library and then decided to create a full crawl.

##### Full Crawl of all countries from all reports:
For this crawl `todo.json` contains a `lang` field specifying the report the page came from.
The reports were all automatically loaded into the db using the `import_reports.py` script.  
[Download](https://b2.nexxxt.cloud/facebook_ads/full.zip) [Reports](https://b2.nexxxt.cloud/facebook_ads/reports_full.zip)

##### Individual countries crawled from:
The data of these countries are also available on [kaggle.com](https://www.kaggle.com/lejo11/facebook-ad-library)
- Germany (DE) [Download](https://b2.nexxxt.cloud/facebook_ads/de.zip) [Report](https://b2.nexxxt.cloud/facebook_ads/report_de.csv)
- USA (US) [Download](https://b2.nexxxt.cloud/facebook_ads/us.zip) [Report](https://b2.nexxxt.cloud/facebook_ads/report_us.csv)

## Crawling

Crawling is done based on the offical [reports](https://www.facebook.com/ads/library/report/) from Facebook. I loaded them into a mongodb and the `crawl.py` script pulled the data from the Api and added it into the ads collection. To do so you need a (or better multiple) access token. The script will automaticly handle rate limiting but you might not be able to pull on multiple threads if you don't have enough tokens.  
For more information just have a look at the `crawl.py` file.

## Contact

If you've got any more information regarding Facebook's API/Library or believe there are any legal issues with the distribution of this data please contact me: <Lejo_1@web.de> or open an Issue!
