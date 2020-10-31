# ghrequests

[![Build Status](https://travis-ci.org/pappacena/ghrequests.svg?branch=main)](https://travis-ci.org/pappacena/ghrequests)


Python library for massive (but controlled) parallel HTTP calls using gevent and requests


## Description

Inspired in [grequests](https://github.com/spyoungtech/grequests/), this
library allows you to do massively parallel HTTP requests, but controlling
both the limit of simultaneous connections per target host and globally.

The usage is simple:


```python
urls = [
    "https://google.com", "https://canonical.com", "https://yahoo.com",
    "https://microsoft.com", "https://facebook.com", "https://python.org"
]
requests = [ghrequests.get(url) for url in urls]
ghrequests.request_all(requests, max_connections=10, max_per_host=2)
responses = [i.response for i in requests]
```
