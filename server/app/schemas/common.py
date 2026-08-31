"""跨域复用的枚举类型（Literal）与公共类型别名。

集中定义可避免字符串散落导致脏数据入库，并作为前后端字段取值的单一真相源。
"""

from typing import Literal

# 紧急度
Priority = Literal["low", "normal", "high", "urgent"]
# 重要度（用于艾森豪威尔矩阵）
Importance = Literal["low", "normal", "high"]
# 重复规则。
#   none      不重复
#   daily     每天
#   weekday   仅工作日（周一~周五，跳过周末）
#   weekly    每周
#   biweekly  每两周
#   monthly   每月同日（钳制到该月最后一天）
#   monthend  每月最后一天
# 说明：新增的 weekday / biweekly / monthend 覆盖了「日报」「双周会」「月末结账」
# 这三类最常见但旧枚举无法表达的场景；旧值语义完全不变，老数据无需迁移。
Recurrence = Literal[
    "none", "daily", "weekday", "weekly", "biweekly", "monthly", "monthend"
]
TaskStatus = Literal["todo", "done"]
RecordType = Literal["diary", "worklog", "note"]
TemplateType = Literal["diary", "worklog", "note", "all"]
GoalStatus = Literal["active", "done"]
# 设备推送平台。harmony = HarmonyOS（走华为 Push Kit），
# android/web 走 FCM；ios 预留。
DevicePlatform = Literal["android", "web", "harmony", "ios"]
