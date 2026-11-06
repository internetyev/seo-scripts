# Internetyev's SEO Python Scripts

Andriy Terentyev, SEO consultant: https://terentyev.net

In SEO for over 15 years in-house and as a consultant. SEO Strategy Advisor at KyivIndependent.com, former SEO Lead at Kiwi.com, and before that COO, CTO and CEO in tech startups. Niches: travel, news, SaaS and ecommerce.

For the last three years I have worked solo, doing the work of a full SEO team with my proprietary SEO tools ([corgiseo.com](https://corgiseo.com)) and a set of AI agents. Write me for:

- technical SEO of large sites,
- SEO automation and QA monitoring,
- AI-assisted content pipelines,
- SEO competitive intelligence, and
- custom AI agents for on-page SEO and linkbuilding, various SEO, GEO, SEM and social media tasks.

Pet project: https://corgiseo.com, an SEO data layer for AI agents.

LinkedIn: https://linkedin.com/in/terentyev

Here is my collection of SEO scripts on python that I find useful.
Some of these scripts are written by me, sometimes with a bit of help from AI. 

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

PS: this is an older version of the script, which I am planning to update by September 20, 2024. 

The easiest way to set up regular tracking of articles that are ranking on "Top Stories" is by setting up PythonAnywhere.com account with recurring tasks.  


## Sources of original scripts:

* https://www.jcchouinard.com/get-number-of-indexed-pages-on-multiple-sites-with-python/

* https://github.com/scraperapi/scraperapi-code-examples

