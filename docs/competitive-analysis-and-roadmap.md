# 抵达 · Reach —— 全景分析 · 同类产品对比 · 优化路线图

- **文档日期**：2026-08-31
- **分析范围**：`server/`（FastAPI）· `web/`（React + TS）· `android/`（Kotlin + Compose）· `harmony/`（本次新增，ArkTS + ArkUI）
- **目标**：把「单人自托管待办」提升到「可长期使用的多端效率系统」，补齐与主流产品的关键能力差距，并把三端行为口径统一。

---

## 一、项目现状全景

### 1.1 架构拓扑

```
                 ┌──────────────────────────────┐
                 │  FastAPI (server/) :8000     │
                 │  ├─ /api/*   业务接口         │
                 │  ├─ /health  健康检查         │
                 │  └─ /{path}  SPA 静态托管     │
                 └───────┬──────────┬───────────┘
             同源托管     │          │ HTTP + JWT(Bearer)
                 ┌────────┘          └─────────┬──────────────┐
        ┌────────▼────────┐        ┌───────────▼───┐  ┌───────▼────────┐
        │ web/ (React SPA)│        │ android/      │  │ harmony/       │
        │ Vite 打包进镜像 │        │ Compose+Retrofit│ │ ArkTS+ArkUI   │
        └─────────────────┘        └───────────────┘  └────────────────┘
```

- **单体单镜像**：`Dockerfile` 阶段 1 构建 web，产物拷进 `server/public`，后端单端口同源托管，避免 CORS 与反代复杂度。
- **数据层**：SQLAlchemy 2.x async；SQLite（发布版）/ PostgreSQL（Docker）双轨；Alembic 管理迁移。
- **鉴权**：JWT（HS256）+ bcrypt；所有资源接口经 `get_current_user`，并逐条做归属校验（`user_id != current.id → 404`），无横向越权。
- **领域模型**：`User / DeviceToken / Category / Goal / Task / FocusSession / Record / Template`。
- **推送**：后端每分钟扫描到期任务 → FCM HTTP v1（`app/push.py`），`reminder_sent_at` 去重。

### 1.2 现有能力盘点

| 域 | 能力 | 覆盖端 |
| --- | --- | --- |
| 维度分块 | 四大默认维度、自定义颜色/图标/排序 | server · web · android · harmony |
| 任务 | 优先级 × 重要度、到期日 + 到期时刻、子任务、拖拽排序、重复(日/周/月) | 全端 |
| 四象限 | `/api/tasks/matrix` 聚合 | server · web ·（android/harmony 本次补齐） |
| 目标 | 目标看板聚合（total/done/overdue/progress） | 全端 |
| 记录 | 日记 / 工作日志 / 读书笔记 + 富文本 + 模板 | 全端 |
| 日历 | 农历 / 节气 / 节日 / 法定节假日 / 黄历详情 | 全端 |
| 专注 | 番茄钟 + 会话落库 + 统计 | 全端 |
| 统计 | 周完成数、streak、专注时长、维度/目标进展 | server · web ·（android/harmony 本次补齐） |
| 导出 | JSON 全量 / CSV 任务表 | server · web |
| 工程化 | pytest 用例 · GitHub Actions（CI / android-build / publish） | — |

### 1.3 已闭环的历史加固（对照 `architecture-quality-review-2026-08-12.md`）

评审列出的 T01–T05 均已落地，验证如下：

- **T01 路径穿越** → `server/app/main.py:107` `_static_candidate_is_safe()` 用 `abspath` 归一化后做前缀断言。
- **T02 Android 明文流量** → `res/xml/network_security_config.xml` 已存在，Manifest 不再全局 `usesCleartextTraffic`。
- **T03 安全响应头** → `server/app/security_headers.py` 已注册。
- **T04 lint** → `web/` 已完成 JSX → TSX 迁移（backlog B5 提前完成），`eslint.config.js` 在位。
- **T05 CSV 注入** → `server/app/sanitize.py:sanitize_csv_cell` + `export.py` 逐单元格清洗。
- **B3 拆分** → `models/` 与 `schemas/` 均已按领域拆包。

