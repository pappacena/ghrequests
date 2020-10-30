from gevent import monkey; monkey.patch_all()

from collections import defaultdict
import logging
import traceback

from gevent.queue import Queue
from gevent.threading import Thread
import requests
from six.moves.urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Request:
    def __init__(self, method, url, **kwargs):
        self.method = method
        self.url = url
        self.kwargs = kwargs
        self.response = None
        self.traceback = None
        self.exception = None

    def send(self):
        try:
            self.response = requests.request(
                self.method, self.url, **self.kwargs)
        except Exception as e:
            self.traceback = traceback.format_exc()
            self.exception = e

    @property
    def domain(self):
        return urlparse(self.url).netloc

    def __str__(self):
        return "<Request %s %s%s>" % (
            self.method.upper(), self.url,
            "" if not self.kwargs else " %s" % self.kwargs)


class Worker(Thread):
    def __init__(self, request_queue):
        super(Worker, self).__init__()
        self.request_queue = request_queue

    def run(self):
        while True:
            request = self.request_queue.get()
            if request is None:
                logger.debug("Finishing worker %s: termination marker "
                             "received", request)
                break
            request.send()


class Prober:
    def __init__(self, max_connections=None, max_per_host=None):
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self.host_queues = defaultdict(lambda: Queue(self.max_per_host))
        self.host_workers = defaultdict(list)

    def get_domain_key(self, request):
        """
        Returns the domain queue used on both self.host_queues and
        self.host_workers.

        If we are not limiting connections per host, this method returns
        "None", indicating that both workers and queues should not be
        splitted between domains.
        """
        return request.domain if self.max_per_host else None

    def get_host_queue(self, request):
        domain = self.get_domain_key(request)
        return self.host_queues[domain]

    def dispatch_host_worker(self, request):
        """Create and start a new worker for the request if we didn't reach
        our limites yet. Does nothing if we reached our simultaneous
        request limits.

        :param request: The Request object that triggered the need for a
            worker.
        :return: True if we started a new worker. False otherwise.
        """
        domain = self.get_domain_key(request)
        workers = self.host_workers[domain]
        limit = (self.max_per_host if self.max_per_host
                 else self.max_connections)
        if limit is not None and len(workers) > limit:
            return False
        logger.debug("Starting new worker for domain '%s'", domain)
        worker = Worker(self.get_host_queue(request))
        workers.append(worker)
        worker.start()
        return True

    def close_host_queues(self):
        for domain, queue in list(self.host_queues.items()):
            for _ in self.host_workers.get(domain):
                queue.put(None)

    def probe(self, async_requests):
        for request in async_requests:
            host_queue = self.get_host_queue(request)
            host_queue.put(request)
            self.dispatch_host_worker(request)

        self.close_host_queues()

        for key, workers in self.host_workers.items():
            for worker in workers:
                worker.join()
