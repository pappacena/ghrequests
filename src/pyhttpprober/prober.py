from gevent.pool import  Pool
from gevent.queue import Queue
from grequests import send
from six.moves.urllib.parse import urlparse


class Prober:
    def __init__(self, max_connections=None, max_per_host=None):
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self.host_pools = {}
        self.pool = Pool(max_connections)

    def get_host_queue(self, url):
        """Returns which queue should be used for the given URL"""
        if self.max_per_host is None:
            key = None
        else:
            key = urlparse(url).netloc
        if key not in self.host_pools:
            self.host_pools[key] = Queue(self.max_per_host)
        return self.host_pools[key]

    def probe(self, urls):
        pass
