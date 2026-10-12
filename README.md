# 今日宜食：情境化饮食决策 Agent

今日宜食是一个面向日常“吃什么”决策困难的受控多 Agent 系统。它通过多轮对话将模糊需求沉淀为七维饮食槽位，使用 MySQL 标签召回和 Java 规则重排生成候选，再由大模型生成候选范围内的推荐理由。

## 系统链路

```text
Vue 3
  │ REST/JSON
  ▼
Spring Boot API
  ▼
Java Orchestrator
  ├─ Intent Agent ──► 意图与七维槽位
  ├─ Clarify Agent ─► 缺失信息追问
  ├─ MySQL JSON_OVERLAPS 召回 ─► Java 槽位覆盖度重排
  ├─ Recommend Agent ─► 候选内推荐理由 ─► ID 白名单校验
  └─ Judge Agent ───► 离线质量评分
  │
  └─ Trace / Session / Feedback ─► MySQL
```

## 技术栈

- 后端：Java 21、Spring Boot 3.3、AgentScope Java 1.0.11、MyBatis
- 模型：阿里云 DashScope / qwen-max/qwen-flash
- 数据库：MySQL 8，JSON 标签检索
- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios

## 项目结构

```text
diet-agent/
├─ frontend/                    # Vue 3 前端源码
├─ src/main/java/com/diet/      # Controller、Orchestrator、Agent与业务服务
├─ src/main/resources/
│  ├─ db/diet_db.sql            # 表结构、槽位字典与演示餐食
│  ├─ mapper/                   # MyBatis Mapper
│  ├─ diet/prompts/             # Agent系统Prompt
│  └─ application.yml
├─ src/test/                    # 后端单元测试
├─ evaluation/                  # 固定评测集、故障注入与报告脚本
└─ docs/FRONTEND_API.md         # 前后端接口约定
```

## 运行环境

- JDK 21
- Maven 3.9+
- MySQL 8.0+
- Node.js 22+ 与 npm
- 可用的 DashScope API Key

## 本地启动

### 1. 初始化数据库

先创建数据库，再导入演示表结构和数据：

```sql
CREATE DATABASE diet_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
mysql -u root -p diet_db < src/main/resources/db/diet_db.sql
```

### 2. 配置环境变量

PowerShell：

```powershell
$env:DB_USERNAME='root'
$env:DB_PASSWORD='你的数据库密码'
$env:DASHSCOPE_API_KEY='你的DashScope API Key'
```

Bash：

```bash
export DB_USERNAME=root
export DB_PASSWORD='你的数据库密码'
export DASHSCOPE_API_KEY='你的DashScope API Key'
```

### 3. 启动后端

```bash
mvn spring-boot:run
```

### 4. 启动Vue前端

```bash
cd frontend
npm ci
npm run dev
```

当前项目使用请求头 `X-User-Id` 演示用户数据隔离。由客户端直接提供。
