# Internetyev's SEO Python Scripts

Hi!
My name is Andriy Terentyev, I am SEO consultant focusing on online travel. ex-SEO Lead at Kiwi.com, and ex-COO of Hotelscan.com

Here is my collection of SEO scripts on python that I find useful.
I have not written majority of them, but modified them significantly. 

## Fetch number of indexed pages from a list of domains

**[fetch-n-of-results.py](n-of-results/fetch-n-of-results.py)**

The script:
* takes a list of domains from a CSV file named [domains.csv][n-of-results/domains.csv],
* uses ScraperAPI.com to scrape the number of indexed pages from Google,
* saves the result in [n-of-results/n-of-results.csv] 

Before you start: 
* [register at ScraperAPI.com](https://www.scraperapi.com/signup?fp_ref=niels31) -- registration is free, and you get 5000 free API credits per month,
* rename `renameto-config-py.py` to `config.py`,
* add the ScraperAPI API key into `config.py`,
* add your list of domains in `domains.csv` without removing the first line `domains`.

## Fetch list of results from 'Top Stories' featured snippet ##

The script:
* takes the list of keywords and crawl locations from news-keywords-tracking.csv;
* fetches Google SERP for this list of keywords;
* saves the links of articles that rank in "Top Stories" featured snippet into a CSV.

Before you start:
* register at DataForSeo.com to obtain API credentials.
* add your API keys in top-stories-fetch.py

The easiest way to set up regular tracking of articles that are ranking on "Top Stories" is by setting up PythonAnywhere.com account with recurring tasks.  



## Sources of original scripts:

* https://www.jcchouinard.com/get-number-of-indexed-pages-on-multiple-sites-with-python/

* https://github.com/scraperapi/scraperapi-code-examples

