# 抵达 Reach · Android

Reach-Todo 的**原生 Android 客户端**（Kotlin + Jetpack Compose），与 Web 端共用同一套 FastAPI 后端，功能对齐：看板、任务、目标、记录、日历（含农历/节假日）、专注计时、设置、资料与改密。

原生 OkHttp/Retrofit 直连后端，**不受浏览器 CORS 限制**，只需在 App 内填对服务器地址即可。

---

## 技术栈

| 层 | 选型 |
| --- | --- |
| 语言 / UI | Kotlin + Jetpack Compose (Material 3) |
| 架构 | 单 Activity + 嵌套 Navigation Compose（根：登录/注册/主框架；内层：底部 Tab + 子页） |
| 网络 | Retrofit2 + OkHttp（带 `AuthInterceptor` 注入 JWT）+ Gson |
| 本地存储 | DataStore (Preferences)：令牌 / 服务器地址 / 应用设置 |
| 异步 | Kotlin Coroutines + `viewModelScope` / `StateFlow` |
| 时区 | `java.time`（minSdk 26），按设置里的 IANA 时区计算日期 |
| 构建 | Gradle 8.9 · AGP 8.5.2 · Kotlin 1.9.24 · Compose Compiler 1.5.14 |

## 环境要求

- **Android Studio** Hedgehog (2023.1) 或更新版本
- **JDK 17**（已配置 `sourceCompatibility = JavaVersion.VERSION_17`）
- 一台 Android 8.0+（minSdk 26）设备或模拟器

> 本仓库不含 `local.properties`。首次用 Android Studio 打开时，IDE 会在 `local.properties` 写入本机 SDK 路径（该文件已被 `.gitignore` 忽略）。

## 打开与构建

1. 用 Android Studio 打开本工程根目录（`reach-android/`）。
2. 等待 **Sync Project with Gradle Files** 完成（会自动下载 Gradle 8.9 与依赖）。
3. 连接设备 / 启动模拟器，点击 ▶ **Run**（或 `Shift + F10`）。
4. 首次运行若提示选择 Gradle 分发版，选 **较新版本（官方 8.9 wrapper 已内置）** 即可。

> 仓库已内置 `gradlew` / `gradlew.bat` / `gradle-wrapper.jar`，命令行可 `./gradlew assembleDebug` 直接构建（需本机已装 JDK 17）。

## 连接你的后端

App 默认服务器地址为 `http://192.168.9.3:8000`（与 NAS 同局域网）。如不一致：

1. 登录页 → 「我的」→ **设置** → 服务器，填入后端地址（如 `http://192.168.1.50:8000` 或公网域名，**无需** `/api` 后缀，也不要带结尾斜杠之外的多余路径）。
2. 地址变化会即时重建 Retrofit 实例，无需重启。
3. 手机必须能访问该地址（同一局域网，或后端已暴露公网）。原生请求不走浏览器，因此不受后端 `CORS_ORIGINS` 限制。

> 后端即 `ZJX93/Reach-Todo`（FastAPI + React/Vite 单体）。Demo 账号 `demo / reach2026`（若已植入 demo 数据）。

## 功能对照

| 模块 | 说明 |
| --- | --- |
| 看板 Dashboard | 问候语 + 待办/连续/今日专注/本周完成统计卡 + 开始专注 + 今日待办 + 目标进展 |
| 任务 Tasks | 待办/已完成/全部筛选；分类色块、到期相对天数；勾选完成、点按编辑、新建 |
| 目标 Goals | 看板式进度条；新建/编辑/删除；勾选完成 |
| 记录 Records | 日记/工作日志/笔记三类；条件显示书名/作者/项目；新建/编辑/删除 |
| 日历 Calendar | 6×7 月视图；周日/周一为首可选；节假日标放假（红）/补班；点格看当日详情（农历 + 记录 + 到期任务） |
| 专注 Focus | 倒计时（默认 25 分钟，可在设置调 15/25/45/60）；结束自动写专注记录 |
| 设置 Settings | 服务器地址、默认专注时长、每周起始、时区（含实时时钟）、农历数据源（后端代理 / 自定义接口） |
| 资料 Profile | 编辑邮箱、修改密码、进入设置/专注、退出登录 |

## 目录结构

```
app/src/main/java/com/zjx93/reach/
├── MainActivity.kt / ReachApplication.kt      # 入口
├── data/
│   ├── model/ApiModels.kt                      # 与后端 schemas 一一对应的数据类
│   ├── remote/{ApiService,RetrofitClient}.kt   # Retrofit 接口 + 带鉴权的客户端
│   ├── local/UserPrefs.kt                     # DataStore 持久化
│   └── repository/ReachRepository.kt           # 统一封装 Result<T> 与错误解析
├── ui/
│   ├── theme/Theme.kt                          # 品牌色 + 明暗主题
│   ├── nav/{Routes,AppNavHost}.kt             # 路由与导航
│   ├── auth/                                   # 登录 / 注册
│   └── main/                                   # 主框架与各业务屏
├── util/{DateTimeUtils,LunarUtils}.kt          # 时区日期 / 农历展示
└── viewmodel/                                  # 各页 ViewModel
```

## 备注

- 包名：`com.zjx93.reach`，应用 ID：`com.zjx93.reach`。
- `android:icon` 暂用系统 `ic_menu_agenda` 占位，正式发布前建议替换为自定义图标。
- 后端 API 契约见 `data/remote/ApiService.kt` 与各 `data/model/ApiModels.kt`（路由前缀 `/api/*`）。
