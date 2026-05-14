"""微信自动回复 agent"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# langchain
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient


# mcp
mcp_client = MultiServerMCPClient(
    connections={
        "weixin": {
            "transport": "http",
            "url": "https://mcp.tavily.com/mcp/?tavilyApiKey=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",
        }
    }
)

llm = ChatOpenAI(
    model=os.environ.get("QWEN_CHAT_MODEL", "qwen3.5-plus"),
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"],
    temperature=0.85,
    extra_body={"enable_thinking": False},
)


async def create_custom_agent():
    async with mcp_client.session("weixin") as session:
        tools = await session.list_tools()
        print(f"tools: {len(tools)}")
        agent = create_agent(
            model=llm,
            tools=tools,
        )
        return agent


if __name__ == "__main__":
    asyncio.run(create_custom_agent())
