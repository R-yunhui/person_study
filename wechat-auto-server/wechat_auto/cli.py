"""CLI 入口 — 启动 API 服务或单次操作"""

import typer
import uvicorn

from wechat_auto.api import app as fastapi_app
from wechat_auto.backends import create_backend
from wechat_auto.config import settings

app = typer.Typer(help="微信自动化工具")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="监听地址"),
    port: int = typer.Option(8000, "--port", "-p", help="监听端口"),
):
    """启动 FastAPI HTTP 服务。"""
    uvicorn.run(fastapi_app, host=host, port=port)


@app.command()
def send(
    contact: str = typer.Argument(..., help="联系人名称"),
    message: str = typer.Argument(..., help="消息内容"),
):
    """发送单条文本消息。"""
    ok = create_backend().send_text(contact, message)
    typer.echo(f"发送{'成功' if ok else '失败'}")


@app.command()
def file(
    contact: str = typer.Argument(..., help="联系人名称"),
    path: str = typer.Argument(..., help="文件路径"),
):
    """发送文件。"""
    ok = create_backend().send_file(contact, path)
    typer.echo(f"发送{'成功' if ok else '失败'}")


@app.command()
def image(
    contact: str = typer.Argument(..., help="联系人名称"),
    path: str = typer.Argument(..., help="图片路径"),
):
    """发送图片（显示为缩略图）。"""
    ok = create_backend().send_image(contact, path)
    typer.echo(f"发送{'成功' if ok else '失败'}")


@app.command()
def mention(
    group: str = typer.Argument(..., help="群聊名称"),
    mentions: str = typer.Argument(..., help="要 @ 的人，多个用逗号分隔"),
    message: str = typer.Argument(..., help="消息内容"),
):
    """在群聊中发送 @提及 消息。"""
    names = [m.strip() for m in mentions.split(",") if m.strip()]
    ok = create_backend().send_text_with_mention(group, names, message)
    typer.echo(f"发送{'成功' if ok else '失败'}")


@app.command()
def dump(
    max_count: int = typer.Option(30, "--max", "-n", help="控件数量上限"),
):
    """导出控件树（调试用）。"""
    controls = create_backend().dump_controls(max_count)
    for c in controls:
        typer.echo(f"[{c['index']}] {c['type']:20s} name={c['name']}")


@app.command()
def agent():
    """启动自动回复 Agent（轮询 → LLM → 回复）。"""
    from wechat_auto.agent import run as agent_run  # noqa: optional dep
    agent_run()


if __name__ == "__main__":
    app()
