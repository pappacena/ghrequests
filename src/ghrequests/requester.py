# -*- coding: utf-8 -*-
from gevent import monkey; monkey.patch_all(thread=False)

from collections import defaultdict
import logging

import gevent
from gevent.queue import Queue
from gevent import Greenlet
import requests
from six.moves.urllib.parse import urlparse

__author__ = "pappacena"
__copyright__ = "pappacena"
__license__ = "mit"
logger = logging.getLogger(__name__)


class Request:
    def __init__(self, method=None, url=None, **kwargs):
        self.method = method
        self.url = url
        self.kwargs = kwargs
        self._response = None
        self.exception = None

    def send(self):
        try:
            self._response = self.run()
        except Exception as e:
            self.exception = e

    def run(self):
        return requests.request(
            self.method, self.url, **self.kwargs)

    @property
    def response(self):
        if self.exception is not None:
            raise self.exception
        return self._response

    @property
    def domain(self):
        return urlparse(self.url).netloc

    def __str__(self):
        return "<Request [%s] %s %s%s>" % (
            self.domain, self.method.upper(), self.url,
            "" if not self.kwargs else " %s" % self.kwargs)


class Worker(Greenlet):
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

    def _run(self):
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

    def __str__(self):
        return "Worker for %s" % self.domain


class Dispatcher:
    def __init__(self, max_connections=None, max_per_domain=None):
        self.max_connections = max_connections
        self.max_per_domain = max_per_domain
        self.domain_queues = defaultdict(Queue)
        self.domain_workers = defaultdict(list)
        self.all_workers = set()
        self.workers_to_join = Queue()
        self.pending_worker_domains = set()

    def get_domain_key(self, request):
        """
        Returns the domain queue used on both self.domain_queues and
        self.domain_workers.

        If we are not limiting connections per host, this method returns
        "None", indicating that both workers and queues should not be
        splitted between domains.
        """
        return request.domain if self.max_per_domain else None

    def get_host_queue(self, request):
        domain = self.get_domain_key(request)
        return self.domain_queues[domain]

    def dispatch_host_worker(self, domain, close_queue=False):
        """Create and start a new worker for the request if we didn't reach
        our limites yet. Does nothing if we reached our simultaneous
        request limits.

        :param domain: Create a worker for this specific domain.
        :param close_queue: If close_queue is True, a None terminator will
            be added to the worker's queue if it will be created.
        :return: A tuple with the created worker and a flag indicating
            if we reached the global limit.
        """
        domain_workers = self.domain_workers[domain]

        # Reached max workers per host?
        limit = self.max_per_domain
        if limit is not None and len(domain_workers) >= limit:
            return None, False

        # Reached global limit?
        limit = self.max_connections
        if limit is not None and len(self.all_workers) >= limit:
            return None, True

        logger.debug("Starting new worker for domain '%s'", domain)
        queue = self.domain_queues[domain]
        worker = Worker(queue, domain, self)
        domain_workers.append(worker)
        self.all_workers.add(worker)
        worker.start()
        if close_queue:
            queue.put(None)
        return worker, False

    def remove_worker(self, worker):
        """Removes the worker from our workers pool."""
        self.domain_workers[worker.domain].remove(worker)
        self.all_workers.remove(worker)
        self.workers_to_join.put(worker)
        # If we still have requests to do for other domains, let's start
        # a new worker.
        if len(self.pending_worker_domains):
            domain = next(iter(self.pending_worker_domains))
            # Start a new worker if possible, and since all requests are
            # already in the queue, we will need a "close_queue" terminator
            # there.
            self.dispatch_host_worker(domain, close_queue=True)
            limit_reached = (
                    self.max_per_domain is not None and
                    len(self.domain_workers[domain]) >= self.max_per_domain)
            if limit_reached or self.domain_queues[domain].empty():
                # If we already have reached max workers or there is no
                # request left for this domain, it's not pending anymore.
                try:
                    self.pending_worker_domains.remove(domain)
                except KeyError:
                    pass
        # We are done with the workers. Let's close the "worker joiner" queue.
        if not len(self.all_workers):
            self.workers_to_join.put(None)

    def close_domain_queues(self, workers_created_per_queue):
        for queue, workers_count in workers_created_per_queue.items():
            for _ in range(workers_count):
                queue.put(None)

    def run(self, async_requests):
        workers_created_per_queue = defaultdict(int)
        for request in async_requests:
            domain = self.get_domain_key(request)
            host_queue = self.get_host_queue(request)
            host_queue.put(request)
            worker, global_limit_reached = self.dispatch_host_worker(domain)
            if worker is not None:
                # We have created a worker.
                workers_created_per_queue[host_queue] += 1
            elif (global_limit_reached and
                  self.max_per_domain is not None and
                  len(self.domain_workers[domain]) < self.max_per_domain):
                # No worker created, global limit reached and we still do not
                # have all workers we want for that domain. We will need a new
                # worker for this domain as soon as possible.
                self.pending_worker_domains.add(domain)

        self.close_domain_queues(workers_created_per_queue)

        while True:
            gevent.sleep(0)
            worker = self.workers_to_join.get()
            if worker is None:
                break
            worker.join()
