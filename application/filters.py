from datetime import datetime


def clean_int_filter(s):
    if s == "":
        s = "0"
    if isinstance(s, str):
        s = s.replace(",", "")
        return int(s)
    return s


def to_float_filter(s):
    if s == "":
        s = "0"
    if isinstance(s, str):
        s = s.replace(",", "")
        return float(s)
    return s


def days_since(d):
    today = datetime.now()
    if not isinstance(d, datetime):
        print("DATE: ")
        print(d)
        d = datetime.strptime(d, "%Y-%m-%d")
    delta = today - d
    return delta.days


def split_filter(s, d):
    return s.split(d)
