import scrapy
from scrapy import signals
from scrapy.mail import MailSender
from scrapy.utils.markup import remove_tags
from jinja2 import Template


class JobSearchSpider(scrapy.Spider):
    # set spider vars
    name = "job_search"
    query_tags = None
    matched_jobs = []
    send_to_email = "some-name@email.com"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):

        # set spider to catch spider_closed to signal.
        spider = super(JobSearchSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def start_requests(self):
        """ this function is the starting point to implementing crawl logic
        """

        # set job search url to scrape
        url_to_crawl = 'https://stackoverflow.com/jobs?sort=i'

        # get query tags
        self.query_tags = self.get_formatted_query_tags()

        # if query_tags exits then clean and build into url
        if self.query_tags is not None:
            # append query tags to url
            url_to_crawl = f"{url_to_crawl}&q={self.query_tags}"

        # let's go scraping for jobs
        yield scrapy.Request(url=url_to_crawl, callback=self.parse_job_search_page)

    def parse_job_search_page(self, response):

        # gather job link urls to crawl
        job_urls = response.css(".js-search-results .listResults .job-details__spaced a.job-link::attr(href)").extract()

        # crawl through job pages and parse job data
        for index, job_url in enumerate(job_urls):
            yield response.follow(job_url, self.parse_job_detail_page)

    def parse_job_detail_page(self, response):

        # get job technology tags
        parsed_tags = response.css("a.post-tag.job-link.no-tag-menu::text").extract()

        # find matched technology tags from query tags
        matched_tags = [tag for tag in parsed_tags if tag in self.query_tags]

        # if there are matched tags, collect job details and store into list
        if matched_tags:
            parsed_job_position = response.xpath("//h1/a/text()").extract()[0]
            parsed_company = response.xpath("//h1/following-sibling::div/a/text()").extract()[0]
            parsed_job_description = response.xpath("//h2[text()='Job description']/following-sibling::div").extract()
            parsed_job_description = remove_tags(parsed_job_description[0])
            self.matched_jobs.append({'company': parsed_company,
                                      'position': parsed_job_position,
                                      'matched_tags': matched_tags,
                                      'tags': parsed_tags,
                                      'description': parsed_job_description,
                                      'url': response.url
                                      })
            self.logger.info(
                f"--------- Found matched tags: {','.join(matched_tags)} in job page: {response.url} ")
            yield self.matched_jobs

    def spider_closed(self, spider):
        """Once the spider has finished crawling this signal function will trigger and allow us to define
        some closing operations as we please.
        """

        # email jobs
        self.email_jobs()

        # log end of signal
        self.logger.debug(f'Spider closed: {spider.name}')

    def email_jobs(self):

        # setup mailer
        mailer = MailSender.from_settings(self.settings)

        # set mail vars
        subject = f"StackOverflow.com Jobs Curated By Scrapy - query tags: {', '.join(self.query_tags)}"
        message = self.render_email_template(template_vars={"matched_jobs": self.matched_jobs})

        # log mail message
        self.logger.info(f"Spider closed: {message}")

        # send email
        mailer.send(to=[self.send_to_email],
                    subject=subject,
                    body=message)

    @staticmethod
    def render_email_template(template_vars):

        # create a job space string that repeats the colon character 100 times
        job_spacer = ':' * 100

        # set email template
        template = Template("{% for matched_job in matched_jobs %}"
                            "Company: {{ matched_job.company }}\t\n\t\n"
                            "Position: {{ matched_job.position }}\t\n\t\n"
                            "Tags: {{ matched_job.tags }}\t\n\t\n"
                            "Description: {{ matched_job.description }}\t\n\t\n"
                            "Url: {{ matched_job.url }}\t\n\t\n"
                            "\t\n\t\n\t\n\t\n"
                            "{{ job_spacer }}"
                            "\t\n\t\n\t\n\t\n"
                            "{% endfor %}")

        # generate message from email populate
        message = template.render(matched_jobs=template_vars["matched_jobs"], job_spacer=job_spacer)

        # return message
        return message

    def get_formatted_query_tags(self):

        # get query_tags param argument from command line
        query_tags = getattr(self, 'query_tags', None)

        # clean tags for processing
        query_tags.replace(',', '+')
        query_tags.replace(' ', '+')

        # format into list
        query_tags = query_tags.split("+")

        return query_tags
