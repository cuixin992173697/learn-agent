import os
import re
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()


from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.agents import create_agent

API_KEY = os.environ["ZHIPU_API_KEY"]

llm = init_chat_model(
    model="glm-5.2",
    model_provider="openai",
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/"
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
agent = create_agent(llm, tools=[calculate, get_current_time])

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
        start = len(messages) # 记住当前位置等下只打印新增的步骤

        # 触发 agent 的 ReAct 循环: 它会决定要不要调用工具
        result = agent.invoke({"messages": messages})
        messages = result["messages"]

        # 打印中间过程，看 agent 调了什么工具、拿到什么结果
        for m in messages[start:]:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    print(f"  🔧 调用工具 {tc['name']}，参数: {tc['args']}")
            elif isinstance(m, ToolMessage):
                print(f"  📋 工具返回: {m.content}")

        # 最后一条消息就是最终回复
        print(f"Agent: {messages[-1].content}\n")

if __name__ == "__main__":
    main()
