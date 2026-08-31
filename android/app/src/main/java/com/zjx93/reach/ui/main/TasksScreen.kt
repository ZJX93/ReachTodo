package com.zjx93.reach.ui.main

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.zjx93.reach.data.model.TaskOut
import com.zjx93.reach.ui.nav.Routes
import com.zjx93.reach.util.daysFromToday
import com.zjx93.reach.viewmodel.TasksViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TasksScreen(nav: NavHostController) {
    val vm: TasksViewModel = viewModel()
    val state by vm.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("任务") },
                actions = {
                    IconButton(onClick = { nav.navigate(Routes.MATRIX) }) {
                        Icon(Icons.Filled.Dashboard, contentDescription = "四象限")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { nav.navigate(Routes.TASK_EDIT) }) {
                Icon(Icons.Filled.Add, contentDescription = "新建")
            }
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize()) {
            Row(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                listOf("todo" to "待办", "done" to "已完成", "all" to "全部").forEach { (k, label) ->
                    FilterChip(
                        selected = state.filter == k,
                        onClick = { vm.setFilter(k) },
                        label = { Text(label) },
                        modifier = Modifier.padding(end = 8.dp),
                    )
                }
            }

            if (state.loading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            } else if (state.tasks.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("暂无任务，点右下角新建", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.outline)
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(state.tasks, key = { it.id }) { task ->
                        TaskCard(task, vm, nav)
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TaskCard(task: TaskOut, vm: TasksViewModel, nav: NavHostController) {
    val done = task.status == "done"
    Card(
        modifier = Modifier.fillMaxWidth().clickable { nav.navigate("${Routes.TASK_EDIT}?id=${task.id}") },
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { vm.toggleDone(task) }) {
                Icon(
                    imageVector = if (done) Icons.Filled.Delete else Icons.Filled.Add,
                    contentDescription = "完成",
                    tint = if (done) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    task.title,
                    style = MaterialTheme.typography.titleMedium,
                    textDecoration = if (done) TextDecoration.LineThrough else null,
                    color = if (done) MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.onSurface,
                    maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    task.categoryName?.let {
                        Surface(
                            color = runCatching { Color(android.graphics.Color.parseColor(task.categoryColor ?: "#3B82F6")) }.getOrElse { MaterialTheme.colorScheme.primary },
                            shape = RoundedCornerShape(8.dp),
                        ) {
                            Text("${task.categoryIcon ?: ""} $it", modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp), style = MaterialTheme.typography.labelSmall, color = Color.White)
                        }
                    }
                    task.dueDate?.let {
                        Spacer(Modifier.width(8.dp))
                        Text(daysFromToday(it, ""), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                    }
                }
            }
        }
    }
}
