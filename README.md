# About This App

This is a sample project using the Scrapy library from ScrapingHub.com to find job postings via stackoverflow.com based on specific technologies. Any job postings found are then emailed.


# Install app instructions

* Configure mail server settings in [settings.py](https://bitbucket.org/pdiez/scrapy_job_search/src/master/scrapy_project/settings.py)

* Install commands
* ```bash
    $ pip install scrapy
    $ pip install jinja2
    $ scrapy crawl job_search -a query_tags=scrapy
    ```
* Run command 
    * Argument params
        * query_tags - technology tags to search for
* ```bash
    $ scrapy crawl job_search -a query_tags=scrapy
    ```

