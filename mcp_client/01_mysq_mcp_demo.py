"""
接入 mysql mcp 服务
"""

import os
import asyncio

from dotenv import load_dotenv

# langchain 相关
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

# 加载环境变量
load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    extra_body={"enable_thinking": False},
    temperature=0.85,
    max_tokens=1000,
    streaming=True,
)

mcp_client = MultiServerMCPClient(
    connections={
        "mcp_809961086783558": {
            "transport": "http",
            "url": "http://192.168.2.131:30080/agent-toolkit/openapi/mcp/809961086783558/mcp",
        },
    }
)


async def get_mcp_tools():
    """获取 mcp 工具"""
    try:
        tools = await mcp_client.get_tools()
        print(f"加载了 {len(tools)} 个工具:")
        for t in tools:
            print(f"  - {t.name}: {t.description}")
        return tools
    except Exception as e:
        print(f"获取 mcp 工具失败: {e}")
        return None


async def main(query: str):
    """
    主流程

    query: 用户问题
    """
    try:
        tools = await get_mcp_tools()
        if not tools:
            return

        agent = create_agent(
            model=chat_model,
            tools=tools,
        )
        result = await agent.ainvoke(input={"messages": [HumanMessage(content=query)]})
        print(result["messages"][-1].content)
    except Exception as e:
        print(f"执行异常: {str(e)}")


if __name__ == "__main__":

    while True:
        query = input("请输入查询语句: ")
        if query == "exit":
            break
        asyncio.run(main(query))
    print("程序结束")
