"""Seniverse now/daily endpoints, adapted from ESP8266-Seniverse."""
from http_client import get_json, quote


class Weather:
    def __init__(self, key, location):
        self.key = key
        self.location = location

    def _request(self, endpoint):
        if not self.key or self.key == "YOUR_SENIVERSE_PRIVATE_KEY":
            raise ValueError("Set API key")
        path = "/v3/weather/%s.json?key=%s&location=%s&language=en&unit=c" % (
            endpoint, quote(self.key), quote(self.location))
        if endpoint == "daily":
            # The current Seniverse plan provides today plus the next two days.
            path += "&start=0&days=3"
        data = get_json("api.seniverse.com", path)
        if "results" not in data or not data["results"]:
            raise ValueError("API " + str(data.get("status_code", "no results")))
        return data["results"][0]

    def now(self):
        result = self._request("now")
        now = result["now"]
        return {"city": result["location"]["name"], "text": now["text"],
                "code": int(now["code"]), "temperature": int(now["temperature"]),
                "updated": result.get("last_update", "")}

    def daily(self):
        result = self._request("daily")
        days = result["daily"]
        if len(days) < 3:
            raise ValueError("Need 3 forecast days")
        return [{"date": day["date"], "text": day["text_day"],
                 "code": int(day["code_day"]), "low": int(day["low"]),
                 "high": int(day["high"])} for day in days[:3]]
