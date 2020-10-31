# -*- coding: utf-8 -*-
from gevent import monkey; monkey.patch_all()

from collections import defaultdict
import logging

from gevent.queue import Queue
from gevent.threading import Thread
import requests
from six.moves.urllib.parse import urlparse

__author__ = "pappacena"
__copyright__ = "pappacena"
__license__ = "mit"
logger = logging.getLogger(__name__)


class Request:
    def __init__(self, method, url, **kwargs):
        self.method = method
        self.url = url
        self.kwargs = kwargs
        self._response = None
        self.exception = None

    def send(self):
        try:
            self._response = requests.request(
                self.method, self.url, **self.kwargs)
        except Exception as e:
            self.exception = e

    @property
    def response(self):
        if self.exception is not None:
            raise self.exception
        return self._response

    @property
    def domain(self):
        return urlparse(self.url).netloc

    def __str__(self):
        return "<Request %s %s%s>" % (
            self.method.upper(), self.url,
            "" if not self.kwargs else " %s" % self.kwargs)


class Worker(Thread):
    def __init__(self, request_queue, domain, dispatcher):
        """

        :param request_queue: The queue of requests to execute.
        :param domain: Which domain key will this worker deal with.
        :param dispatcher: The dispatcher object that will be notified once
            this worker stops.
        """
        super(Worker, self).__init__()
        self.request_queue = request_queue
        self.domain = domain
        self.dispatcher = dispatcher

    def run(self):
        while True:
            request = self.request_queue.get()
            if request is None:
                logger.debug("Finishing worker %s: termination marker "
                             "received", request)
                # Once we finish running, notify the dispatcher, so it can
                # free up one worker spot.
                self.dispatcher.remove_worker(self)
                break
            request.send()


class Dispatcher:
    def __init__(self, max_connections=None, max_per_host=None):
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self.host_queues = defaultdict(lambda: Queue(self.max_per_host))
        self.host_workers = defaultdict(list)
        self.global_workers_count = 0

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
        domain_workers = self.host_workers[domain]

        # Reached max workers per host?
        limit = self.max_per_host
        if limit is not None and len(domain_workers) > limit:
            return False

        # Reached global limit?
        limit = self.max_connections
        if limit is not None and self.global_workers_count > limit:
            return False

        logger.debug("Starting new worker for domain '%s'", domain)
        worker = Worker(self.get_host_queue(request), domain, self)
        domain_workers.append(worker)
        self.global_workers_count += 1
        worker.start()
        return True

    def remove_worker(self, worker):
        """Removes the worker from our workers pool."""
        self.host_workers[worker.domain].remove(worker)
        self.global_workers_count -= 1

    def close_host_queues(self):
        for domain, queue in list(self.host_queues.items()):
            for _ in self.host_workers.get(domain):
                queue.put(None)

    def run(self, async_requests):
        for request in async_requests:
            host_queue = self.get_host_queue(request)
            host_queue.put(request)
            self.dispatch_host_worker(request)

        self.close_host_queues()

        for key, workers in self.host_workers.items():
            for worker in workers:
                worker.join()
