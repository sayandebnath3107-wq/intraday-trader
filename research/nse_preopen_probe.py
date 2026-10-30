"""Can GitHub's servers read NSE's pre-open (opening auction) data? Prints a short summary."""
import json
import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
     "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
     "Referer": "https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market"}
s = requests.Session()
for url in ("https://www.nseindia.com", "https://www.nseindia.com/market-data/pre-open-market-cm-and-emerge-market"):
    r = s.get(url, headers=H, timeout=20)
    print("GET", url, r.status_code, len(r.content))
for key in ("NIFTY", "ALL"):
    r = s.get(f"https://www.nseindia.com/api/market-data-pre-open?key={key}", headers=H, timeout=20)
    print("API", key, r.status_code, len(r.content))
    try:
        j = r.json()
        print(" top-level keys:", list(j)[:12])
        rows = j.get("data", [])
        print(" rows:", len(rows))
        if rows:
            print(" first row:", json.dumps(rows[0])[:1500])
        for k, v in j.items():
            if k != "data":
                print(" ", k, ":", json.dumps(v)[:300])
    except Exception as e:
        print(" not json:", e, r.text[:300])
