import json
import os
import urllib.request
import urllib.parse
from urllib.error import HTTPError

key = os.environ.get("ODDS_API_KEY", "").strip()
if not key:
    raise SystemExit("ODDS_API_KEY missing")
url = "https://api.the-odds-api.com/v4/sports/?" + urllib.parse.urlencode({"apiKey": key})
try:
    with urllib.request.urlopen(url, timeout=20) as response:
        sports = json.load(response)
        print("API connection OK")
        print("Remaining credits:", response.headers.get("x-requests-remaining", "unknown"))
        for sport in sports:
            if sport.get("group") == "Soccer" and sport.get("active"):
                print(sport["key"])
except HTTPError as exc:
    raise SystemExit(f"API HTTP status: {exc.code}") from None
except Exception:
    raise SystemExit("API connection or response error") from None
