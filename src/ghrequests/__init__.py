# -*- coding: utf-8 -*-
from functools import partial

from ghrequests.requester import Dispatcher
from pkg_resources import get_distribution, DistributionNotFound
from .requester import Request

try:
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound

__all__ = [
    'get',
    'post',
    'put',
    'head',
    'patch',
    'delete',
    'request',
    'Request'
]

get = partial(Request, 'GET')
options = partial(Request, 'OPTIONS')
head = partial(Request, 'HEAD')
post = partial(Request, 'POST')
put = partial(Request, 'PUT')
patch = partial(Request, 'PATCH')
delete = partial(Request, 'DELETE')
request = Request


def request_all(requests, max_connections=None, max_per_domain=None):
    """
    Run all requests in parallel, respecting the given limits.


    :param max_connections: Global max simultaneous connections.
    :param max_per_domain: Max requests per host.
    """
    return Dispatcher(max_connections, max_per_domain).run(requests)
