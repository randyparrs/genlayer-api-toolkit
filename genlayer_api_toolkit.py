# { "Depends": "py-genlayer:test" }

import json
from genlayer import *


class GenLayerAPIToolkit(gl.Contract):

    owner: Address
    query_count: u256
    query_log: DynArray[str]  # "type:input:result"

    def __init__(self, owner_address: Address):
        self.owner = owner_address
        self.query_count = u256(0)

    @gl.public.view
    def get_query_count(self) -> u256:
        return self.query_count

    @gl.public.view
    def get_last_query(self) -> str:
        count = len(self.query_log)
        if count == 0:
            return "No queries yet"
        return self.query_log[count - 1]

    @gl.public.view
    def get_toolkit_summary(self) -> str:
        return (
            f"GenLayer API Toolkit\n"
            f"Total Queries: {int(self.query_count)}\n"
            f"Available APIs:\n"
            f"  get_crypto_price(symbol) -> CoinGecko\n"
            f"  get_weather(city) -> wttr.in\n"
            f"  get_news_summary(topic) -> Wikipedia\n"
            f"  get_github_stats(owner, repo) -> GitHub\n"
            f"  check_url_health(url) -> HTTP status"
        )

    @gl.public.write
    def get_crypto_price(self, coin_id: str) -> str:
        def leader_fn():
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            response = gl.nondet.web.get(url)
            data = json.loads(response.body.decode("utf-8"))

            if coin_id not in data:
                return json.dumps({"coin": coin_id, "price_usd": 0, "change_24h": 0, "found": False})

            price = data[coin_id].get("usd", 0)
            change = data[coin_id].get("usd_24h_change", 0)

            return json.dumps({
                "coin": coin_id,
                "price_usd": round(price, 2),
                "change_24h": round(change, 2),
                "found": True
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if not leader_data["found"]:
                    return not validator_data["found"]
                leader_price = leader_data["price_usd"]
                validator_price = validator_data["price_usd"]
                if leader_price == 0:
                    return validator_price == 0
                # price within 2%: abs(diff) * 100 <= price * 2
                return abs(leader_price - validator_price) * 100 <= leader_price * 2
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self._log_query("crypto", coin_id, raw)
        return raw

    @gl.public.write
    def get_weather(self, city: str) -> str:
        def leader_fn():
            safe_city = city.replace(" ", "+")
            url = f"https://wttr.in/{safe_city}?format=j1"
            response = gl.nondet.web.get(url)
            data = json.loads(response.body.decode("utf-8"))

            current = data["current_condition"][0]
            temp_c = int(current.get("temp_C", 0))
            temp_f = int(current.get("temp_F", 0))
            condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
            humidity = int(current.get("humidity", 0))
            wind_kmph = int(current.get("windspeedKmph", 0))

            return json.dumps({
                "city": city,
                "temp_c": temp_c,
                "temp_f": temp_f,
                "condition": condition,
                "humidity": humidity,
                "wind_kmph": wind_kmph
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                return abs(leader_data["temp_c"] - validator_data["temp_c"]) <= 3
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self._log_query("weather", city, raw)
        return raw

    @gl.public.write
    def get_news_summary(self, topic: str) -> str:
        def leader_fn():
            url = "https://en.wikipedia.org/wiki/Portal:Current_events"
            response = gl.nondet.web.get(url)
            web_data = response.body.decode("utf-8")[:3000]

            prompt = f"""You are a news summarizer. Based on the Wikipedia current events page below,
find and summarize the most relevant recent news about: "{topic}"

Wikipedia Current Events:
{web_data}

Respond ONLY with a JSON object:
{{
  "topic": "{topic}",
  "summary": "2-3 sentence summary of relevant recent events",
  "found": true
}}

If no relevant news found, set found to false and summary to "No recent news found".
No extra text."""

            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            return json.dumps({
                "topic": data.get("topic", topic),
                "summary": data.get("summary", ""),
                "found": data.get("found", False)
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                return leader_data["found"] == validator_data["found"]
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self._log_query("news", topic, raw)
        return raw

    @gl.public.write
    def get_github_stats(self, owner: str, repo: str) -> str:
        def leader_fn():
            url = f"https://api.github.com/repos/{owner}/{repo}"
            response = gl.nondet.web.get(url)
            data = json.loads(response.body.decode("utf-8"))

            if "message" in data:
                return json.dumps({"found": False, "error": data["message"]})

            return json.dumps({
                "repo": f"{owner}/{repo}",
                "stars": int(data.get("stargazers_count", 0)),
                "forks": int(data.get("forks_count", 0)),
                "language": data.get("language", "Unknown"),
                "description": data.get("description", "")[:100],
                "open_issues": int(data.get("open_issues_count", 0)),
                "found": True
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if not leader_data["found"]:
                    return not validator_data["found"]
                if abs(leader_data["stars"] - validator_data["stars"]) > 10:
                    return False
                return leader_data["language"] == validator_data["language"]
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self._log_query("github", f"{owner}/{repo}", raw)
        return raw

    @gl.public.write
    def check_url_health(self, url: str) -> str:
        def leader_fn():
            try:
                response = gl.nondet.web.get(url)
                content = response.body.decode("utf-8")
                return json.dumps({
                    "url": url,
                    "accessible": True,
                    "content_length": len(content),
                    "preview": content[:100].replace("\n", " ")
                }, sort_keys=True)
            except Exception as e:
                return json.dumps({
                    "url": url,
                    "accessible": False,
                    "content_length": 0,
                    "preview": str(e)[:100]
                }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if leader_data["accessible"] != validator_data["accessible"]:
                    return False
                return abs(leader_data["content_length"] - validator_data["content_length"]) <= 500
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self._log_query("health", url, raw)
        return raw

    def _log_query(self, query_type: str, input_data: str, result: str) -> None:
        safe_input = input_data[:50].replace(":", "-")
        safe_result = result[:100].replace(":", "-")
        self.query_log.append(f"{query_type}:{safe_input}:{safe_result}")
        self.query_count = u256(int(self.query_count) + 1)
