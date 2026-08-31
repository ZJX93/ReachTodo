# 抵达 · Reach · 清单分类 + 关联目标 + 农历日历

[![CI](https://github.com/ZJX93/Reach-Todo/actions/workflows/ci.yml/badge.svg)](https://github.com/ZJX93/Reach-Todo/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/ZJX93/Reach-Todo)](./LICENSE)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)

## 🎯 项目核心

**抵达 · Reach**（项目代号 **GoalFlow**）是一款围绕「**分块 + 优先级 + 关联目标**」构建的效率工具。它把杂乱的待办拆解为清晰可控的三层结构，让你每天一眼看清：在忙什么、为什么忙、忙得值不值。

- **① 维度分块**：待办按「**工作 / 健康 / 学习 / 生活**」等维度归位，告别大杂烩清单。
- **② 优先级标注**：每件事都标上优先级，配合紧急度自然形成轻重缓急，先做什么、后做什么一目了然。
- **③ 关联目标**：每件事都可挂到某个长期目标，以 **蓝色文字** 标注——做这件小事时，永远看得见它通向的那个更大的目标。

> 收件箱再大也只是一堆任务；当任务被分块、被排序、被关联到目标，清单才真正变成"你的方向"。

---

## ✨ 功能特性

- **维度分类**：任务按「工作 / 健康 / 学习 / 生活」分块，避免大杂烩列表。
- **优先级 + 重要度**：组合成 **艾森豪威尔四象限**（紧急 × 重要），提供独立「四象限」视图。
- **关联目标**：任务可挂到某个目标，看板以蓝色文字显示；目标页展示 **完成进度条 / 逾期数**。
- **标签与搜索**：任务支持多标签，列表可按关键字、标签、维度筛选。
- **批量操作**：多选后批量改维度 / 目标 / 优先级 / 标签 / 完成 / 删除。
- **回收站**：删除进入回收站（软删除），可恢复或彻底清除，到期自动清理。
- **重复任务**：每天 / 每周 / 每月 / 每工作日 / 每两周 / 每月末，完成后自动顺延下一次。
- **番茄钟专注**：专注计时并自动记录专注时长（**结束时间戳算法**，后台降频不漂移）。
- **周回顾 / 数据看板**：本周完成、连续天数（streak）、专注时长、各维度与目标进展。
- **📅 日历视图**：公历 + **农历**（初一显示月份，其余显示日）、**节气**、**节日**；法定节假日 / 调休补班标注。
- **📄 ICS 日历订阅**：把带到期日的任务输出为 VEVENT，可被系统日历订阅（独立 feed token，可重置）。
- **📥 数据导入 / 备份恢复**：`/api/export` 备份可经 `/api/import` 回灌，支持 merge / replace。
- **🔔 双通道提醒**：
  - **本地日程提醒**（Android `AlarmManager` / HarmonyOS `reminderAgentManager`）——离线、进程被杀依旧准时，无需任何推送配置。
  - **云端推送**（FCM + 华为 Push Kit）——按平台分发，补足「应用被冻结 / 换机未打开」场景。
- **☁️ 偏好云同步**：专注时长、周起始日、时区、强调色、默认提醒提前量等设置服务端为唯一真相源，三端一致。

---

## 🧱 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI · SQLAlchemy(async) · SQLite（发布版）/ PostgreSQL（Docker 版） |
| Web 前端 | React 18 · Vite 5 · Tailwind CSS |
| Android | Kotlin · Jetpack Compose · Retrofit · 原生 AlarmManager 本地提醒 |
| HarmonyOS | ArkTS · ArkUI 声明式 UI（API 12 / HarmonyOS NEXT 5.0） |
| 认证 | JWT（HS256，多用户数据隔离） |
| 日历数据 | 第三方万年历接口（apihz.cn）+ 节假日接口（后端代理） |
| 测试 / CI | pytest · GitHub Actions |

---

## 🚀 快速开始

### 方式一：Docker + PostgreSQL（推荐生产 / 本地一键部署）

```bash
# 多阶段构建：前端在镜像内 vite build 并打进后端镜像，
# 由后端单端口 8000 同源托管前端与 API（不再有独立 5173 服务）
docker compose up -d --build

# 应用（前端 + 后端 API 同源托管）：http://localhost:8000
# 后端 API 文档：http://localhost:8000/docs
```

注册即自动预置「工作 / 健康 / 学习 / 生活」四个维度。

### 方式二：发布版（单端口 SQLite，零外部依赖）

```bash
# 后端（单端口 8000 同时托管前端）
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # 可选：按需修改
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端构建产物已输出到 server/static（如需自行构建）
cd ../web
npm install
npm run build                  # 产物写入 ../server/static
```

打开 **http://localhost:8000** 即可（SPA 由后端单端口托管）。

---

## 📱 三端客户端

| 端 | 目录 | 构建 / 运行 | 说明 |
| --- | --- | --- | --- |
| Web | `web/` | `npm install && npm run build` | 浏览器访问，与后端同源 |
| Android | `android/` | `cd android && ./gradlew assembleDebug` | Kotlin + Compose，独立 Gradle 工程 |
| HarmonyOS | `harmony/` | DevEco Studio → Build Hap(s) | ArkTS + ArkUI，API 12，详见 `harmony/README.md` |

三端共用同一套 REST 语义与偏好模型；登录同一账号后，专注时长 / 周起始日 / 时区等设置服务端为唯一真相源，任一端改动另两端重启后自动同步。

---

## 📄 页面导航（Web）

| 页面 | 路由 | 说明 |
| --- | --- | --- |
| 全部待办（按维度） | `/` | 工作 / 健康 / 学习 / 生活 分块列表 |
| 艾森豪威尔四象限 | `/matrix` | 紧急 × 重要 矩阵 |
| 我的目标 | `/goals` | 进度看板、逾期统计 |
| 周回顾 / 数据 | `/stats` | 本周完成、streak、专注时长 |
| 专注 / 番茄钟 | `/focus` | 专注计时 |
| 📅 日历 | `/calendar` | 农历 / 节气 / 节假日 / 黄历详情 |

---

## 🔧 环境变量

复制 `.env.example` 为 `.env` 并按需修改。**最小可用配置是「全部留空」**，启动时后端会打印配置提醒，并可通过 `GET /health` 查看当前生效配置（密钥自动脱敏）。

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `APP_ENV` | 运行环境 `dev` / `prod` | `dev` |
| `APP_TIMEZONE` | 业务时区（IANA）。**决定到期提醒触发时刻** | `Asia/Shanghai` |
| `DATABASE_URL` | 数据库连接；留空用 SQLite | `sqlite+aiosqlite:///./goalflow.db` |
| `JWT_SECRET` | **生产务必显式设置强随机值**（`openssl rand -hex 32`）；留空时自动生成并持久化到 `server/.jwt_secret` | 自动生成 |
| `JWT_ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | token 有效期 | `1440` |
| `PASSWORD_MIN_LENGTH` | 最短密码长度 | `6` |
| `CORS_ORIGINS` | 允许的前端源，逗号分隔（**不要写 `*`**） | `http://localhost:5173` |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW` | 登录/注册限流（防爆破） | `1` / `10` / `60` |
| `PAGE_SIZE_DEFAULT` / `PAGE_SIZE_MAX` | 列表分页默认/上限 | `100` / `500` |
| `SEED_DEMO_ACCOUNT` | 是否播种演示账号 `demo/reach2026` | `1` |
| `REMINDER_ENABLED` / `REMINDER_LEAD_MINUTES` / `REMINDER_INTERVAL_SECONDS` | 后端提醒调度总开关 / 默认提前量 / 扫描周期 | `1` / `10` / `60` |
| `FCM_PROJECT_ID` / `FCM_CLIENT_EMAIL` / `FCM_PRIVATE_KEY` | 推送通道 A：FCM（Android with GMS / Web） | 空 |
| `HMS_CLIENT_ID` / `HMS_CLIENT_SECRET` | 推送通道 B：华为 Push Kit（**鸿蒙云推送必需**） | 空 |
| `APIHZ_ID` / `APIHZ_KEY` | 万年历接口账号（apihz.cn，默认公共测试号） | `88888888` |
| `HOLIDAY_API_BASE` | 法定节假日数据源 | jiejiariapi.com |
| `FEATURE_TRASH` / `TRASH_RETENTION_DAYS` | 回收站开关 / 保留天数 | `1` / `30` |
| `FEATURE_ICS_FEED` | ICS 日历订阅（`/api/calendar.ics?token=`） | `1` |
| `FEATURE_IMPORT` | 数据导入 / 备份恢复（`/api/import`） | `1` |

> ⚠️ 未设置 `JWT_SECRET` 时虽会自动生成，但 **任何人拿到该值都可伪造 token**，生产环境请务必显式配置。

---

## 📡 API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/auth/register` · `/api/auth/login` | 注册 / 登录（返回 JWT） |
| GET | `/api/tasks` · `/api/tasks/summary` · `/api/tasks/matrix` | 任务列表 / 概览 / 四象限 |
| POST | `/api/tasks/bulk` | 批量操作（改维度/目标/优先级/标签/完成/删除） |
| GET/POST/PUT/DELETE | `/api/tags` | 标签管理（改色、删除保留任务） |
| GET/POST/PUT/DELETE | `/api/goals` · `/api/goals/board` | 目标 / 目标看板 |
| GET/POST/PUT/DELETE | `/api/records` · `/api/templates` | 记录 / 模板 |
| POST | `/api/focus` | 上报专注会话 |
| GET | `/api/stats/summary` | 周回顾统计 |
| GET/PUT | `/api/settings` · `/api/settings/feed-token/reset` | 偏好云同步 / 重置 ICS feed token |
| GET | `/api/calendar.ics?token=` | ICS 日历订阅 |
| POST | `/api/import` | 数据导入（merge / replace） |
| GET | `/api/trash` · POST `/api/trash/{kind}/{id}/restore` | 回收站 / 恢复 |
| GET | `/api/lunar/{date}` · `/api/holidays/{year}` | 农历 / 节假日（后端代理） |
| POST | `/api/devices/register` · `/api/devices/unregister` | 推送设备注册（FCM / HMS 按平台分发） |
| GET | `/health` | 健康检查 + 当前生效配置（密钥脱敏） |

完整接口见后端启动后的 **/docs**（Swagger）或 **/redoc**。

---

## 🛡️ 安全与工程化

- **SPA 路径穿越**：改用 `StaticFiles` + catch-all 回退，杜绝 `../` 越权读取。
- **JWT 密钥可伪造**：默认值已移除，未配置时自动生成随机密钥并持久化到 `.jwt_secret`。
- **富文本 XSS**：服务端清洗，不再依赖前端过滤。
- **登录 / 注册限流**：限速中间件，防暴力破解（支持 Redis 共享计数）。
- **输入校验**：枚举 / 长度 / 范围校验。
- **列表分页 / 时区统一**：统计全链路使用 UTC，修复 streak 跨凌晨断签。
- **多推送通道**：FCM 与华为 Push Kit 可同时启用，按 `DeviceToken.platform` 分发。
- **测试 + CI**：pytest 用例覆盖 settings / tags / bulk / trash / import / ics / recurrence / 安全头 等，GitHub Actions 自动运行。

---

## 🗂️ 项目结构

```
server/        FastAPI 应用（发布版在此单端口托管 web/static）
  app/
    main.py        应用入口、SPA 托管、限流中间件、/health
    config.py      配置（含 JWT 自动密钥、功能开关）
    database.py    SQLAlchemy 异步引擎 / 会话
    scheduler.py   提醒调度（UTC-aware，窗口化扫描）
    models/         ORM 模型（task/category/goal/record/tag/setting…）
    routers/       认证、任务、目标、记录、统计、标签、设置、导入、日历订阅、设备
    schemas/       请求/响应模型与校验
    push.py / push_hms.py   FCM / 华为 Push Kit 推送
  tests/          pytest 用例
web/           React 应用（构建产物输出到 server/static）
android/       Android 原生应用（Kotlin + Compose，独立 Gradle 工程）
harmony/       HarmonyOS 原生应用（ArkTS + ArkUI，见 harmony/README.md）
docs/          竞品分析 / 路线图
docker-compose.yml
```

---

## 🧪 开发与测试

```bash
cd server
pytest                 # 运行 pytest 用例（settings / tags / bulk / trash / import / ics / recurrence / 安全…）

# 本地起服务（开发）
uvicorn app.main:app --reload --port 8000
```

CI 工作流 `.github/workflows/ci.yml` 在每次 push / PR 自动安装依赖并运行测试。
Android / HarmonyOS 各自有独立的构建 CI（见 `android/README.md`、`harmony/README.md`）。

---

## 📦 部署

- **Docker（推荐）**：`docker compose up -d --build` 一键完成多阶段构建——前端在镜像内 `vite build` 并打进后端镜像，由后端单端口 **8000** 同源托管前端与 API；PostgreSQL 数据持久化在 `pgdata` 卷中。生产部署务必通过环境变量注入强随机 `JWT_SECRET`（如 `JWT_SECRET=$(openssl rand -hex 32)`）。
- **发布版（零外部依赖）**：按「方式二」在本地构建前端（`npm run build` 产物输出到 `server/static`）并启动单端口后端，适合轻量自托管 / 演示。
- **推送（可选）**：Android 云推送配置 FCM 三要素；**鸿蒙云推送必须配置华为 Push Kit 的 `HMS_CLIENT_ID/SECRET`**，否则鸿蒙端退化为本机本地提醒。
- **日历农历数据**：依赖第三方免费接口（apihz.cn），默认使用公共测试账号，量大会限频，**生产请替换为自己的账号**（注册 https://www.apihz.cn）。

---

## 📄 许可证

[MIT](./LICENSE) © 2026 ZJX93

## Mobile client (Android)

The native Android app lives in the [`android/`](android/) subdirectory. It is a standalone Gradle project (Kotlin + Jetpack Compose) that uses the same backend API as the web client.

- CI: [`.github/workflows/android-build.yml`](.github/workflows/android-build.yml) builds `app-debug.apk` on every push/PR that touches `android/`.
- Local build: `cd android && ./gradlew assembleDebug`

## HarmonyOS client

The native HarmonyOS (ArkTS) app lives in the [`harmony/`](harmony/) subdirectory. See [`harmony/README.md`](harmony/README.md) for DevEco Studio setup, emulator/device run, signing, and Push Kit configuration.
