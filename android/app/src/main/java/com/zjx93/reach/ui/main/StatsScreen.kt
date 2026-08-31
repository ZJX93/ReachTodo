package com.zjx93.reach.ui.main

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.zjx93.reach.data.model.CategoryStat
import com.zjx93.reach.data.model.GoalProgress
import com.zjx93.reach.viewmodel.StatsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatsScreen(nav: NavHostController) {
    val vm: StatsViewModel = viewModel()
    val state by vm.state.collectAsState()
    val s = state.summary

    Scaffold(topBar = { TopAppBar(title = { Text("周回顾") }) }) { padding ->
        if (state.loading) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        } else if (s == null) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text(state.error ?: "暂无数据", color = MaterialTheme.colorScheme.outline)
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatCard("本周完成", "${s.weekCompleted}", Modifier.weight(1f))
                        StatCard("连续天数", "${s.streak}", Modifier.weight(1f))
                    }
                }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatCard("今日专注", "${s.focusMinutesToday}'", Modifier.weight(1f))
                        StatCard("本周专注", "${s.focusMinutesWeek}'", Modifier.weight(1f))
                    }
                }
                item { Text("概览", style = MaterialTheme.typography.titleMedium) }
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        StatCard("待办", "${s.totalTodo}", Modifier.weight(1f))
                        StatCard("已完成", "${s.totalDone}", Modifier.weight(1f))
                    }
                }
                item { Text("维度投入", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 4.dp)) }
                if (s.perCategory.isEmpty()) {
                    item { Text("暂无维度数据", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline) }
                } else {
                    items(s.perCategory, key = { it.name }) { c -> CategoryStatRow(c) }
                }
                item { Text("目标推进", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(top = 4.dp)) }
                if (s.goalsProgress.isEmpty()) {
                    item { Text("暂无目标", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline) }
                } else {
                    items(s.goalsProgress, key = { it.id }) { g -> GoalStatRow(g) }
                }
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(modifier = Modifier.padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Medium)
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun CategoryStatRow(c: CategoryStat) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text("${c.icon} ${c.name}", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(6.dp))
            Text("待办 ${c.todo} · 已完成 ${c.done}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
        }
    }
}

@Composable
private fun GoalStatRow(g: GoalProgress) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(g.title, style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.height(6.dp))
            LinearProgressIndicator(g.progress / 100f, modifier = Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)))
            Text("${g.done}/${g.total} (${g.progress}%)", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
        }
    }
}
