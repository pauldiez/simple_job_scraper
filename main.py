
"""A script to run app/script from debugger."""
from scrapy import cmdline
cmdline.execute("scrapy crawl job_search -a query_tags=scrapy".split())