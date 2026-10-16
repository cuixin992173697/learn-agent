import os
import sys
from typing import Any

# Windows 控制台默认 GBK，遇到中文/emoji 会崩；切到 utf-8
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig


@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }


# glm-5.2 走 openai 兼容协议：显式指定 provider + key + base_url，建好 llm 对象再传给 create_agent
llm = init_chat_model(
    model="glm-5.2",
    model_provider="openai",
    api_key=os.environ["ZHIPU_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

agent = create_agent(
    llm,                       # ← 传 llm 对象，别传裸字符串 "glm-5.2"（会猜不出 provider）
    tools=[],                  # ← 原来是 [...](Ellipsis 占位)，这文件不需要工具，给空列表
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

print("（开始 4 轮对话，每轮调一次 API，总共约 30 秒，请稍候……）\n")

print("第1轮：自我介绍")
agent.invoke({"messages": "hi, my name is bob"}, config)
print("  ✓ 完成\n")

print("第2轮：写猫的诗")
agent.invoke({"messages": "write a short poem about cats"}, config)
print("  ✓ 完成\n")

print("第3轮：写狗的诗")
agent.invoke({"messages": "now do the same but for dogs"}, config)
print("  ✓ 完成\n")

print("第4轮：问名字（验证裁剪后还记得吗）")
final_response = agent.invoke({"messages": "what's my name?"}, config)

print("\n===== 最终回复 =====")
final_response["messages"][-1].pretty_print()
