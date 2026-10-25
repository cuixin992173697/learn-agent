# PostgreSQL 学习笔记

围绕 `conversations`（会话）和 `messages`（消息）两张表，记录建表、插入、查询的常用写法。
两张表通过 `messages.conversation_id -> conversations.id` 形成 **一对多** 关系：一个会话可以有多条消息。

---

## 一、查看当前数据库

```sql
SELECT current_database();
```

`current_database()` 是内置函数，返回当前连接的数据库名，常用来确认自己连对了库。

---

## 二、建表

### 2.1 conversations —— 会话表

```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,               -- SERIAL: 自增整数，插入时不用手动写，数据库自动生成
    agent_name VARCHAR(50),              -- agent 名称，最长 50 字符
    started_at TIMESTAMP DEFAULT NOW()   -- 创建时间，不填则默认当前时间
);
```

### 2.2 messages —— 消息表

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,                                -- 自增主键
    conversation_id INT REFERENCES conversations(id),     -- 外键：指向 conversations.id，保证引用的会话真实存在
    role VARCHAR(20),                                     -- 角色：user / assistant
    content TEXT,                                         -- 消息正文
    created_at TIMESTAMP DEFAULT NOW()                    -- 创建时间
);
```

> **SERIAL 主键**：插入数据时不要手动写 `id`，让数据库自增；有 `DEFAULT` 的列也可以省略，自动用默认值。
> **外键 `REFERENCES`**：插入消息时，`conversation_id` 必须是 `conversations` 里真实存在的 `id`，否则会被拒绝。这就是前面"必须先有会话，才能插它下面的消息"的底层保障。

---

## 三、查看当前数据库里的所有表

```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_type = 'BASE TABLE'
AND table_schema NOT IN ('pg_catalog', 'information_schema');
```

`information_schema` 是 PostgreSQL 自带的元数据视图，可以查表、列、约束等信息。
这里过滤掉系统表（`pg_catalog`、`information_schema`），只看用户自己建的表。

---

## 四、插入数据（INSERT）

### 4.1 批量插入会话

```sql
INSERT INTO conversations (agent_name) VALUES
    ('weather-agent'),
    ('code-reviewer'),
    ('translator');
```

- 只列出 `agent_name` 一列：`id` 是 SERIAL 自动生成、`started_at` 有 DEFAULT，均可省略。
- `VALUES` 后面用逗号分隔多组括号，**一次插多行**，比写多条 INSERT 高效。
- 字符串用**单引号** `'...'`；双引号 `"` 是给表名/列名用的，别混。

### 4.2 按已知 id 插入消息

```sql
INSERT INTO messages (conversation_id, role, content) VALUES
    (1, 'user',      '今天北京天气怎么样？'),
    (1, 'assistant', '北京今天晴，最高气温 22 度。'),
    (2, 'user',      '帮我 review 这段代码'),
    (2, 'assistant', '这段代码有几个问题……'),
    (3, 'user',      '把这句翻译成英文');
```

- `conversation_id` 直接填具体数字，要求该 id 在 conversations 表中真实存在，否则外键约束报错。
- 每个值独占一行、行尾带逗号，**漏逗号时一眼能看出来**。

### 4.3 用子查询插入消息（不依赖具体 id）

```sql
INSERT INTO messages (conversation_id, role, content)
VALUES (
    (SELECT id FROM conversations WHERE agent_name = 'weather-agent'),
    'user',
    '明天山西下雨吗？'
);
```

- 用子查询 `(SELECT id FROM conversations WHERE agent_name = 'weather-agent')` 现查 id，不用记具体编号。
- ⚠️ **每个值之间都要有逗号**。少一个逗号时，相邻的字符串字面量（如 `'user' '明天...'`）会被 SQL 自动拼接成一个字符串，
  导致报错 `INSERT has more target columns than expressions`（目标列数比提供的值多）。

### 4.4 用 RETURNING 拿到刚插入的 id（写代码时最常用）

```sql
INSERT INTO conversations (agent_name) VALUES ('search-agent')
RETURNING id;
```

插入后立刻返回新生成的 `id`，程序里可以拿着它继续插关联的 messages，省去再查一次。
这是 PostgreSQL 很实用的特性，很多别的数据库没有。

---

## 五、查询数据（SELECT）

### 5.1 查看全部消息

```sql
SELECT * FROM messages;
```

`*` 表示所有列，平时排查数据用；生产代码里一般会显式列出列名（性能和可维护性更好）。

### 5.2 JOIN：把会话和消息拼成一张宽表（重点）

```sql
-- 用 JOIN 把会话和它的消息连起来看
SELECT c.agent_name, c.started_at, m.role, m.content
FROM conversations c                          -- c 是 conversations 的别名（AS 可省略）
JOIN messages m ON m.conversation_id = c.id   -- 按外键关系拼接：消息的会话id = 会话的id
ORDER BY c.id, m.id;                          -- 先按会话排序，会话内再按消息顺序排
```

- `FROM conversations c`：给表起短别名 `c`，等价于 `AS c`，后面写 `c.xxx` 更简洁。
- `JOIN messages m ON ...`：默认是 **INNER JOIN（内连接）**，只保留两边都能匹配上的行。
  某个会话如果一条消息都没有，就**不会**出现在结果里；反过来消息也必须能找到对应会话。
- `c.agent_name`、`m.role`：带表前缀，明确列来自哪张表（两张表都有 `id` 列时不加前缀会报歧义错误）。
- `ORDER BY c.id, m.id`：多列排序按**字典序**，先比 `c.id`，相同再比 `m.id`。

**JOIN 的本质**：对每条 message 找到 `id` 等于它 `conversation_id` 的那条 conversation，拼成一行。
会话信息会被"复制"到每条消息所在的行——结果行数 = 匹配上的组合数。

### 5.3 LEFT JOIN：保留没有消息的会话

```sql
SELECT c.agent_name, m.role, m.content
FROM conversations c
LEFT JOIN messages m ON m.conversation_id = c.id
ORDER BY c.id, m.id;
```

`LEFT JOIN` 以**左表为准**，右表匹配不上的列填 `NULL`——所以没有消息的会话也会出现（消息列为空）。
对比 5.2 的 INNER JOIN，就能直观看出两者区别。

### 5.4 加 WHERE 过滤某个会话的消息

```sql
SELECT m.role, m.content
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
WHERE c.agent_name = 'weather-agent'
ORDER BY m.id;
```

`WHERE` 在 JOIN 拼好之后过滤行，这里只保留 `weather-agent` 这个会话的消息。

### 5.5 GROUP BY + 聚合：统计每个会话的消息数

```sql
SELECT c.agent_name, COUNT(*) AS msg_count
FROM conversations c
JOIN messages m ON m.conversation_id = c.id
GROUP BY c.agent_name;
```

`GROUP BY` 按 `agent_name` 分组，`COUNT(*)` 统计每组行数，`AS msg_count` 给结果列起别名。

---

## 六、常见错误速查

| 报错信息 | 原因 | 解决 |
|---------|------|------|
| `INSERT has more target columns than expressions` | `VALUES` 里值之间漏了逗号，相邻字符串被自动拼接 | 补上逗号 |
| `violates foreign key constraint` | 给 `conversation_id` 填了不存在的 id | 先确保对应会话已插入 |
| `column reference "id" is ambiguous` | 两张表都有 `id` 列，没加表前缀 | 写成 `c.id` / `m.id` |
