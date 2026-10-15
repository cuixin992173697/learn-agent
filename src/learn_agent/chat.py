# 基础的langchain对话示例
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

API_KEY = os.environ["ZHIPU_API_KEY"]

llm = ChatOpenAI(
    model="glm-5.2",
    api_key=API_KEY,
    base_url = "https://open.bigmodel.cn/api/paas/v4/"
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
        # 2. 把整段历史发给模型，拿到回复
        response = llm.invoke(messages)
        # 3. 打印回复key
        print(f"GLM: {response.content}\n")
        # 4. 把回复也加进历史，下一轮就能接着聊
        messages.append(response)


if __name__ == "__main__":
    main()


