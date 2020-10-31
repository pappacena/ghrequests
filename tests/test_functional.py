import datetime
from unittest.case import TestCase

import ghrequests

# Test URLs for some known websites.
test_urls = [
    "https://google.com", "https://canonical.com", "https://yahoo.com",
    "https://microsoft.com", "https://facebook.com", "https://python.org"
]


class TestFunctionalRequester(TestCase):
    def test_requester_no_limit(self):
        requests = [ghrequests.head(url) for url in test_urls]
        ghrequests.request_all(requests)
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)

    def test_requester_connection_limit(self):
        # Include 8 requests that takes 1 second each. Since the max
        # requests is 2, we should take at least 4 seconds to
        # complete.
        urls = test_urls + (["http://httpbin.org/delay/1"] * 8)
        requests = [ghrequests.head(url) for url in urls]

        start = datetime.datetime.now()
        ghrequests.request_all(requests, max_connections=2)
        end = datetime.datetime.now()
        self.assertGreaterEqual(end - start, datetime.timedelta(seconds=4))
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)

    def test_requester_connection_limit_per_host(self):
        # Include 8 requests that takes 1 second each. Since the max
        # requests per host is 2, we should take at least 4 seconds to
        # complete.
        urls = test_urls + (["http://httpbin.org/delay/1"] * 8)
        requests = [ghrequests.head(url) for url in urls]

        start = datetime.datetime.now()
        ghrequests.request_all(requests, max_per_host=2)
        end = datetime.datetime.now()
        self.assertGreaterEqual(end - start, datetime.timedelta(seconds=4))
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)
