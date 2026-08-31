package com.zjx93.reach.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.zjx93.reach.data.model.StatsSummary
import com.zjx93.reach.data.repository.ReachRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StatsUiState(
    val loading: Boolean = false,
    val error: String? = null,
    val summary: StatsSummary? = null,
)

class StatsViewModel(private val repo: ReachRepository = ReachRepository()) : ViewModel() {

    private val _state = MutableStateFlow(StatsUiState())
    val state = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            val s = repo.statsSummary().getOrNull()
            _state.update { it.copy(loading = false, summary = s) }
        }
    }
}
