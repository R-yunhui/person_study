"""
LangChain DeepAgent 框架演示

演示内容：
  1. DeepAgent 的 built-in 能力：规划 (write_todos)、文件系统 (read/write_file)、子 Agent (task)
  2. FilesystemBackend —— 虚拟文件系统后端，Agent 的中间产物落盘
  3. 流式输出 —— 实时观察 Agent 思考和执行过程

使用方式：
  uv run python large_model/01_deep_agent_demo.py
"""

import os
import warnings

from dotenv import load_dotenv

from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# 静默 langgraph 内部 deprecation 警告
warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change",
)

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# FilesystemBackend —— DeepAgent 的虚拟文件系统后端
# ═══════════════════════════════════════════════════════════════
# DeepAgent 内部带有一套文件操作工具（write_file / read_file / edit_file / ls / glob / grep），
# FilesystemBackend 决定这些工具"写到哪里"：
#
#   - StateBackend()     → 内存中，进程结束就没了（默认）
#   - FilesystemBackend() → 落到本地磁盘，可调试、可复用
#   - StoreBackend()     → 持久化到 DB（跨会话）
#   - CompositeBackend() → 混合路由，不同路径走不同后端
#
# virtual_mode=False 表示直接操作真实文件系统路径（开发调试用）。
# 生产环境建议用 StateBackend 或 SandboxBackend。
# ═══════════════════════════════════════════════════════════════
filesystem_backend = FilesystemBackend(
    root_dir=os.path.join(os.path.dirname(__file__), "workspace"),
    virtual_mode=False,
)

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_CHAT_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
)

deep_agent = create_deep_agent(
    model=chat_model,
    tools=[],
    system_prompt="""你是一个深度研究助手，对于用户的每个问题：

1. 先用 write_todos 拆解任务
2. 搜索/分析相关信息
3. 把研究结果用 write_file 保存到 /research_report.md
4. 最后给用户一个简洁的总结

请始终遵循：先计划，再执行，再总结。""",
    backend=filesystem_backend,
)


def main() -> None:
    """
    LangChain DeepAgent 框架 深度研究助手 示例
    """
    
    # ── 流式输出 ──
    # stream_mode="values" 返回每次状态更新后的完整快照，
    # 能实时看到 Agent 的每一步操作（规划、工具调用、回复等）
    topic = "什么是 LangChain？它和 LangGraph 的关系是什么？"
    
    print(f"研究课题：{topic}\n")
    print("=" * 60)

    for chunk in deep_agent.stream(
        {"messages": [HumanMessage(content=topic)]},
        stream_mode="values",
    ):
        messages = chunk.get("messages", [])
        if messages:
            last_msg = messages[-1]
            msg_type = getattr(last_msg, "type", "?")
            content = getattr(last_msg, "content", "")

            # 只展示实际内容（跳过空消息和内部 tool 调用细节）
            if isinstance(content, str) and content.strip():
                # 截断过长的内容
                print(f"\n[{msg_type}] {content}")
            elif isinstance(content, list):
                # tool_calls 等结构化消息
                for item in content:
                    if isinstance(item, dict):
                        name = item.get("name", "")
                        args = str(item.get("args", ""))[:150]
                        if name:
                            print(f"\n[工具调用] {name}({args}...)")

    print("\n" + "=" * 60)
    print("执行完成。查看 workspace/ 目录下的中间文件。")


if __name__ == "__main__":
    main()
