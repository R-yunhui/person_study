"""
CrewAI vs LangChain — Thinking/Reasoning 配置对比

支持的 thinking 模式：
  - OpenAI o-series: reasoning_effort (low/medium/high)
  - Anthropic Claude: thinking dict (type + budget_tokens)
"""

# ==================== CrewAI ====================
from crewai import LLM as CrewLLM

# --- OpenAI: reasoning_effort ---
crew_openai = CrewLLM(
    model="openai/o3-mini",
    reasoning_effort="high",  # "low" | "medium" | "high"
)

# --- Anthropic: thinking dict ---
crew_anthropic = CrewLLM(
    model="anthropic/claude-sonnet-4-6",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 16000},  # 关闭 thinking 则去掉此参数
)

# --- 无 thinking 的普通模型 ---
crew_regular = CrewLLM(
    model="openai/gpt-4o",
    temperature=0.7,
)


# ==================== LangChain ====================
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# --- OpenAI: reasoning_effort ---
lc_openai = ChatOpenAI(
    model="o3-mini",
    reasoning_effort="high",
)

# --- Anthropic: thinking dict ---
lc_anthropic = ChatAnthropic(
    model="claude-sonnet-4-6",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 16000},
)

# --- 无 thinking ---
lc_regular = ChatOpenAI(model="gpt-4o", temperature=0.7)


# ==================== 差异分析 ====================
"""
┌──────────────┬────────────────────────────┬────────────────────────────┐
│              │ CrewAI LLM                 │ LangChain                 │
├──────────────┼────────────────────────────┼────────────────────────────│
│ 参数命名      │ 直接参数名                 │ 相同参数名                │
│ 模型前缀      │ 需要 (openai/o3-mini)      │ 不需要 (o3-mini)          │
│ thinking 开关 │ 加/删 thinking 参数         │ 加/删 thinking 参数       │
│ 关闭方式      │ 不传对应参数即可            │ 不传对应参数即可          │
│ vendor 适配   | LLM 内部根据 model 前缀     | 不同 Provider 类各自处理   │
│               │ 自动分发参数                │                           │
└──────────────┴────────────────────────────┴────────────────────────────┘

相同点：
  1. 参数名完全一致（reasoning_effort、thinking dict）
  2. 开关方式相同——传递参数=开启，不传=关闭

不同点：
  1. CrewAI 需要 model 前缀（如 openai/），LangChain 通过不同类区分
  2. CrewAI 用单个 LLM 类 + 前缀路由，LangChain 每个 Provider 独立类
  3. CrewAI 的 thinking 参数传递给底层 litellm，litellm 再映射到对应 SDK
  4. LangChain 直接操作各 Provider 的 SDK，参数更原生
"""
