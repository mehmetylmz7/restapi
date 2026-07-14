from datetime import datetime


def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")
