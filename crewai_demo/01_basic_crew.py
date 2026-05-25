"""
CrewAI 基础 Demo — Agent + Task + Crew

流式输出：逐 token 打印模型响应。
"""

import os
from dotenv import load_dotenv

from crewai import Agent, Crew, Process, Task
from crewai import LLM

load_dotenv()

base_url = os.getenv("DASHSCOPE_BASE_URL")
api_key = os.getenv("DASHSCOPE_API_KEY")
model = os.getenv("QWEN_CHAT_MODEL", "qwen3.6-plus")


def create_llm() -> LLM | None:
    if base_url and api_key:
        return LLM(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0.7,
            stream=True,
        )
    return None


def basic_crew_demo():
    llm = create_llm()

    researcher = Agent(
        role="资深研究员",
        goal="发现并总结 {topic} 领域的最新进展",
        backstory="你是一名经验丰富的研究员，擅长从信息中提炼关键洞察。",
        llm=llm,
    )

    writer = Agent(
        role="技术作家",
        goal="将复杂技术内容写成通俗易懂的文章",
        backstory="你是一名出色的技术写手，能把晦涩的概念讲得清晰有趣。",
        llm=llm,
    )

    research_task = Task(
        description="研究 {topic} 领域的最新发展，找出 3 个关键趋势。",
        expected_output="返回 3 个关键趋势，每个趋势包含简要说明和影响分析。",
        agent=researcher,
    )

    write_task = Task(
        description="基于研究结果，写一篇面向技术读者的短文介绍 {topic}。",
        expected_output="一篇约 300 字的短文，语言通俗、结构清晰。",
        agent=writer,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        stream=True,  # kickoff() 返回 CrewStreamingOutput
    )

    # CrewStreamingOutput 是可迭代对象，逐 chunk 吐出 token
    #   chunk.content → 当前 token 文本
    #   遍历完后 .result → 最终完整输出
    streaming = crew.kickoff(inputs={"topic": "AI Agent 多智能体协作"})
    for chunk in streaming:
        if chunk.content:
            print(chunk.content, end="", flush=True)

    # 获取最终完整结果
    result = streaming.result
    print("\n" + "=" * 60)
    print("执行完成")


if __name__ == "__main__":
    basic_crew_demo()
