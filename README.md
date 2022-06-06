# Internetyev's SEO Python Scripts

Hi!
My name is Andriy Terentyev, I work as SEO Lead at Kiwi.com

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


## Sources of original scripts:

* https://www.jcchouinard.com/get-number-of-indexed-pages-on-multiple-sites-with-python/

* https://github.com/scraperapi/scraperapi-code-examples

