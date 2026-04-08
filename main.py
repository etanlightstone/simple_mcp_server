import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_BASE_URL = "http://api.weatherapi.com/v1"


# ---------------------------------------------------------------------------
# Response models – clean, well-named fields that LLMs can reason about easily
# ---------------------------------------------------------------------------

class Location(BaseModel):
    name: str
    region: str
    country: str
    local_time: str = Field(..., description="Local date and time at the location")


class CurrentWeather(BaseModel):
    location: Location
    temperature_f: float
    temperature_c: float
    feels_like_f: float
    feels_like_c: float
    condition: str = Field(..., description="Plain-English weather condition, e.g. 'Partly cloudy'")
    wind_mph: float
    wind_kph: float
    wind_direction: str
    humidity_pct: int
    uv_index: float
    visibility_miles: float
    visibility_km: float
    pressure_mb: float
    precipitation_mm: float
    cloud_cover_pct: int


class DaySummary(BaseModel):
    date: str
    condition: str
    high_f: float
    low_f: float
    high_c: float
    low_c: float
    avg_temp_f: float
    avg_temp_c: float
    max_wind_mph: float
    total_precip_mm: float
    avg_humidity_pct: float
    chance_of_rain_pct: int
    uv_index: float


class HourForecast(BaseModel):
    time: str
    temp_f: float
    temp_c: float
    condition: str
    chance_of_rain_pct: int
    wind_mph: float
    humidity_pct: int


class ForecastResponse(BaseModel):
    location: Location
    summary: DaySummary
    hourly: list[HourForecast]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Weather MCP Server",
    description="MCP-compatible weather API wrapping WeatherAPI.com",
    root_path=os.environ.get("ROOT_PATH", ""),
)


async def _call_weather_api(endpoint: str, params: dict) -> dict:
    if not WEATHER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="WEATHER_API_KEY environment variable is not configured on the server.",
        )
    params["key"] = WEATHER_API_KEY
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{WEATHER_BASE_URL}/{endpoint}", params=params)
        if resp.status_code != 200:
            try:
                msg = resp.json().get("error", {}).get("message", resp.text)
            except Exception:
                msg = resp.text
            raise HTTPException(status_code=resp.status_code, detail=msg)
        return resp.json()


@app.get(
    "/weather/current",
    operation_id="get_current_weather",
    tags=["weather"],
    response_model=CurrentWeather,
    summary="Get current weather conditions",
)
async def get_current_weather(
    location: str = Query(
        ...,
        description=(
            "Location to query. Accepts city name ('London'), "
            "US zip ('90210'), UK postcode ('SW1'), "
            "lat/lon ('48.85,2.35'), or IP address."
        ),
    ),
) -> CurrentWeather:
    """Return current weather conditions for a location including temperature,
    wind, humidity, UV index, visibility, and cloud cover."""
    data = await _call_weather_api("current.json", {"q": location})
    loc = data["location"]
    cur = data["current"]
    return CurrentWeather(
        location=Location(
            name=loc["name"], region=loc["region"],
            country=loc["country"], local_time=loc["localtime"],
        ),
        temperature_f=cur["temp_f"],
        temperature_c=cur["temp_c"],
        feels_like_f=cur["feelslike_f"],
        feels_like_c=cur["feelslike_c"],
        condition=cur["condition"]["text"],
        wind_mph=cur["wind_mph"],
        wind_kph=cur["wind_kph"],
        wind_direction=cur["wind_dir"],
        humidity_pct=cur["humidity"],
        uv_index=cur["uv"],
        visibility_miles=cur["vis_miles"],
        visibility_km=cur["vis_km"],
        pressure_mb=cur["pressure_mb"],
        precipitation_mm=cur["precip_mm"],
        cloud_cover_pct=cur["cloud"],
    )


@app.get(
    "/weather/forecast",
    operation_id="get_weather_forecast",
    tags=["weather"],
    response_model=ForecastResponse,
    summary="Get today's weather forecast",
)
async def get_weather_forecast(
    location: str = Query(
        ...,
        description=(
            "Location to query. Accepts city name ('London'), "
            "US zip ('90210'), UK postcode ('SW1'), "
            "lat/lon ('48.85,2.35'), or IP address."
        ),
    ),
) -> ForecastResponse:
    """Return today's weather forecast for a location with a daily summary
    (high/low temps, rain chance, UV) and an hourly breakdown."""
    data = await _call_weather_api("forecast.json", {"q": location, "days": 1})
    loc = data["location"]
    day_data = data["forecast"]["forecastday"][0]
    day = day_data["day"]

    hourly = [
        HourForecast(
            time=h["time"],
            temp_f=h["temp_f"],
            temp_c=h["temp_c"],
            condition=h["condition"]["text"],
            chance_of_rain_pct=int(h["chance_of_rain"]),
            wind_mph=h["wind_mph"],
            humidity_pct=h["humidity"],
        )
        for h in day_data["hour"]
    ]

    return ForecastResponse(
        location=Location(
            name=loc["name"], region=loc["region"],
            country=loc["country"], local_time=loc["localtime"],
        ),
        summary=DaySummary(
            date=day_data["date"],
            condition=day["condition"]["text"],
            high_f=day["maxtemp_f"],
            low_f=day["mintemp_f"],
            high_c=day["maxtemp_c"],
            low_c=day["mintemp_c"],
            avg_temp_f=day["avgtemp_f"],
            avg_temp_c=day["avgtemp_c"],
            max_wind_mph=day["maxwind_mph"],
            total_precip_mm=day["totalprecip_mm"],
            avg_humidity_pct=day["avghumidity"],
            chance_of_rain_pct=int(day["daily_chance_of_rain"]),
            uv_index=day["uv"],
        ),
        hourly=hourly,
    )


# ---------------------------------------------------------------------------
# Landing page – served at the root, excluded from MCP tool list
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing():
    html_path = Path(__file__).parent / "landing.html"
    return HTMLResponse(html_path.read_text())


app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


# ---------------------------------------------------------------------------
# MCP server – exposes only the weather-tagged endpoints as MCP tools
# ---------------------------------------------------------------------------

from fastapi_mcp import FastApiMCP  # noqa: E402

mcp = FastApiMCP(
    app,
    name="Weather MCP Server",
    description=(
        "Get current weather conditions and today's forecast "
        "for any location worldwide, powered by WeatherAPI.com"
    ),
    include_tags=["weather"],
)
mcp.mount_http()


# ---------------------------------------------------------------------------
# Local dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
