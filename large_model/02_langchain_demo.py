"""LangChain 框架演示"""

import os
import base64

from dotenv import load_dotenv

# langchain 相关
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# 加载环境变量
load_dotenv()

chat_model = ChatOpenAI(
    model=os.getenv("QWEN_VLM_MODEL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL"),
    temperature=0.7,
    extra_body={"enable_thinking": False},
)


def pic_to_base64(pic_path: str) -> str:
    """将图片转换为 base64 编码"""
    try:
        with open(pic_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"将图片转换为 base64 编码失败: {e}")
        return ""


def chat(prompt: str, pic_path: str) -> str:
    """调用模型进行对话"""
    response = chat_model.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{pic_to_base64(pic_path)}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ]
            ),
        ]
    )
    return response.content


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: uv run python large_model/02_langchain_demo.py <图片路径> [提示词]")
        sys.exit(1)
    path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else "描述这张图片的内容"
    data = chat(query, path)
    print(data)
