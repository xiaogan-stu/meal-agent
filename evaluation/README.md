# 今日宜食固定评测工具

这套工具用于回答四个简历问题：

1. 同一轮 IntentAgent 原始意图经过 Java 编排规则后，哪些样本被纠正、哪些被改错？
2. 多轮会话状态合并后，槽位抽取是否改善？
3. Intent、Clarify、Recommend 和 Judge 出错时，业务是否仍能完成？
4. 推荐模型原始输出是否产生候选外 ID，白名单实际拦截了多少次？

运行器只调用项目已有 HTTP API，不会直接修改业务表结构。每次运行使用独立的评测用户和会话 ID；生成的 Trace 会正常保存在 MySQL 中，并自动写入对应 Gold Label。

## 目录

```text
evaluation/
├─ benchmark-config.json          评测集版本说明
├─ benchmark-schema.json          单条 JSONL 用例格式
├─ cases/
│  ├─ quality-cases.jsonl         76 个会话、136 个 Turn
│  ├─ fault-cases.jsonl           3×10 次在线故障 + Judge 故障
│  ├─ smoke-cases.jsonl           2 Turn 低成本连通性检查
│  └─ smoke-fault-cases.jsonl     每类故障各 1 次
├─ run_evaluation.py              标准库实现的主运行器
├─ run.ps1                        Windows 快捷入口
├─ compare_reports.py             旧版本/新版本对照
└─ reports/                       自动生成报告，默认被 Git 忽略
```

## 前置条件

- MySQL 8 已启动，并已经初始化 `src/main/resources/db/diet_db.sql`。
- JDK 21。
- Maven 3.6.3 以上。
- Python 3.10 以上；脚本只用标准库，无需 `pip install`。
- 已设置 `DB_PASSWORD` 和 `DASHSCOPE_API_KEY`。

本机若同时安装多个 Java/Maven，请先确认：

```powershell
java -version
mvn -version
python --version
```

推荐使用 JDK 21、Maven 3.9+ 和 Python 3.10+。若存在多个本地版本，
请通过 `JAVA_HOME`、`PATH` 或版本管理工具选择对应运行时。

## 第一步：人工复核 Gold Label

正式产生简历数字前，请至少通读一次：

```text
evaluation/cases/quality-cases.jsonl
```

其中包含20组多轮会话，每组4轮：8组“逐步补充槽位→完成推荐→换一批”，12组“推荐→换一批→修改条件→再次调整”；另含8条诱导模型输出候选外ID的红队样本。重点确认：

- `expectedIntent` 是否符合你对六类意图的定义。
- `expectedSlots` 是否真的能从用户原话得到。
- `expectedClarifyAction` 是否符合当前澄清规则。
- `acceptableMealIds` 是否与当前公共餐食库一致。

脚本会在运行前从 `/slot-options` 读取当前字典，自动拒绝包含字典外标签的评测集。但业务含义仍需要项目作者最终确认。

## 第二步：启动项目

只跑质量、延迟和 Token 时，按平常方式启动即可：

```powershell
$env:DB_PASSWORD='你的数据库密码'
$env:DASHSCOPE_API_KEY='你的 DashScope Key'
mvn spring-boot:run
```

若要执行故障注入，启动前额外设置：

```powershell
$env:DIET_EVALUATION_FAULT_INJECTION_ENABLED='true'
mvn spring-boot:run
```

故障注入默认关闭。只有同时满足以下两个条件才会生效：

- 服务启动时显式设置 `DIET_EVALUATION_FAULT_INJECTION_ENABLED=true`；
- 单次请求携带 `X-Evaluation-Fault` 请求头。

因此正常页面和普通 API 请求不会意外触发故障。

## 第三步：先做快速校验

另开一个 PowerShell：

```powershell
.\evaluation\run.ps1 -Mode validate
```

成功时应看到类似：

```text
评测集校验通过：76 个会话，136 个 Turn
故障集校验通过：4 类故障配置
```

## 第四步：运行一个版本快照

完整运行质量评测和故障注入：

```powershell
.\evaluation\run.ps1 `
  -Mode all `
  -RunName baseline-v2 `
  -CodeVersion baseline-v2 `
  -ModelName qwen-flash `
  -PromptVersion intent-v1 `
  -Repeats 1
```

如果只想先确认主流程，可运行 2 Turn 的低成本冒烟集：

```powershell
.\evaluation\run.ps1 `
  -Mode quality `
  -Cases .\evaluation\cases\smoke-cases.jsonl `
  -RunName smoke-quality
```

后端以 `DIET_EVALUATION_FAULT_INJECTION_ENABLED=true` 启动后，还可以执行 3 次 Agent 故障和 1 次 Judge 故障冒烟：

```powershell
.\evaluation\run.ps1 `
  -Mode fault `
  -FaultCases .\evaluation\cases\smoke-fault-cases.jsonl `
  -RunName smoke-fault
```

如果要让性能数据更稳定，建议相同版本跑 3 次：

```powershell
.\evaluation\run.ps1 -Mode quality -RunName baseline-perf -Repeats 3
```

注意：`Repeats 3` 会产生408个对话Turn，并产生相应模型费用。

