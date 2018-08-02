import scrapy
from scrapy import signals
from scrapy.mail import MailSender
from scrapy.utils.markup import remove_tags
from jinja2 import Template


class JobSearchSpider(scrapy.Spider):
    """Job Search Spider - A class that will scrape jobs sites based on
    technologies.
    """

    # Set spider vars
    name = "job_search"
    query_tags = None
    matched_jobs = []
    send_to_email = "some-name@email.com"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Set up the spider.

        :param crawler:
        :param args:
        :param kwargs:
        :return:
        """

        # set spider to catch spider_closed from signal.
        spider = super(JobSearchSpider, cls).from_crawler(crawler, *args,
                                                          **kwargs)
        crawler.signals.connect(spider.spider_closed,
                                signal=signals.spider_closed)
        return spider

    def start_requests(self):
        """ This function is the starting point to implementing crawl logic.

        :return:
        """
        # Set job search url to scrape
        url_to_crawl = 'https://stackoverflow.com/jobs?sort=i'

        # Get query tags from input
        self.query_tags = self.get_formatted_query_tags()

        # If query_tags exits then clean and build into url
        if self.query_tags is not None:
            # Append query tags to url
            url_to_crawl = f"{url_to_crawl}&q={self.query_tags}"

        # Let's go scraping for jobs
        yield scrapy.Request(url=url_to_crawl,
                             callback=self.parse_job_search_page)

    def parse_job_search_page(self, response):
        """Return a generator that parses the job search result page

        :param response:
        :return:
        """

        # Gather job link urls to crawl
        job_urls = response.css(
            ".js-search-results .listResults "
            ".job-details__spaced a.job-link::attr(href)").extract()

        # Crawl through job pages and parse job data
        for index, job_url in enumerate(job_urls):
            yield response.follow(job_url, self.parse_job_detail_page)

    def parse_job_detail_page(self, response):
        """Return a generator that parses the job details page

        :param response:
        :return:
        """

        # Get job technology tags
        parsed_tags = response.css(
            "a.post-tag.job-link.no-tag-menu::text").extract()

        # Find matched technology tags from query tags
        matched_tags = [tag for tag in parsed_tags if tag in self.query_tags]

        # If there are matched tags, collect job details and store into list
        if matched_tags:
            parsed_job_position = response.xpath("//h1/a/text()").extract()[0]
            parsed_company = \
                response.xpath(
                    "//h1/following-sibling::div/a/text()").extract()[0]
            parsed_job_description = response.xpath(
                "//h2[text()='Job description']"
                "/following-sibling::div").extract()
            parsed_job_description = remove_tags(parsed_job_description[0])
            self.matched_jobs.append({'company': parsed_company,
                                      'position': parsed_job_position,
                                      'matched_tags': matched_tags,
                                      'tags': parsed_tags,
                                      'description': parsed_job_description,
                                      'url': response.url
                                      })
            self.logger.info(
                f"--------- Found matched tags: {','.join(matched_tags)} "
                f"in job page: {response.url} ")

            yield self.matched_jobs

    def spider_closed(self, spider):
        """Once the spider has finished crawling this function will
        trigger and allow us to define some closing operations.

        Send an email of found jobs; if any.
        """

        if self.matched_jobs:
            self.email_jobs()

        self.logger.debug(f'Spider closed: {spider.name}')

    def email_jobs(self):
        """Email jobs

        :return:
        """

        # Setup mailer
        mailer = MailSender.from_settings(self.settings)

        subject = f"StackOverflow.com Jobs Curated By Scrapy - " \
                  f"query tags: {', '.join(self.query_tags)}"
        message = self.render_email_template(
            template_vars={"matched_jobs": self.matched_jobs})

        self.logger.info(f"Sending email: {message}")

        mailer.send(to=[self.send_to_email],
                    subject=subject,
                    body=message)

    @staticmethod
    def render_email_template(template_vars):
        """Render email template

        :param template_vars:
        :return:
        """

        # Create a job space string that repeats the colon character 100 times
        job_spacer = ':' * 100

        # Set email template
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

        # Render template with data
        message = template.render(matched_jobs=template_vars["matched_jobs"],
                                  job_spacer=job_spacer)

        return message

    def get_formatted_query_tags(self):
        """Get formatted query tags

        :return:
        """

        # Get query_tags param argument from command line
        query_tags = getattr(self, 'query_tags', None)

        # Clean tags for processing
        query_tags.replace(',', '+')
        query_tags.replace(' ', '+')

        # Format into list
        query_tags = query_tags.split("+")

        return query_tags
