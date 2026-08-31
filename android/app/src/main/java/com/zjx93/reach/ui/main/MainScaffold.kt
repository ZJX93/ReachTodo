package com.zjx93.reach.ui.main

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.zjx93.reach.ui.nav.Routes

data class Tab(val route: String, val label: String, val icon: ImageVector)

@Composable
fun MainScaffold(rootNav: NavHostController) {
    val inner = rememberNavController()
    val navBack by inner.currentBackStackEntryAsState()
    val route = navBack?.destination?.route
    val showBar = route != null && route in Routes.TAB_ROUTES

    val tabs = listOf(
        Tab(Routes.DASHBOARD, "看板", Icons.Filled.Home),
        Tab(Routes.TASKS, "任务", Icons.Filled.CheckCircle),
        Tab(Routes.GOALS, "目标", Icons.Filled.Flag),
        Tab(Routes.CALENDAR, "日历", Icons.Filled.CalendarMonth),
        Tab(Routes.PROFILE, "我的", Icons.Filled.Person),
    )

    Scaffold(
        bottomBar = {
            if (showBar) {
                NavigationBar {
                    tabs.forEach { t ->
                        NavigationBarItem(
                            selected = route == t.route,
                            onClick = { inner.navigate(t.route) { launchSingleTop = true; popUpTo(Routes.DASHBOARD) { saveState = true } } },
                            icon = { androidx.compose.material3.Icon(t.icon, contentDescription = t.label) },
                            label = { Text(t.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(inner, startDestination = Routes.DASHBOARD, modifier = Modifier.padding(padding)) {
            composable(Routes.DASHBOARD) { DashboardScreen(inner) }
            composable(Routes.TASKS) { TasksScreen(inner) }
            composable(route = "${Routes.TASK_EDIT}?id={id}", arguments = listOf(navArgument("id") { type = NavType.StringType; nullable = true; defaultValue = null })) { back -> TaskEditScreen(inner, back.arguments?.getString("id")?.toIntOrNull()) }
            composable(Routes.GOALS) { GoalsScreen(inner) }
            composable(route = "${Routes.GOAL_EDIT}?id={id}", arguments = listOf(navArgument("id") { type = NavType.StringType; nullable = true; defaultValue = null })) { back -> GoalEditScreen(inner, back.arguments?.getString("id")?.toIntOrNull()) }
            composable(Routes.RECORDS) { RecordsScreen(inner) }
            composable(route = "${Routes.RECORD_EDIT}?id={id}", arguments = listOf(navArgument("id") { type = NavType.StringType; nullable = true; defaultValue = null })) { back -> RecordEditScreen(inner, back.arguments?.getString("id")?.toIntOrNull()) }
            composable(Routes.CALENDAR) { CalendarScreen(inner) }
            composable(route = "${Routes.DAY_DETAIL}?date={date}", arguments = listOf(navArgument("date") { type = NavType.StringType; nullable = true; defaultValue = null })) { back -> DayDetailScreen(inner, back.arguments?.getString("date")) }
            composable(Routes.FOCUS) { FocusScreen(inner) }
            composable(Routes.PROFILE) { ProfileScreen(inner, rootNav) }
            composable(Routes.SETTINGS) { SettingsScreen(inner) }
            composable(Routes.MATRIX) { MatrixScreen(inner) }
            composable(Routes.STATS) { StatsScreen(inner) }
        }
    }
}
