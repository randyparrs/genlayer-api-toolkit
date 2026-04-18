# GenLayer API Toolkit

A reusable library of external API integrations for GenLayer Intelligent Contracts. Provides standardized access to crypto prices, weather, news, GitHub stats and URL health checks  all resolved through Optimistic Democracy consensus.

## What is this?

One thing I kept running into while building Intelligent Contracts is that every time you want to fetch external data you have to figure out the right equivalence tolerance from scratch. This toolkit solves that by providing ready-to-use patterns for 5 common API types, each with a tested tolerance rule that achieves reliable consensus.

Other developers can use this as a reference when integrating external APIs into their own contracts.

## Available APIs

| Function | Source | Equivalence Rule |
|----------|--------|-----------------|
| `get_crypto_price(coin_id)` | CoinGecko | ±2% price tolerance |
| `get_weather(city)` | wttr.in | ±3°C temperature |
| `get_news_summary(topic)` | Wikipedia | found field must match |
| `get_github_stats(owner, repo)` | GitHub API | ±10 stars, same language |
| `check_url_health(url)` | HTTP | ±500 chars content length |

## Examples

```
get_crypto_price("bitcoin")
→ {"coin": "bitcoin", "price_usd": 82543.21, "change_24h": 1.23, "found": true}

get_weather("London")
→ {"city": "London", "temp_c": 12, "condition": "Cloudy", "humidity": 78}

get_github_stats("genlayerlabs", "genlayer-studio")
→ {"repo": "genlayerlabs/genlayer-studio", "stars": 342, "language": "Python"}
```

## Why tolerance rules matter

Each API has different characteristics that affect how validators will see the data:

- **Crypto prices** change every second, so two validators running a few seconds apart will see slightly different prices  ±2% handles this
- **Weather** updates every few minutes  ±3°C covers normal variation
- **GitHub stars** can change between validator runs  ±10 covers new stars being added
- **Web content** can vary due to caching  ±500 chars handles minor differences

## Built with

- GenLayer Studio
- Python (GenLayer Intelligent Contract SDK)
- `gl.vm.run_nondet_unsafe` for Equivalence Principle
- Optimistic Democracy consensus

## How to run it

1. Go to [GenLayer Studio](https://studio.genlayer.com)
2. Create a new file and paste `genlayer_api_toolkit.py`
3. Set execution mode to Normal (Full Consensus)
4. Deploy with your address as `owner_address`
5. Call any of the API functions

Note: the contract in this repository uses the Address type in the constructor as required by genvm-lint. When deploying in GenLayer Studio use a version that receives str in the constructor and converts internally with Address(owner_address) since Studio requires primitive types to parse the contract schema correctly.

## Notes

This is part of the GenLayer Incentivized Builder Program, Tools & Infrastructure track. All 5 APIs were tested and achieved 100% consensus rate in GenLayer Studio.
