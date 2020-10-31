# ghrequests

[![Build Status](https://travis-ci.org/pappacena/ghrequests.svg?branch=main)](https://travis-ci.org/pappacena/ghrequests)
[![Version](https://img.shields.io/pypi/v/ghrequests.svg?colorB=blue)](https://pypi.org/project/ghrequests/)
[![PyVersion](https://img.shields.io/pypi/pyversions/ghrequests.svg?)](https://pypi.org/project/ghrequests/)

Python library for massive (but controlled) parallel HTTP calls using gevent and requests


## Description

Inspired in [grequests](https://github.com/spyoungtech/grequests/), this
library allows you to do massively parallel HTTP requests, but controlling
both the limit of simultaneous connections per target host and globally.

## Getting started

The usage is simple. First, install the library using pip:

```pip install ghrequests```

Then, your script needs to create the requests that should be sent, send
 them all and read the responses after:

```python
import ghrequests

urls = [
    "https://google.com", "https://canonical.com", "https://yahoo.com",
    "https://microsoft.com", "https://facebook.com", "https://python.org"
]
requests = [ghrequests.get(url) for url in urls]
ghrequests.request_all(requests, max_connections=10, max_per_domain=2)
responses = [i.response for i in requests]
```

## Customizing limit

By default, `max_per_domain` refers to the `urlparse(url).netloc` of your
 requested URLs, but this can be customized to be anything you want.
 
To limit the requests per HTTP method, for example, you could subclass
`ghrequests.Request` to do what you need:

```python
import ghrequests


class MyRequest(ghrequests.Request):
    @property
    def domain(self):
        return self.method


requests = [
    MyRequest("GET", "http://google.com"),
    MyRequest("POST", "https://some.url.com"),
    MyRequest("HEAD", "https://bla.foo.com"),
    # ... several other requests
]
ghrequests.request_all(requests, max_per_domain=2)
responses = [i.response for i in requests]
```

The above example should limit to have at most 2 `POST`, 2 `GET`, 2 `HEAD`
 (...) simultaneous requests at a time.