---

## 二、同类产品对比

对比对象选取三类代表：**商业闭源 SaaS**（滴答清单 TickTick、Todoist）、**自托管开源**（Vikunja）、**本项目**。

### 2.1 能力矩阵

| 能力 | 滴答清单 | Todoist | Vikunja | Reach（改造前） | Reach（本次后） |
| --- | :-: | :-: | :-: | :-: | :-: |
| 清单/项目分组 | ✅ | ✅ | ✅ | ✅ 维度 | ✅ |
| **标签 / Label** | ✅ | ✅ | ✅ | ❌ | ✅ **新增** |
| **全文搜索** | ✅ | ✅ | ✅ | 仅记录 | ✅ **任务也支持** |
| **保存的筛选视图** | ✅ | ✅ | ✅ | ❌ | 🟡 路线图 P2 |
| 四象限 | ✅ | ❌ | ❌ | ✅ | ✅ |
| 关联长期目标 | 🟡 弱 | ❌ | ❌ | ✅ **差异化优势** | ✅ |
| 子任务 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 重复规则 | ✅ 自然语言 | ✅ 自然语言 | ✅ RRULE | 日/周/月 | ✅ **+工作日/双周/每月最后一天** |
| **每任务独立提醒提前量** | ✅ | ✅ | ✅ | ❌ 全局一个值 | ✅ **新增** |
| **回收站 / 软删除** | ✅ | ✅ | 🟡 | ❌ 硬删 | ✅ **新增** |
| **批量操作** | ✅ | ✅ | ✅ | ❌ | ✅ **新增** |
| **数据导入 / 恢复** | ✅ | ✅ | ✅ | 只能导出 | ✅ **新增** |
| **日历订阅 (ICS)** | ✅ 会员 | ✅ | ✅ | ❌ | ✅ **新增** |
| 番茄钟 | ✅ | ❌ | ❌ | ✅ | ✅ |
| 习惯打卡 | ✅ | ❌ | ❌ | ❌ | 🟡 路线图 P1 |
| 农历/黄历 | 🟡 | ❌ | ❌ | ✅ **差异化优势** | ✅ |
| **偏好跨设备同步** | ✅ | ✅ | ✅ | ❌ 各端本地 | ✅ **新增** |
| **开放 API Token** | ✅ | ✅ | ✅ | ❌ 仅 JWT | 🟡 路线图 P2 |
| 协作共享 | ✅ | ✅ | ✅ | ❌（有意不做） | ❌ 单人定位 |
| 自托管 | ❌ | ❌ | ✅ | ✅ | ✅ |
| 原生鸿蒙端 | 🟡 | ❌ | ❌ | ❌ | ✅ **本次新增** |

### 2.2 结论

**本项目的护城河**是「维度分块 + 四象限 + 关联目标 + 中式日历（农历/黄历/节假日）」这一组合——主流产品都没有把「长期目标」做成一等公民，也几乎没人认真做农历黄历。

**明确落后的是"日常打磨项"**，而这些恰恰是留存的关键：

1. **标签与搜索缺失** —— 任务量过 200 条后，只有「维度」一个筛选维度就找不到东西。
2. **删除即消失** —— 没有回收站，误删不可恢复，这是自托管工具的信任红线。
3. **只能导出、不能导入** —— 备份文件无法回灌，等于备份只有一半价值。
4. **偏好不同步** —— web 存 `localStorage`、Android 存 DataStore，同一个人换端后番茄钟时长、周起始日、时区全部要重设。
5. **提醒能力单薄** ——
   - 全局一个 `FCM_REMINDER_LEAD_MINUTES`，无法「重要会议提前 1 小时、买菜提前 5 分钟」；
   - **移动端提醒 100% 依赖 FCM**，而国内绝大多数 Android 设备无 GMS，等于提醒功能对国内用户直接失效 —— 这是最严重的功能性缺陷。
