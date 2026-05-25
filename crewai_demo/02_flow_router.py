"""
CrewAI Flow Demo — Flow + State + Router

展示 CrewAI v1.14 推荐的 Flow 模式：
  - Flow 管理状态和执行顺序
  - @router 条件路由
  - 结构化状态 (Pydantic)
  - Crew 作为 Flow 内部步骤
"""

import json
from pydantic import BaseModel

from crewai import Agent, Crew, Process, Task
from crewai import LLM
from crewai.flow.flow import Flow, listen, or_, router, start


def create_llm():
    """读取环境变量配置 LLM"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    base_url = os.getenv("DASHSCOPE_BASE_URL")
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("QWEN_CHAT_MODEL", "qwen3.6-plus")
    flash = os.getenv("QWEN_FLASH_MODEL", "qwen3.6-27b-fp8")

    if base_url and api_key:
        return (
            LLM(
                model=f"openai/{model}",
                base_url=base_url,
                api_key=api_key,
                temperature=0.7,
            ),
            LLM(
                model=f"openai/{flash}",
                base_url=base_url,
                api_key=api_key,
                temperature=0.3,
            ),
        )
    return LLM(model="gpt-4o-mini"), LLM(model="gpt-4o-mini")


# ========== 结构化状态 ==========


class ReportState(BaseModel):
    topic: str = ""
    research_result: str = ""
    quality_score: int = 0
    final_report: str = ""


# ========== Flow ==========


class ReportFlow(Flow[ReportState]):
    """用 Flow 编排：选题 → 研究 → 质量检查 → 输出"""

    llm, flash_llm = create_llm()

    @start()
    def prepare_topic(self):
        """准备研究主题（可接收外部输入）"""
        # 如果未传入 topic，让 LLM 自动生成一个
        if not self.state.topic:
            from litellm import completion

            resp = completion(
                model=f"openai/{self.llm.model}",
                base_url=self.llm.base_url,
                api_key=self.llm.api_key,
                messages=[
                    {
                        "role": "user",
                        "content": "推荐一个 2026 年值得研究的技术话题，只返回话题名称。",
                    }
                ],
            )
            self.state.topic = resp["choices"][0]["message"]["content"].strip()
        print(f"\n📌 研究主题：{self.state.topic}")

    @listen(prepare_topic)
    def research_topic(self):
        """Crew 协作研究"""
        researcher = Agent(
            role="高级研究员",
            goal="提供关于 {topic} 的深度研究",
            backstory="你是一名顶级技术研究员。",
            llm=self.llm,
        )
        reviewer = Agent(
            role="质量审核员",
            goal="检查研究结果的质量和准确性",
            backstory="你负责把关研究质量，确保结果可靠。",
            llm=self.flash_llm,
        )

        research = Task(
            description=f"深入研究 {self.state.topic}，找出核心技术原理、应用场景和未来趋势。",
            expected_output="结构化的研究报告，包含技术原理、应用场景、未来趋势三部分。",
            agent=researcher,
        )
        review = Task(
            description="审核研究报告，确保内容准确、结构清晰。给出质量评分(1-10)。",
            expected_output="审核意见 + 质量评分。",
            agent=reviewer,
        )

        crew = Crew(
            agents=[researcher, reviewer],
            tasks=[research, review],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff(inputs={"topic": self.state.topic})
        self.state.research_result = result.raw

    @router(research_topic)
    def quality_check(self):
        """基于研究结果中的质量评分做条件路由"""
        # 从结果中提取评分
        text = self.state.research_result.lower()
        for i in range(10, 0, -1):
            if f"评分：{i}" in text or f"评分: {i}" in text or f"质量评分：{i}" in text:
                self.state.quality_score = i
                break
        if self.state.quality_score == 0:
            # 尝试用 LLM 提取评分
            self.state.quality_score = 6  # 默认中等

        print(f"\n⭐ 质量评分：{self.state.quality_score}/10")
        if self.state.quality_score >= 7:
            return "accepted"
        return "needs_revision"

    @listen("needs_revision")
    def revise_report(self):
        """质量不达标时润色改进"""
        improver = Agent(
            role="内容优化专家",
            goal="提升技术报告的质量",
            backstory="你擅长改进技术写作。",
            llm=self.llm,
        )
        improve_task = Task(
            description=f"优化以下研究报告，提升清晰度和完整性：\n{self.state.research_result}",
            expected_output="优化后的完整报告。",
            agent=improver,
        )
        crew = Crew(agents=[improver], tasks=[improve_task], verbose=True)
        result = crew.kickoff()
        self.state.research_result = result.raw

    @listen("accepted")
    def final_output(self):
        """生成最终报告"""
        writer = Agent(
            role="技术撰稿人",
            goal="撰写高质量技术报告",
            backstory="你是业界知名的技术作者。",
            llm=self.llm,
        )
        write_task = Task(
            description=f"基于以下研究内容，写一份完整的技术报告：\n{self.state.research_result}",
            expected_output="格式规范的 Markdown 技术报告，包含标题、摘要、正文和结论。",
            agent=writer,
        )
        crew = Crew(agents=[writer], tasks=[write_task], verbose=True)
        result = crew.kickoff()
        self.state.final_report = result.raw
        return self.state.final_report

    @listen(or_(revise_report, final_output))
    def done(self):
        print("\n" + "=" * 60)
        print("最终报告：")
        print(self.state.final_report)
        print(f"\n📊 状态摘要：{self.state.model_dump_json(indent=2)}")


def run():
    flow = ReportFlow()
    flow.kickoff()


def run_with_topic(topic: str):
    flow = ReportFlow()
    flow.kickoff(inputs={"topic": topic})


if __name__ == "__main__":
    # run("AI 大模型在医疗领域的应用")
    run()
