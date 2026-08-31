package com.zjx93.reach.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.zjx93.reach.data.model.MatrixQuadrant
import com.zjx93.reach.data.model.TaskOut
import com.zjx93.reach.data.model.TaskUpdate
import com.zjx93.reach.data.repository.ReachRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MatrixUiState(
    val loading: Boolean = false,
    val error: String? = null,
    val quadrants: List<MatrixQuadrant> = emptyList(),
)

class MatrixViewModel(private val repo: ReachRepository = ReachRepository()) : ViewModel() {

    private val _state = MutableStateFlow(MatrixUiState())
    val state = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val q = repo.tasksMatrix().getOrNull() ?: emptyList()
            _state.update { it.copy(loading = false, quadrants = q) }
        }
    }

    fun toggleDone(task: TaskOut) {
        val newStatus = if (task.status == "done") "todo" else "done"
        // 乐观更新：立即在本地翻转，避免等待网络时「点击无反应」
        _state.update { s ->
            s.copy(
                quadrants = s.quadrants.map { q ->
                    q.copy(tasks = q.tasks.map { if (it.id == task.id) it.copy(status = newStatus) else it })
                }
            )
        }
        viewModelScope.launch {
            repo.updateTask(task.id, TaskUpdate(status = newStatus))
                .onFailure { e ->
                    // 失败回滚到原状态并提示
                    _state.update { s ->
                        s.copy(
                            quadrants = s.quadrants.map { q ->
                                q.copy(tasks = q.tasks.map { if (it.id == task.id) it.copy(status = task.status) else it })
                            },
                            error = e.message,
                        )
                    }
                }
        }
    }
}
