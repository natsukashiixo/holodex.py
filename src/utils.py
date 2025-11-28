from datetime import datetime, timezone
from operator import attrgetter

# py-cord utils

def pt(timestamp):
    if timestamp:
        return datetime.fromisoformat(timestamp)
    return None

def fdt(dt, /, style = None):
    if isinstance(dt, datetime.time):
        dt = datetime.datetime.combine(datetime.now(), dt)
    if style is None:
        return f"<t:{int(dt.timestamp())}>"
    return f"<t:{int(dt.timestamp())}:{style}>"

def find(predicate, seq):
    for element in seq:
        if predicate(element):
            return element
    return None

def get(iterable, **attrs):
    _all = all
    attrget = attrgetter

    if len(attrs) == 1:
        k, v = attrs.popitem()
        pred = attrget(k.replace("__", "."))
        for elem in iterable:
            if pred(elem) == v:
                return elem
        return None

    converted = [
        (attrget(attr.replace("__", ".")), value) for attr, value in attrs.items()
    ]

    for elem in iterable:
        if _all(pred(elem) == value for pred, value in converted):
            return elem
    return None

def ed(string):
    return string

# etc

def filter_params(params: dict):
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}

def fix_url(url):
    if not url.startswith("/"):
        url = "/" + url
    return API_URL + url

def parse_int(string: str | None) -> int | None:
    if not string:
        return None
    return int(str(string).replace(",", ""))

def parse_time(string: str | None) -> datetime | None:
    if not string:
        return None
    return pt(string.split("+")[0].split(".")[0]).replace(tzinfo=timezone.utc)

async def parse_type(data):
    c = str(data.content_type)
    if "json" in c:
        return await data.json()
    if "text" in c:
        return await data.text()
    return data