6. **无 ICS 订阅** —— 无法把待办投射到系统日历 / 手机日历。
7. **移动端功能不对等** —— web 有 `/matrix`、`/stats`，Android 没有；同一账号在不同端看到的能力不一致。
8. **配置分散** —— 环境变量散落在 `config.py` 各处、`.env.example` 只覆盖一半，`ratelimit.py` 还自己 `os.getenv`，缺少启动自检与集中说明。

---

## 三、本次实施内容

### 3.1 后端（`server/`）

| # | 项 | 说明 | 文件 |
| --- | --- | --- | --- |
| B1 | **配置中心化** | 新增 `Settings` 数据类统一收口全部环境变量，带类型转换、默认值、`describe()` 自省与 `warnings()` 生产自检；旧的模块级常量全部保留为别名，零破坏 | `app/config.py` |
| B2 | **`.env.example` 全量化** | 从 12 项扩到 40+ 项，按「基础 / 数据库 / 安全 / 限流 / 推送 / 提醒 / 第三方 / 功能开关」分组并逐条注释 | `.env.example` |
| B3 | **健康检查增强** | `/health` 返回版本、数据库连通性、调度器状态、功能开关；探针可用 | `app/main.py` |
| B4 | **偏好云同步** | `UserSetting` 模型 + `GET/PUT /api/settings`，三端共用一份偏好（番茄钟时长、周起始、时区、主题、日历数据源…） | `models/setting.py`·`routers/settings.py` |
| B5 | **标签体系** | `Tag` + `task_tags` 多对多，`/api/tags` CRUD，`TaskOut.tags` 返回名称数组，写入时按名自动建标签 | `models/tag.py`·`routers/tags.py` |
| B6 | **任务搜索与筛选增强** | `/api/tasks` 新增 `q`（标题/备注模糊）、`tag`、`due_from`/`due_to`、`overdue`、`sort` | `routers/tasks.py` |
| B7 | **批量操作** | `POST /api/tasks/bulk`：批量完成/取消完成/改维度/改目标/加减标签/删除 | `routers/tasks.py` |
| B8 | **回收站（软删除）** | `Task`/`Record` 增 `deleted_at`；`DELETE` 默认进回收站，`?purge=1` 彻底删；`/api/trash` 列表 / 恢复 / 清空；按 `TRASH_RETENTION_DAYS` 自动清理 | `routers/trash.py` |
| B9 | **每任务提醒提前量** | `Task.remind_before_minutes`（空=用全局默认），调度器按任务粒度计算触发时刻 | `models/task.py`·`app/scheduler.py` |
| B10 | **重复规则扩展** | 新增 `weekday`（工作日顺延）、`biweekly`（每两周）、`monthend`（每月最后一天） | `routers/tasks.py`·`schemas/common.py` |
| B11 | **ICS 日历订阅** | `GET /api/calendar.ics?token=...`：把带到期日的任务输出为 VEVENT，可被系统日历订阅；令牌独立于 JWT，可重置 | `routers/calendar_feed.py` |
| B12 | **数据导入** | `POST /api/import`：回灌 `/api/export?fmt=json` 的备份，支持 `merge`/`replace` 两种策略 | `routers/import_data.py` |
| B13 | **调度器加固** | 时区统一 UTC-aware；查询加窗口条件 + 复合索引，避免每分钟全表扫 | `app/scheduler.py` |
| B14 | **多推送通道** | `DeviceToken.platform` 扩展 `harmony`；新增华为 Push Kit 通道，按平台分发；FCM 与 HMS 可同时启用 | `app/push.py`·`app/push_hms.py` |

### 3.2 鸿蒙客户端（`harmony/`，新增）

