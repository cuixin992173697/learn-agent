import os
import sys
from typing import Literal

# Windows 控制台默认 GBK，遇到 emoji/中文会崩；切到 utf-8
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field, ValidationError

API_KEY = os.environ["ZHIPU_API_KEY"]

llm = init_chat_model(
    model="glm-5.2",
    model_provider="openai",
    api_key=API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)


# ===== 1. 用 Pydantic 定义"输出结构" =====
# 普通聊天模型回的是一坨自由文字；结构化输出让它回"固定形状的数据"，方便程序直接用。
# 每个字段都带 description，作用跟 @tool 的 docstring 一样：告诉模型这个字段该填什么。
class Review(BaseModel):
    """从一条商品评论里提取的结构化信息"""

    product: str = Field(description="评论里提到的商品名称")
    rating: int = Field(description="评分，1~5 的整数", ge=1, le=5)  # ge/le 限制范围
    sentiment: Literal["好评", "中评", "差评"] = Field(description="情感倾向，只能三选一")
    summary: str = Field(description="用一句话总结这条评论")


# ===== 2. 把普通 llm 包成"结构化输出模型" =====
# with_structured_output 返回一个新模型：调它 .invoke 直接得到 Review 对象，而不是一坨文字。
# method="function_calling" 是关键：glm-5.2 默认走 JSON Schema 模式容易回纯文本，
#   改成函数调用方式（它本来就支持 @tool）就稳了。不同模型要试不同 method。
struct_llm = llm.with_structured_output(Review, method="function_calling")


# ===== 3. 固定例子：同一结构、不同输入 =====
EXAMPLES = [
    "刚买的蓝牙耳机音质超棒，续航也长，必须给5分，强烈推荐！",
    "这款保温杯居然漏水，做工太差了，只能给1分，很失望。",
    "鼠标手感一般，凑合用吧，3分。",
]


def extract_and_print(text: str) -> None:
    """对一条评论做结构化提取并打印结果。"""
    result = struct_llm.invoke(text)            # 返回的是 Review 对象，不是字符串
    print(f"  → 商品：{result.product}")
    print(f"  → 评分：{result.rating}（类型 {type(result.rating).__name__}）")  # 注意是 int 不是 str
    print(f"  → 情感：{result.sentiment}")
    print(f"  → 总结：{result.summary}")
    print(f"  → 整体 dict：{result.model_dump()}\n")   # model_dump() 把对象转回普通字典


def main() -> None:
    print("===== 固定例子：看看结构化输出长啥样 =====\n")
    for text in EXAMPLES:
        print(f"评论：{text}")
        extract_and_print(text)

    print("===== 互动：你输入一条评论，看它怎么提取 =====")
    print("（输入 quit 退出）\n")
    while True:
        user_input = input("评论：").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not user_input:
            continue
        try:
            extract_and_print(user_input)
        except ValidationError as e:
            # 结构化输出会"校验"结果：模型填的字段不合规（比如评分给了6）就会被拦下
            print(f"  ⚠️ 模型返回的数据没通过校验：\n{e}\n")


if __name__ == "__main__":
    main()
