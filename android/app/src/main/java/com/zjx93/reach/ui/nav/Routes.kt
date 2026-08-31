package com.zjx93.reach.ui.nav

/** 所有导航路由常量。带参页面用 ?id= / ?date= 形式，在 NavHost 中以 navArgument 接收。 */
object Routes {
    const val LOGIN = "login"
    const val REGISTER = "register"
    const val MAIN = "main"

    // 底部导航主标签
    const val DASHBOARD = "dashboard"
    const val TASKS = "tasks"
    const val GOALS = "goals"
    const val CALENDAR = "calendar"
    const val PROFILE = "profile"

    // 子页面
    const val TASK_EDIT = "taskEdit"
    const val GOAL_EDIT = "goalEdit"
    const val RECORDS = "records"
    const val RECORD_EDIT = "recordEdit"
    const val DAY_DETAIL = "dayDetail"
    const val FOCUS = "focus"
    const val SETTINGS = "settings"
    const val MATRIX = "matrix"
    const val STATS = "stats"

    val TAB_ROUTES = listOf(DASHBOARD, TASKS, GOALS, CALENDAR, PROFILE)
}
