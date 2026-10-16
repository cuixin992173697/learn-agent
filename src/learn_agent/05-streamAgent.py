import os
import re
import sys
from datetime import datetime

# Windows 控制台默认 GBK，遇到 emoji/中文会崩；切到 utf-8
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()


from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from langchain.agents import create_agent

API_KEY = os.environ["ZHIPU_API_KEY"]

llm = init_chat_model(
    model="glm-5.2",
    model_provider="openai",
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)


# ===== 1. 定义工具：用 @tool 把普通函数变成 LLM 能调用的工具 =====
@tool
def get_current_time() -> str:
    """获取当前的日期和时间。当用户问现在几点、今天日期时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculate(expression: str) -> str:
    """计算数学表达式，例如 '3 + 5 * 2'。只支持数字和 + - * / ( )。"""
    if not re.fullmatch(r"[\d\s+\-*/().]+", expression):
        return "只支持数字和 + - * / ( ) 运算符"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"计算失败：{e}"


# ===== 2. 组装成 Agent =====
agent = create_agent(
    llm,
    tools=[calculate, get_current_time],
    system_prompt="你是一个乐于助人的中文助手。当涉及时间或数学计算时，请主动调用对应工具，不要凭空猜测。",
)

def main() -> None:
    print("开始和 Agent 对话（输入 quit 退出）\n")
    messages = []

    while True:
        user_input = input("你：").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not user_input:
            continue

        messages.append(HumanMessage(content=user_input))

        final_messages = None
        answer_started = False  # 在第一段文字 token 前才打印 "Agent: "，避免标签悬空

        # 触发 agent 的 ReAct 循环（流式版）：
        # stream_mode 双模式 = messages 实时打印 + values 拿到最终完整状态用于下一轮历史
        for event in agent.stream(
            {"messages": messages},
            stream_mode=["messages", "values"],
        ):
            mode, payload = event
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk):
                    # (a) 决定调用工具的阶段：tool_call_chunks 里带 name
                    tool_call_chunks = getattr(chunk, "tool_call_chunks", None) or []
                    if tool_call_chunks:
                        for tc in tool_call_chunks:
                            if tc.get("name"):
                                print(f"  🔧 调用工具 {tc['name']}，参数: {tc.get('args')}")
                    # (b) 最终答案逐 token 流式
                    elif chunk.content:
                        if not answer_started:
                            print("Agent: ", end="", flush=True)
                            answer_started = True
                        print(chunk.content, end="", flush=True)
                # (c) 工具执行结果
                elif isinstance(chunk, ToolMessage):
                    print(f"  📋 工具返回: {chunk.content}")
            elif mode == "values":
                # values 每个步骤都吐完整消息列表，最后一次就是最终状态
                final_messages = payload.get("messages")

        # 用最终完整状态覆盖历史，下一轮带上对话（含工具调用/结果）
        if final_messages:
            messages = final_messages

        # 答复结束换行
        print()

if __name__ == "__main__":
    main()
