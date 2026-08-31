# 抵达 Reach · HarmonyOS 客户端

基于 **ArkTS + ArkUI 声明式 UI** 的鸿蒙原生客户端，运行于 **HarmonyOS NEXT（API 12 / 5.0）**。
与后端 `server/`、Web `web/`、Android `android/` 共享同一套 REST 语义与偏好模型。

---

## 1. 环境要求

| 工具 | 版本 | 说明 |
| --- | --- | --- |
| DevEco Studio | 5.0+（NEXT 版） | 内置 hvigor 构建与 ArkTS 编译器 |
| HarmonyOS SDK | API 12 (5.0.0) | `compileSdkVersion` / `targetSdkVersion` 已锁定 12 |
| 模拟器 / 真机 | HarmonyOS NEXT | 手机、平板、2in1（已在 `module.json5` 声明 `deviceTypes`） |

> 首次打开请用 DevEco Studio 的 **File → Open** 选择本 `harmony/` 目录；
> 等待 `oh-package install` 与 hvigor 同步完成（约 1–2 分钟）。

---

## 2. 配置后端地址

应用启动后需要指向你的后端（`server/`，默认端口 8000）：

1. 登录页 / 「我的 → 服务器地址」中填写，例如 `http://192.168.1.10:8000`。
   - 自动补全协议：缺失 `http://` / `https://` 时默认补 `https://`；结尾斜杠会被去掉。
2. 默认值见 `common/Prefs.ets` 的 `DEFAULT_SERVER_URL`（`http://127.0.0.1:8000`，仅适合本机直连）。
3. **模拟器访问宿主机**：模拟器把 `127.0.0.1` 指向自身，请填宿主机的局域网 IP
   （如 `http://192.168.x.x:8000`），并确保后端已监听 `0.0.0.0`。

后端需先就绪：`cd server && uvicorn app.main:app --host 0.0.0.0 --port 8000`，
或 `docker compose up -d --build` 后 `curl localhost:8000/health` 返回 `database: ok`。

---

## 3. 运行 / 构建

### 模拟器
1. Device Manager 新建一个 **HarmonyOS NEXT** Phone 模拟器并启动。
2. 顶部 Run → **Run 'entry'**（或 `Shift+F10`），选择该模拟器。

### 真机
1. 手机开启 **开发者模式 → USB 调试 / 无线调试**。
2. 用 USB 或同一局域网无线连接，Run 时选择该设备。

### 构建 HAP / APP
- 菜单 **Build → Build Haps(s) / APP(s) → Build APP(s)** 产出可分发安装包。
- 验收要求见根目录 `docs/competitive-analysis-and-roadmap.md` 第五节：
  `harmony/` 在 DevEco Studio 中 `Build → Build Hap(s)` 通过。

---

## 4. 签名（发布 / 真机安装必须）

HarmonyOS NEXT 安装必须带签名：

1. **调试签名**：DevEco Studio → **File → Project Structure → Signing Configs**，
   勾选 **Automatically generate signature**（需登录华为开发者账号），IDE 会自动写入
   `build-profile.json5` 的 `signingConfigs`。
2. **发布签名**：在 [AppGallery Connect](https://developer.huawei.com/consumer/cn/) 创建应用，
   下载 `p12` / `csr` / `cer` / `p7b`，在 Signing Configs 手动指定后 **Build APP(s)**。

> 仓库中的 `build-profile.json5` 故意留空 `signingConfigs`，CI / 他人克隆后由本地 IDE 注入，
> 避免把证书提交进版本库。

---

## 5. 推送（云端提醒）可选配置

提醒采用**双通道互补**：

- **本地日程提醒**（`reminderAgentManager`，`common/Reminder.ets`）：
  离线、飞行模式、进程被杀依旧准时，**无需任何配置**，安装即生效。
- **云端推送**（华为 Push Kit，`common/Push.ets`）：
  补全「应用被冻结 / 换机未打开」场景。需先在 AGC 接入推送并开通，
  客户端会自动取 token 上报后端（`/api/devices/register`）。
  取不到 token 时**静默降级**，不影响其它功能。

要启用云端推送：
1. AGC 项目开启 **Push Kit**，下载 `agconnect-services.json` 放到 `entry/` 下。
2. 后端在 `server/.env` 配置华为推送凭证（`push_hms.py` 通道），
   并把 `DeviceToken.platform` 支持 `harmony`（已支持）。

---

## 6. 工程结构

```
harmony/
├── AppScope/                 # 应用级配置（bundleName、图标、app_name）
│   └── resources/base/       # 应用图标、应用名
├── entry/                    # 主模块
│   └── src/main/
│       ├── ets/
│       │   ├── common/       # 网络层 + 工具 + 模型（与后端 schema 一一对应）
│       │   │   ├── ApiClient.ets   # 统一 Bearer 注入 / 401 登出 / 错误归一
│       │   │   ├── Api.ets         # 接口清单（路径+查询+类型，无业务判断）
│       │   │   ├── Models.ets      # 与 server/app/schemas 对齐的数据模型
│       │   │   ├── DateUtil.ets    # 全部基于 YYYY-MM-DD 字符串的日期运算
│       │   │   ├── Lunar.ets       # 离线农历/黄历，与 Android 同一数据表算法
│       │   │   ├── Prefs.ets       # AppStorage + PersistentStorage 持久化
│       │   │   ├── Push.ets        # Push Kit token 注册（静默降级）
│       │   │   ├── Reminder.ets    # 本地日程提醒（全量重排，幂等）
│       │   │   ├── Theme.ets       # 视觉常量 + 选项枚举（与 web/Android 一致）
│       │   │   └── Toast.ets       # 轻提示 / 错误文案归一
│       │   ├── stores/
│       │   │   └── AppStore.ets    # 会话 + 偏好/维度/标签缓存 + 提醒同步
│       │   ├── view/          # 看板/任务/日历/记录/我的 等 Tab 视图与共用组件
│       │   ├── pages/         # 12 个二级页（编辑、目标、四象限、专注、周回顾…）
│       │   └── entryability/  # EntryAbility 生命周期
│       ├── resources/         # 字符串、颜色、图标、页面路由
│       └── module.json5       # 权限（INTERNET / 网络信息 / 本地提醒）
├── build-profile.json5        # 产品/SDK 版本（API 12）
├── hvigorfile.ts              # hvigor 构建入口
└── oh-package.json5           # 模块依赖
```

### 页面与路由（`resources/base/profile/main_pages.json`）
`Index`（登录门禁 + 底部 Tab）下挂：`TaskEditPage` `GoalEditPage` `RecordEditPage`
`DayDetailPage` `MatrixPage` `GoalsPage` `StatsPage` `FocusPage` `SettingsPage`
`TagsPage` `TrashPage`。

---

## 7. 关键设计

- **状态驱动登录**：`@StorageLink(KEY_TOKEN)` 直接监听持久化令牌，401 拦截器清空令牌后
  任意深度页面都会立即回到登录态，无需 router 跳转兜底。
- **模型不转驼峰**：字段名直接对齐后端 snake_case，少一层转换少一类 bug；
  唯一例外是 `/api/settings` 后端本身用 camelCase。
- **提醒全量重排**：取消全部再发布最近 28 条，幂等且无「幽灵提醒」漂移风险。
- **一切降级优先**：推送、本地提醒、偏好云同步任意一步失败都不阻断主流程。

详见各文件顶部注释。