DevEco Studio 标准工程，ArkTS + ArkUI 声明式 UI，API 12（HarmonyOS NEXT / 5.0）。

- **网络层**：`@ohos.net.http` 封装 `ApiClient`（统一 Bearer 注入、401 登出、错误消息归一）+ 与后端 schema 一一对应的 `models`。
- **状态层**：`AppStorage` + `PersistentStorage` 持久化 token / serverUrl / 偏好；`stores/` 内置各领域 Store。
- **页面**：登录 / 注册 · 看板 · 任务 · **四象限** · 目标 · 日历（农历+黄历+节假日） · 记录 · 专注 · **周回顾** · 设置。
- **提醒**：`@ohos.reminderAgentManager` 本地日程提醒（不依赖任何云推送，离线可用）+ `@kit.PushKit` 注册 token 上报后端做云端提醒，双通道互补。
- **构建**：`hvigor` 配置 + `README.md` 说明真机/模拟器运行与签名。

### 3.3 Android 端对齐优化（`android/`）

| # | 项 | 说明 |
| --- | --- | --- |
| A1 | **四象限页** | 新增 `MatrixScreen`，消费 `/api/tasks/matrix` |
| A2 | **周回顾页** | 新增 `StatsScreen`，消费 `/api/stats/summary` |
| A3 | **本地提醒兜底** | `AlarmManager` + `BroadcastReceiver` 精确闹钟，登录后按任务到期时间在本机排程；**无 GMS 环境下提醒依然可用**，与 FCM 去重 |
| A4 | **偏好云同步** | 启动拉取 `/api/settings` 覆盖本地，改动后回写；与 web / 鸿蒙一致 |
| A5 | **标签 + 搜索** | 任务列表加搜索框与标签筛选；编辑页可增删标签 |
| A6 | **回收站** | 设置页入口，支持恢复 / 彻底删除 |
| A7 | **网络与安全** | 默认地址改 `https://` 占位、OkHttp 超时/重试/日志分级、Gson 收紧 |
| A8 | **依赖与构建** | AGP/Kotlin/Compose BOM 升级到与 `compileSdk 35` 匹配，`release` 开启 R8 + 资源压缩 |

---

## 四、后续路线图（未纳入本次）

| 优先级 | 项 | 理由 |
| :-: | --- | --- |
| P1 | **习惯打卡（Habit）** | 与「维度 + 目标」天然契合，是滴答清单最受欢迎的模块之一；需新模型 + 三端页面，工作量大 |
| P1 | **跨端农历算法单一真相源** | 目前 Android/鸿蒙离线算，web/后端走第三方接口，口径可能有细微差异。建议把离线算法下沉到后端 `/api/lunar` 本地实现，彻底去掉对 apihz 公共账号的依赖 |
| P2 | **保存的筛选视图（Saved Filter）** | 有了 tags + q + 日期范围后，把组合条件存成命名视图即可 |
| P2 | **开放 API Token** | 便于接自动化（Shortcuts / n8n / Home Assistant） |
| P2 | **Webhook** | 任务完成 / 目标达成事件外发 |
| P3 | **桌面小组件 / 快捷添加** | Android AppWidget + 鸿蒙卡片（FormAbility） |
| P3 | **附件与图片** | 需要引入对象存储，自托管场景成本较高 |

---

## 五、验收要点

- `cd server && pytest` 全绿（新增用例覆盖 settings / tags / bulk / trash / import / ics / recurrence）。
- `cd web && npm run build` 通过。
- `cd android && ./gradlew assembleDebug` 通过。
- `harmony/` 在 DevEco Studio 中 `Build → Build Hap(s)` 通过。
- `docker compose up -d --build` 后 `curl localhost:8000/health` 返回 `database: ok`。
- 三端登录同一账号：番茄钟时长 / 周起始日 / 时区一致；任一端改动，另两端重启后同步。
