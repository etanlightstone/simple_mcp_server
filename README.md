# Weather MCP Server

A FastAPI application that exposes current weather conditions and daily forecasts
from [WeatherAPI.com](https://www.weatherapi.com/) as
[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools.
Built with [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp).

## Quick start (local)

```bash
pip install -r requirements.txt
export WEATHER_API_KEY=your_key_here
python main.py
```

Open <http://localhost:8888> for interactive docs, code samples, and an API test
panel. The MCP endpoint is at <http://localhost:8888/mcp>.

## Deploying on Domino Data Lab

1. **Environment variables** – set `WEATHER_API_KEY` in the project settings.
   Optionally set `ROOT_PATH` to the URL prefix assigned by the platform
   (e.g. `/app/<run-id>`).

2. **Start command:**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8888
   ```

3. **Authentication** – Domino routes traffic through an nginx proxy that
   validates bearer tokens. Agents running inside Domino can obtain a token
   from the sidecar at `http://localhost:8899/access-token` and pass it in the
   `Authorization` header when connecting to the MCP endpoint.

## Available MCP tools

| Tool | Description |
|------|-------------|
| `get_current_weather` | Current conditions (temp, wind, humidity, UV, etc.) |
| `get_weather_forecast` | Today's forecast with hourly breakdown |

Both tools accept a `location` parameter – city name, zip code, lat/lon, etc.

## Project structure

```
main.py          – FastAPI app, weather endpoints, MCP mount
landing.html     – Self-documenting landing page with code samples + test panel
requirements.txt – Python dependencies
```
