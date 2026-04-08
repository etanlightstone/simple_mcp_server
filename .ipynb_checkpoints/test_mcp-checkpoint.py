## TBD
import asyncio
import requests
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP


# -- Domino platform: fetch a short-lived bearer token ------------------
# This helper calls the Domino sidecar running inside every Domino app
# container.  Remove the headers= argument when running outside Domino.
def get_domino_auth_headers() -> dict:
    resp = requests.get("http://localhost:8899/access-token", timeout=2)
    token = resp.text.strip()
    if not token.startswith("Bearer "):
        token = f"Bearer {token}"
    return {"Authorization": token}
# -----------------------------------------------------------------------


server = MCPServerStreamableHTTP(
    url="https://apps.cloud-dogfood.domino.tech/apps/403c7f11-77da-41a5-bb16-a638488c9eef/mcp",
    headers=get_domino_auth_headers(),   # remove when running locally
)

agent = Agent("openai:gpt-5.4-mini", toolsets=[server])


async def main():
    async with agent:
        result = await agent.run(
            "What is the weather like in San Francisco right now?"
        )
        print(result.output)


asyncio.run(main())