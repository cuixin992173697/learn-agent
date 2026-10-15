# 基础的langchain对话示例
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.chat_models import init_chat_model

API_KEY = os.environ["ZHIPU_API_KEY"]

llm = init_chat_model(
    model="glm-5.2",
    model_provider="openai",                       # ← 用字符串指定厂商
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

def main() -> None:
    print("开始和 GLM 对话（输入 quit 退出）\n")

    # 用一个列表保存对话历史，模型才能"记住"上下文，实现多轮对话
    messages = [SystemMessage(content="你是一个编程助手。")]

    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not user_input:
            continue

        # 1. 把用户的话加进历史
        messages.append(HumanMessage(content=user_input))
        # 2. 流式输出：逐块读取并实时打印
        print("GLM: ", end="", flush=True)
        full_response = ""
        for chunk in llm.stream(messages):
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
        print("\n")
        # 3. 把完整回复加入历史，下一轮接着聊
        messages.append(AIMessage(content=full_response))


if __name__ == "__main__":
    main()


