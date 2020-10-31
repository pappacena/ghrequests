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

## Customizing

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


## Using as a Flow Control

ghrequests can actually be used just as a flow control, regardless of doing
HTTP requests or not. 

All you need to do is implementing your
Request subclass accordingly, overriding `domain` property and `run` method:
  
```python
class MyRunner(ghrequests.Request):
    """This requester runs something on the database, and we want to limit
     it per target database."""
    def __init__(self, database, other_parameter):
        super().__init__()  # Don't forget to call super.
        self.database = database
        self.other_parameter = other_parameter

    @property
    def domain(self):
        # Target domain is the database where we will run the query.
        return self.database

    def run(self):
        # Fetch something from the database, for example.
        value = self.database.select("SELECT count FROM table LIMIT 1")[0]
        return value * self.other_parameter

requests = [
    MyRunner(db1, 5),
    MyRunner(db1, 15),
    MyRunner(db1, 25),
    MyRunner(db1, 35),
    MyRunner(db2, 5),
    MyRunner(db2, 15),
    MyRunner(db2, 25),
    MyRunner(db2, 35),
    # ...
]

# Send at most 2 request per target database:
ghrequests.request_all(requests, max_per_domain=2)
responses = [i.response for i in requests]
```

