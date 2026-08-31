package com.zjx93.reach.ui.main

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.zjx93.reach.ui.nav.Routes
import com.zjx93.reach.viewmodel.AuthViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(nav: NavHostController, rootNav: NavHostController) {
    val vm: AuthViewModel = viewModel()
    val state by vm.state.collectAsState()

    var showEmail by remember { mutableStateOf(false) }
    var showPwd by remember { mutableStateOf(false) }

    Scaffold(topBar = { TopAppBar(title = { Text("我的") }) }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(modifier = Modifier.size(56.dp).clip(CircleShape), color = MaterialTheme.colorScheme.primary) {
                    Box(contentAlignment = Alignment.Center) { Text((state.user?.username ?: "?").first().uppercase(), style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.onPrimary) }
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(state.user?.username ?: "未登录", style = MaterialTheme.typography.titleLarge)
                    Text(state.user?.email ?: "未设置邮箱", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.outline)
                }
            }

            ListItem(headlineContent = { Text("编辑资料") }, leadingContent = { Icon(Icons.Filled.Edit, null) }, modifier = Modifier.clickable { showEmail = true })
            ListItem(headlineContent = { Text("修改密码") }, leadingContent = { Icon(Icons.Filled.Lock, null) }, modifier = Modifier.clickable { showPwd = true })
            ListItem(headlineContent = { Text("设置") }, leadingContent = { Icon(Icons.Filled.Settings, null) }, modifier = Modifier.clickable { nav.navigate(Routes.SETTINGS) })
            ListItem(headlineContent = { Text("专注计时") }, leadingContent = { Icon(Icons.Filled.PlayArrow, null) }, modifier = Modifier.clickable { nav.navigate(Routes.FOCUS) })
            ListItem(headlineContent = { Text("周回顾") }, leadingContent = { Icon(Icons.Filled.DateRange, null) }, modifier = Modifier.clickable { nav.navigate(Routes.STATS) })

            Spacer(Modifier.weight(1f))
            Button(onClick = {
                vm.logout()
                rootNav.navigate(Routes.LOGIN) { popUpTo(0) { inclusive = true } }
            }, modifier = Modifier.fillMaxWidth().height(48.dp), colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.errorContainer, contentColor = MaterialTheme.colorScheme.onErrorContainer)) {
                Icon(Icons.Filled.ExitToApp, contentDescription = null)
                Spacer(Modifier.width(6.dp))
                Text("退出登录")
            }
        }
    }

    if (showEmail) {
        var email by remember { mutableStateOf(state.user?.email ?: "") }
        AlertDialog(onDismissRequest = { showEmail = false }, confirmButton = {
            TextButton(onClick = { vm.updateEmail(email) { showEmail = false } }) { Text("保存") }
        }, dismissButton = { TextButton(onClick = { showEmail = false }) { Text("取消") } }, title = { Text("编辑邮箱") }, text = {
            OutlinedTextField(email, { email = it }, label = { Text("邮箱") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        })
    }

    if (showPwd) {
        var oldP by remember { mutableStateOf("") }
        var newP by remember { mutableStateOf("") }
        AlertDialog(onDismissRequest = { showPwd = false }, confirmButton = {
            TextButton(onClick = { vm.changePassword(oldP, newP) { showPwd = false } }) { Text("保存") }
        }, dismissButton = { TextButton(onClick = { showPwd = false }) { Text("取消") } }, title = { Text("修改密码") }, text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(oldP, { oldP = it }, label = { Text("当前密码") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                OutlinedTextField(newP, { newP = it }, label = { Text("新密码（≥6 位）") }, singleLine = true, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                state.error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            }
        })
    }
}
