from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 内存模拟数据库
messages_db: list[dict] = [
    {"id": 1, "conversation_id": 1, "role": "user", "content": "今天北京天气怎么样？"},
    {"id": 2, "conversation_id": 1, "role": "assistant", "content": "北京今天晴，最高气温 22 度。"},
    {"id": 3, "conversation_id": 2, "role": "user", "content": "帮我 review 这段代码"},
]


class MessageCreate(BaseModel):
    """创建消息的请求体模型"""
    conversation_id: int
    role: str
    content: str


@router.get("/")
def list_messages(conversation_id: int | None = None):
    """列出所有消息；可用 ?conversation_id=1 过滤某个会话的消息"""
    if conversation_id is not None:
        return [m for m in messages_db if m["conversation_id"] == conversation_id]
    return messages_db


@router.get("/{message_id}")
def get_message(message_id: int):
    """获取单条消息，不存在则返回 404"""
    for m in messages_db:
        if m["id"] == message_id:
            return m
    raise HTTPException(status_code=404, detail="消息不存在")


@router.post("/")
def create_message(body: MessageCreate):
    """创建消息，id 自动递增"""
    new_id = max((m["id"] for m in messages_db), default=0) + 1
    # body.model_dump() 把 Pydantic 模型转成 dict，再拼上 id
    new_msg = {"id": new_id, **body.model_dump()}
    messages_db.append(new_msg)
    return new_msg
