package com.frischar.fantareal.domain.workshop

import kotlinx.serialization.Serializable

@Serializable
data class WorkshopState(
    val stage: String = "A",
    val stageName: String = "初始相遇",
    val affinity: Int = 2,
    val stagePrompt: String = "当前处于初始相遇阶段。保持礼貌、自然、克制，优先建立信任。"
)
