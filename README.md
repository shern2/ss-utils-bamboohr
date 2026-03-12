# SS Utils BambooHR

A BambooHR API Python SDK focused on hiring-related API endpoints.

## Features

- **Hiring API**: Interact with BambooHR's hiring-related endpoints.
- **Async Support**: Built on `httpx` for high-performance asynchronous operations.
- **Type Safety**: Fully typed with Pydantic v2 models.
- **Robustness**: Built-in retry logic via `backoff`.

## Installation

```bash
uv add ss-utils-bamboohr
```

## Quick Start

```python
import asyncio
from ss_utils_bamboohr import BambooHRClient

async def main():
    client = BambooHRClient(
        company_domain="your-company",
        api_key="your-api-key"
    )
    
    # Fetch candidates
    candidates = await client.get_candidates()
    for candidate in candidates:
        print(f"Found candidate: {candidate.first_name} {candidate.last_name}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Development

```bash
just setup
```

## Testing

```bash
# Run unit tests
just test-unit

# Run integration tests (requires .env)
just test-integration
```

## Documentation

For more details on the available endpoints and schemas, refer to the [BambooHR API Documentation](https://documentation.bamboohr.com/docs/getting-started).

