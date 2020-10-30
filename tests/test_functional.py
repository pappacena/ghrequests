import datetime
from unittest.case import TestCase

from pyhttpprober.prober import Prober, Request

# Test URLs for some known websites.
test_urls = [
    "https://google.com", "https://canonical.com", "https://yahoo.com",
    "https://microsoft.com", "https://facebook.com", "https://python.org"
]


class TestFunctionalProber(TestCase):
    def test_probe_no_limit(self):
        prober = Prober()
        requests = [Request('head', url) for url in test_urls]
        prober.probe(requests)
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)

    def test_probe_connection_limit(self):
        prober = Prober(max_connections=2)
        # Include 8 requests that takes 1 second each. Since the max
        # requests is 2, we should take at least 4 seconds to
        # complete.
        urls = test_urls + (["http://httpbin.org/delay/1"] * 8)
        requests = [Request('head', url) for url in urls]

        start = datetime.datetime.now()
        prober.probe(requests)
        end = datetime.datetime.now()
        self.assertGreaterEqual(end - start, datetime.timedelta(seconds=4))
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)

    def test_probe_connection_limit_per_host(self):
        prober = Prober(max_per_host=2)
        # Include 8 requests that takes 1 second each. Since the max
        # requests per host is 2, we should take at least 4 seconds to
        # complete.
        urls = test_urls + (["http://httpbin.org/delay/1"] * 8)
        requests = [Request('head', url) for url in urls]

        start = datetime.datetime.now()
        prober.probe(requests)
        end = datetime.datetime.now()
        self.assertGreaterEqual(end - start, datetime.timedelta(seconds=4))
        for request in requests:
            self.assertIsNotNone(
                request.response, "%s didn't finish" % request.url)
