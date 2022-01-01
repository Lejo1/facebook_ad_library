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

In the end this resulted in the ads in this dataset being less than it should be according to the reports.

### There are two json files per country:

`todo.json`: based on the [Ad-reports](https://www.facebook.com/ads/library/report/) and contains all pages crawled from with the timestamp of the last crawl and the paging cursor (after) in the "msg" field  
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

The whole dataset with all crawled countries and reports is available on [kaggle.com](https://www.kaggle.com/lejo11/facebook-ad-library)  
You can also download the individual zip-folders and reports they are based on from here:

- Germany (DE) [Download](https://s3.nexxxt.cloud/facebook_ads/de.zip) [Report](https://s3.nexxxt.cloud/facebook_ads/report_de.csv)
- USA (US) [Download](https://s3.nexxxt.cloud/facebook_ads/us.zip) [Report](https://s3.nexxxt.cloud/facebook_ads/report_us.csv)
- Planned: Full Crawl of all countries from all reports

## Crawling

Crawling is done based on the offical [reports](https://www.facebook.com/ads/library/report/) from Facebook. I loaded them into a mongodb and the `crawl.py` script pulled the data from the Api and added it into the ads collection. To do so you need a (or better multiple) access token. The script will automaticly handle rate limiting but you might not be able to pull on multiple threads if you don't have enough tokens.  
For more information just have a look at the `crawl.py` file.

## Contact

If you've got any more information regarding Facebook's API/Library or believe there are any legal issues with the distribution of this data please contact me: <Lejo_1@web.de> or open an Issue!
