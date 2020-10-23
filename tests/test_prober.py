from unittest.case import TestCase

from gevent.queue import Queue
from pyhttpprober.prober import Prober


class TestProberQueues(TestCase):
    def test_get_host_queue_no_limit(self):
        prober = Prober(max_per_host=None)
        q1 = prober.get_host_queue("http://google.com")
        q2 = prober.get_host_queue("http://yahoo.com")
        self.assertIsNotNone(q1)
        self.assertIs(q1, q2)

    def test_get_host_queue_with_limit(self):
        prober = Prober(max_per_host=2)
        q1 = prober.get_host_queue("http://google.com")
        q2 = prober.get_host_queue("http://yahoo.com")
        self.assertIsInstance(q1, Queue)
        self.assertIsInstance(q2, Queue)
        self.assertIsNot(q1, q2)
