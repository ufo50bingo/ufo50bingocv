import math

import urllib.parse


def get_hrs_mins_secs(time: float) -> tuple[int, int, int]:
    hrs = math.trunc(time / 3600)
    remaining = time - 3600 * hrs
    mins = math.trunc(remaining / 60)
    remaining = remaining - 60 * mins
    secs = round(remaining)
    return (hrs, mins, secs)


def get_url_at_time(url: str, time: float) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.hostname
    query = urllib.parse.parse_qsl(parsed.query)

    if domain is None:
        raise Exception(f"No domain found for url: {url}")
    if "twitch.tv" in domain:
        [hrs, mins, secs] = get_hrs_mins_secs(time)
        if hrs > 0:
            time_param = f"{hrs}h{mins}m{secs}s"
        elif mins > 0:
            time_param = f"{mins}m{secs}s"
        else:
            time_param = f"{secs}s"
        query.append(("t", time_param))
    elif "youtube.com" in domain or "youtu.be" in domain:
        time_param = f"{int(time)}"
        query.append(("t", time_param))
    else:
        raise Exception(f"Unexpected domain {domain} for url {url}")

    parsed_list = list(parsed)
    parsed_list[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(parsed_list)