## 输出文件

每次运行会生成独立目录，例如：

```text
evaluation/reports/20261011153000-baseline-v1/
├─ report.md              人工阅读报告
├─ summary.json           版本比较使用的结构化汇总
├─ raw-results.json       完整 Trace 提取结果与原始响应
└─ turn-results.csv       可用 Excel 打开的逐 Turn 结果
```

报告包含：

- 同一轮 IntentAgent Raw 与编排后意图的正确数、Accuracy、95% Wilson区间和Macro-F1。
- 编排层纠正数、回退数、净增正确数及配对McNemar精确检验。
- 原始槽位与状态合并后槽位的 Micro-F1、Exact Match。
- 澄清决策准确率。
- 有 Gold Label 的推荐 Hit@3。
- 推荐Agent原始候选越界轮数/ID数、实际拦截轮数和最终越界轮数；常规样本与8条诱导越界红队样本分开报告。
- Trace完整数、Fallback触发数和业务完成率；工程覆盖率不作为简历效果数字。
- 端到端平均/P50/P95 延迟。
- 输入、输出、总 Token 及覆盖率。
- 3 类在线 Agent 故障注入和 Judge 降级结果。

## 本项目实际如何召回

当前实现不是向量检索。召回链路是：

1. MySQL 使用 `JSON_OVERLAPS`，按 7 维结构化槽位标签从公共库或个人库召回，最多 50 条。
2. Java 对候选计算 7 维槽位覆盖分，过滤上一批结果后降序重排，最多保留 10 条。
3. 推荐Agent接收Top 3候选；运行器同时解析Agent原始JSON和最终响应，分别统计原始越界、白名单拦截和最终越界。常规样本代表固定业务集表现；8条红队样本只验证攻击诱导下约束是否生效，不能混写为线上自然越界率。

因此简历中可以准确写成“基于结构化槽位的 MySQL 规则召回 + Java 覆盖度重排”，不要写向量检索。

## 两类“基线”不要混淆

- 报告里的 `IntentAgent Raw` 是同一次请求、同一个模型输出在 `IntentReviseService` 之前的结果，用来做编排层消融；它不是旧代码版本。
- `baseline-v2` / `candidate-v3` 才是两个独立代码或Prompt版本，需要分别运行并通过 `compare_reports.py` 对照。

## 旧版本与新版本对照

先在旧版本运行一次并保留 `summary.json`，再切换到新版本，用完全相同的命令和 `Repeats` 运行。

比较命令：

```powershell
python evaluation/compare_reports.py `
  evaluation/reports/旧版本目录/summary.json `
  evaluation/reports/新版本目录/summary.json `
  --output evaluation/reports/baseline-vs-candidate.md
```

比较器会拒绝以下不公平对照：

- 评测集 SHA-256 不同。
- 故障评测集 SHA-256 不同。
- 重复次数不同。
- 公共餐食库快照不同。
- 槽位字典快照不同。
- 评测配置文件不同。

模型名和 Prompt 版本会写入报告。若本轮不是专门测试模型或 Prompt，必须保证两次相同。

## 推荐的最快工作流

1. 人工复核76组会话、136轮Gold Label，特别检查20组多轮状态累计和8条红队指令是否合理。
2. 当前代码运行 `baseline-v2`。
3. 只修改一个因素，例如意图 Prompt 或历史消息裁剪。
4. 新代码运行 `candidate-v3`。
5. 使用 `compare_reports.py` 生成对照。
6. 检查 `raw-results.json` 中的错误样本，再决定是否继续优化。

不要同时改模型、Prompt、槽位字典和排序算法，否则无法判断提升来自哪里。

## 如何把结果写进简历

只有在 Gold Label 完成人工复核、两次运行配置一致后，才能使用报告数字。例如：

```text
在76组、136轮固定评测集上，编排规则纠正X轮并改错Y轮，净增Z轮；
常规样本原始候选越界A/B轮；8条红队样本中越界C轮、实际拦截D轮，最终越界E轮；
在 30 次可控 Agent 故障注入中，业务响应完成率达到 E%。
```

准确率 `80% → 90%` 应写“提升 10 个百分点”。Token 和延迟下降使用相对比例，并注明固定评测集和样本数。

## 常见问题

### 提示连接失败

确认 Spring Boot 已启动，默认地址为：

```text
http://localhost:8080/api/v1/diet
```

若修改了端口：

```powershell
.\evaluation\run.ps1 -BaseUrl http://localhost:新端口/api/v1/diet
```

### 故障评测返回“故障注入未启用”

停止服务，设置下面的环境变量后重新启动：

```powershell
$env:DIET_EVALUATION_FAULT_INJECTION_ENABLED='true'
```

### Token 覆盖率不是 100%

只有模型调用成功且供应商返回 Usage 时才能得到完整 Token。报告会单独展示覆盖率，不会把缺失值当成 0。

### Fallback Rate 很高

先查看 `raw-results.json` 的 `errorEvents`，区分主动故障注入、模型限流、鉴权、网络异常和解析错误。质量评测与故障注入使用独立统计，不应混在一个简历数字中。
