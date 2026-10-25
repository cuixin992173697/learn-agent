from fastapi import FastAPI
from learn_agent.routers import conversations, messages

app = FastAPI(
    title="Learn Agent API",
    description="学习 FastAPI 多文件结构的 demo",
)

# 把两组路由挂到 app 上：
#   prefix —— 给这组接口加统一前缀（如 /conversations/...）
#   tags   —— 在 /docs 文档里按标签分组显示
app.include_router(conversations.router, prefix="/conversations", tags=["会话"])
app.include_router(messages.router, prefix="/messages", tags=["消息"])


@app.get("/", tags=["默认"])
def root():
    return {"status": "ok", "提示": "访问 /docs 查看接口文档"}
