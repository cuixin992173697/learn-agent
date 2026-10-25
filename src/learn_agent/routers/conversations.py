from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 内存模拟数据库（学习阶段先用假数据，后续再接 PostgreSQL）
conversations_db: list[dict] = [
    {"id": 1, "agent_name": "weather-agent"},
    {"id": 2, "agent_name": "code-reviewer"},
    {"id": 3, "agent_name": "translator"},
]


class ConversationCreate(BaseModel):
    """创建会话的请求体模型：声明接口需要什么字段、什么类型"""
    agent_name: str


@router.get("/")
def list_conversations():
    """列出所有会话"""
    return conversations_db


@router.get("/{conversation_id}")
def get_conversation(conversation_id: int):
    """获取单个会话，不存在则返回 404"""
    for c in conversations_db:
        if c["id"] == conversation_id:
            return c
    raise HTTPException(status_code=404, detail="会话不存在")


@router.post("/")
def create_conversation(body: ConversationCreate):
    """创建会话，id 自动递增。body 由 FastAPI 从请求体解析并校验"""
    new_id = max((c["id"] for c in conversations_db), default=0) + 1
    new_conv = {"id": new_id, "agent_name": body.agent_name}
    conversations_db.append(new_conv)
    return new_conv
