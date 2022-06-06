import requests
import pandas as pd
import concurrent.futures
from urllib.parse import urlencode
import bs4
import requests as rq



# 
# SCRAPER SETTINGS

# You need to define the following values below:

# - API_KEY --> Find this on your dashboard, or signup here to create a 
#                 free account here https://www.scraperapi.com/signup?fp_ref=niels31

                
# - NUM_RETRIES --> We recommend setting this to 5 retries. For most sites 
#                 95% of your requests will be successful on the first try,
#                 and 99% after 3 retries. 
                
# - NUM_THREADS --> Set this equal to the number of concurrent threads available
#                 in your plan. For reference: Free Plan (5 threads), Hobby Plan (10 threads),
#                 Startup Plan (25 threads), Business Plan (50 threads), 
#                 Enterprise Plan (up to 5,000 threads).

# 


API_KEY = '4775cb8179c3e11bacff64983a44d8c5'
NUM_RETRIES = 3
NUM_THREADS = 5



#export domain list from CSV

df_domains = pd.read_csv("competitors-domains.csv")

#convert dataframe to list
df_domains_values = df_domains["domain_id"].values
list_of_domains = df_domains_values.tolist() 
print(list_of_domains)

# Example: list of urls to scrape
# list_of_urls = [
#     'lastminute.kiwi.com',
#     'stansteadairport.kiwi.com'
#     ]



#create google URLs
url_template = "https://www.google.com/search?q=site%3A"
list_of_urls =  [url_template + d for d in list_of_domains]


## we will store the scraped data in this list
indexed_pages = []

# Just for reference: xpath for number of pages
#xpath = '//*[@id="result-stats"]'



#### PARSING NUMBER OF PAGES FROM STRING #####

def split_n_of_results (results):
    if (str(results).find("About ")>0) & (str(results).find("results")>0):
        results = str(results).split('About ')[1].split(' results')[0]
    elif (str(results).find("About ")<0) & (str(results).find("results")>=0):
        results = str(results).split('result-stats">')[1].split(' results')[0]
    elif (str(results).find("1 result")>0):
        results = "1"
    else:
        results = "0"  # domain is not active or an error
    results = int(results.replace(",",""))
    print("pages: ", results)
    return results

def scrape_url(url, domain_url):
    # 
    # SEND REQUESTS TO SCRAPER API AND PARSE DATA FROM THE HTML RESPONSE
    
    # INPUT/OUTPUT: Takes a single url as input, and appends the scraped data to the "scraped_quotes" list.
    # METHOD: Takes the input url, requests it via scraperapi and keeps retrying the request until it gets a 
    # successful response (200 or 404 status code) or up to the number of retries you define in NUM_RETRIES. 
    # If it did yield a successful response then it parses the data from the HTML response and adds it to the
    # "scraped_quotes" list. You can easily reconfigure this to store the scraped data in a database.
    # 
    
    params = {
        'api_key': API_KEY, 
        'url': url,
        'device_type': 'desktop'
        }

    # send request to scraperapi, and automatically retry failed requests
    for _ in range(NUM_RETRIES):
        try:
            response = requests.get('http://api.scraperapi.com/', params=urlencode(params))
            if response.status_code in [200, 404]:
                ## escape for loop if the API returns a successful response
                break
        except requests.exceptions.ConnectionError:
            response = ''
    
    
    ## parse data if 200 status code (successful response)
    if response.status_code == 200:



        
        #
        # parsing code 
        #
        
        html_response = response.text
        soup = bs4.BeautifulSoup(html_response)
        scraped_result = str(soup.find("div", { "id" : "result-stats" }))
        number_of_pages = split_n_of_results(scraped_result)
        indexed_pages.append ({
            'site': domain_url,
            'indexed_pages': number_of_pages
        })


# """
# CONFIGURE CONCURRENT THREADS

# Create thread pools up to the NUM_THREADS you define above and splits the urls you
# want to scrape amongst these threads until complete. Takes as input:

# - max_workers --> the maximum number of threads it will create. Here we set it to the
#                 value we defined in NUM_THREADS.
                
# - function to execute --> the first input to the executor.map() function is the function
#                 we want to execute in each thread. Here we input the "scrape_url(url)"" 
#                 function which accepts a single url as input.
                
# - input list --> the second input to the executor.map() function is the data we want to
#                 be split amongst the threads created. Here we input the "list_of_urls" we
#                 want to scrape.

# """

with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
     executor.map(scrape_url, list_of_urls,list_of_domains)

# SINGLE THREAD VERSION 

# i = 0
# for d in list_of_domains:
#     scrape_url(list_of_urls[i],list_of_domains[i])
#     print(str(i) + d + ": " + str(indexed_pages))
#     i += 1

# move to CSV
df = pd.DataFrame(indexed_pages)
df.to_csv('competitors_indexed_pages.csv')
