# 今日宜食：情境化饮食决策 Agent

今日宜食是一个面向日常“吃什么”决策困难的受控多 Agent 系统。它通过多轮对话将模糊需求沉淀为七维饮食槽位，使用 MySQL 标签召回和 Java 规则重排生成候选，再由大模型生成候选范围内的推荐理由。

项目重点不在“让模型自由决定一切”，而在于把语义理解交给 LLM，把路由、状态、召回、排序、输出约束、故障降级和可观测性留在确定性的 Java 业务层。

## 核心能力

- **受控多 Agent 编排**：拆分 Intent、Clarify、Recommend 和 Judge Agent，由 Java Orchestrator 管理路由、槽位合并和会话状态跃迁。
- **七维情境画像**：维护餐次、情绪、场景、健康目标、菜系、口味和便捷性七类槽位，支持多轮补充和条件调整。
- **可控召回与生成**：通过 MySQL `JSON_OVERLAPS` 从公共库或个人库召回，按槽位覆盖度重排，并使用 Top 3 候选 ID 白名单约束模型输出。
- **分级 Fallback**：为意图识别、澄清、推荐生成和 LLM Judge 提供关键词或模板降级，避免单点模型异常中断业务流程。
- **全链路 Trace**：记录意图、槽位、路由、召回、模型输入输出、耗时、Token 和异常，持久化后支持回放、标注和离线评估。
- **固定评测闭环**：提供固定 Gold Set、故障注入、版本快照和自动报告脚本，用相同数据对照不同代码、Prompt 或模型版本。

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
  └─ Trace / Session / Feedback / Evaluation ─► MySQL
```

## 技术栈

- 后端：Java 21、Spring Boot 3.3、AgentScope Java 1.0.11、MyBatis
- 模型：阿里云 DashScope / 通义千问
- 数据库：MySQL 8，JSON 标签检索
- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、Axios
- 评测：Python、PowerShell、JUnit 5

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
- Python 3.10+（仅运行离线评测时需要）
- PowerShell 7+（运行 `evaluation/run.ps1` 时需要）

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

仓库中不保存真实密码或API Key。

### 3. 启动后端

```bash
mvn spring-boot:run
```

后端默认运行在 `http://localhost:8080`。

### 4. 启动Vue前端

```bash
cd frontend
npm ci
npm run dev
```

浏览器访问 `http://localhost:5173`。Vite会把 `/api` 请求代理到本地8080端口。

## 自动化测试

```bash
mvn test
cd frontend && npm ci && npm run build
python evaluation/test_evaluation.py
```

## 固定评测

评测源码和Gold Set保留在 `evaluation/`，每次运行产生的完整Trace报告不会提交到Git。详细说明见 [evaluation/README.md](evaluation/README.md)。

启动后端后，只做数据集、配置与服务快照校验（不会调用大模型跑完整质量集）：

```powershell
.\evaluation\run.ps1 -Mode validate
```

后端启动后执行质量与故障评测：

```powershell
$env:DIET_EVALUATION_FAULT_INJECTION_ENABLED='true'

.\evaluation\run.ps1 `
  -Mode all `
  -RunName baseline-v2 `
  -CodeVersion baseline-v2 `
  -ModelName qwen-flash `
  -PromptVersion intent-v1 `
  -Repeats 1
```

当前固定集包含76组会话、136轮对话，其中20组为四轮连续会话。一次固定配置运行中：澄清决策为66/69，端到端延迟P50约1.1秒、P95约2.2秒；30次在线Agent故障注入均完成业务响应，8条候选越界红队样本触发2次模型原始越界并均被白名单拦截。

这些数字只说明对应固定数据和配置下的结果，不代表线上流量或大规模餐食库上的泛化结论。

## 演示身份与安全边界

当前项目使用请求头 `X-User-Id` 演示用户数据隔离。该值由客户端直接提供，**不是登录、认证或授权机制**，只适合本地演示和作品展示。

真实部署时应接入可信认证系统，从服务端认证上下文获取用户身份，同时限制Trace、标注和评估接口的访问权限。故障注入默认关闭，只有显式设置 `DIET_EVALUATION_FAULT_INJECTION_ENABLED=true` 才会启用。

## 已知边界

- 当前演示公共餐食库规模较小，推荐Hit@3只用于回归检查，不能作为召回泛化能力证明。
- 系统采用结构化标签召回和规则重排，不是向量检索。
- HTTP接口为同步调用，耗时会受到模型服务和网络状态影响。
- 完整评测报告包含模型输入输出和Trace，仅保存在本地，不进入公开仓库。
