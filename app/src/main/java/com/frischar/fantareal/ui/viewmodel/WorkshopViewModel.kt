package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.WorkshopRepository
import com.frischar.fantareal.domain.workshop.WorkshopState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class WorkshopUiState(
    val state: WorkshopState = WorkshopState()
)

class WorkshopViewModel(
    private val workshopRepository: WorkshopRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(WorkshopUiState())
    val uiState: StateFlow<WorkshopUiState> = _uiState.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _uiState.value = WorkshopUiState(workshopRepository.loadState())
        }
    }
}
