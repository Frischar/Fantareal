package com.frischar.fantareal.domain.statejournal

import com.frischar.fantareal.core.AppJson
import java.security.MessageDigest
import kotlin.math.abs
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject

class StateJournalEngine {
    fun parseConfig(element: JsonElement?): StateJournalConfig {
        val root = element as? JsonObject ?: return StateJournalConfig()
        val enabled = root.booleanValue("enabled", default = true)
        val roles = (root["roles"] as? JsonArray).orEmpty().mapNotNull roleLoop@ { roleElement ->
            val role = roleElement as? JsonObject ?: return@roleLoop null
            val roleId = role.stringValue("role_id", "roleId", "id")
            if (roleId.isBlank()) return@roleLoop null
            val variables = (role["variables"] as? JsonArray).orEmpty().mapNotNull variableLoop@ { variableElement ->
                val variable = variableElement as? JsonObject ?: return@variableLoop null
                val key = variable.stringValue("var_key", "varKey", "key")
                if (key.isBlank()) return@variableLoop null
                val minValue = variable.doubleValue("min_value", "minValue") ?: 0.0
                val maxValue = variable.doubleValue("max_value", "maxValue") ?: 100.0
                val lower = minOf(minValue, maxValue)
                val upper = maxOf(minValue, maxValue)
                StateJournalVariableDefinition(
                    key = key,
                    name = variable.stringValue("var_name", "varName", "name").ifBlank { key },
                    enabled = variable.booleanValue("enabled", default = true),
                    defaultValue = (variable.doubleValue("default_value", "defaultValue", "value") ?: lower)
                        .coerceIn(lower, upper),
                    minValue = lower,
                    maxValue = upper,
                    deltaMin = variable.doubleValue("delta_min", "deltaMin"),
                    deltaMax = variable.doubleValue("delta_max", "deltaMax"),
                    display = variable.booleanValue("display", default = true),
                    stageRelevant = variable.booleanValue("stage_relevant", "stageRelevant", default = true),
                    instruction = variable.stringValue("instruction")
                )
            }
            val stages = (role["stages"] as? JsonArray).orEmpty().mapNotNull stageLoop@ { stageElement ->
                val stage = stageElement as? JsonObject ?: return@stageLoop null
                val key = stage.stringValue("stage_key", "stageKey", "key")
                if (key.isBlank()) return@stageLoop null
                val conditions = (stage["conditions"] as? JsonArray).orEmpty().mapNotNull conditionLoop@ { conditionElement ->
                    val condition = conditionElement as? JsonObject ?: return@conditionLoop null
                    val variable = condition.stringValue("var", "field")
                    val target = condition["value"] ?: return@conditionLoop null
                    if (variable.isBlank()) return@conditionLoop null
                    StateJournalStageCondition(
                        variable = variable,
                        operator = condition.stringValue("op").takeIf(ALLOWED_OPERATORS::contains) ?: ">=",
                        target = target
                    )
                }
                StateJournalStageDefinition(
                    key = key,
                    name = stage.stringValue("stage_name", "stageName", "name", "title").ifBlank { key },
                    enabled = stage.booleanValue("enabled", default = true),
                    priority = stage.intValue("priority") ?: 0,
                    conditionMode = stage.stringValue("condition_mode", "conditionMode")
                        .lowercase().takeIf { it == "any" } ?: "all",
                    conditions = conditions,
                    allowRegression = stage.booleanOrNull("allow_regression", "allowRegression"),
                    confirmTurns = stage.intValue("confirm_turns", "confirmTurns")?.coerceAtLeast(1),
                    cooldownTurns = stage.intValue("cooldown_turns", "cooldownTurns")?.coerceAtLeast(0),
                    activationTag = stage.stringValue("activation_tag", "activationTag", "active_tag"),
                    emitsTags = stage["emits_tags"].asStringList()
                )
            }
            val snapshotFields = ((role["snapshotFields"] ?: role["snapshot_fields"]) as? JsonArray)
                .orEmpty().mapNotNull snapshotLoop@ { fieldElement ->
                    val field = fieldElement as? JsonObject ?: return@snapshotLoop null
                    val key = field.stringValue("key", "field_key")
                    if (key.isBlank()) return@snapshotLoop null
                    StateJournalSnapshotFieldDefinition(
                        key = key,
                        label = field.stringValue("label", "name").ifBlank { key },
                        enabled = field.booleanValue("enabled", default = true),
                        display = field.booleanValue("display", default = true),
                        instruction = field.stringValue("instruction")
                    )
                }
            val settings = role["settings"] as? JsonObject
            StateJournalRoleDefinition(
                roleId = roleId,
                roleName = role.stringValue("role_name", "roleName", "name").ifBlank { roleId },
                aliases = role["aliases"].asStringList(),
                enabled = role.booleanValue("enabled", default = true),
                initialStage = role.stringValue("initial_stage", "initialStage").ifBlank {
                    stages.firstOrNull()?.key ?: "stage_a"
                },
                variables = variables,
                stages = stages,
                snapshotFields = snapshotFields,
                settings = StateJournalRoleSettings(
                    allowRegression = settings?.booleanValue("allow_regression", "allowRegression", default = false) ?: false,
                    confirmTurns = (settings?.intValue("confirm_turns", "confirmTurns") ?: 1).coerceAtLeast(1),
                    cooldownTurns = (settings?.intValue("cooldown_turns", "cooldownTurns") ?: 0).coerceAtLeast(0)
                )
            )
        }
        return StateJournalConfig(
            version = root.intValue("version")?.coerceAtLeast(1) ?: 1,
            enabled = enabled,
            activeStageTags = root["active_stage_tags"].asStringList(),
            roles = roles
        )
    }

    fun initialize(config: StateJournalConfig, now: Long = System.currentTimeMillis()): StateJournalRuntime {
        return StateJournalRuntime(
            version = config.version,
            configSignature = configSignature(config),
            roles = config.roles.filter { it.enabled }.map { role ->
                val initialStage = role.stages.firstOrNull { it.key == role.initialStage }
                    ?: role.stages.firstOrNull { it.enabled }
                StateJournalRoleRuntime(
                    roleId = role.roleId,
                    roleName = role.roleName,
                    variables = role.variables.filter { it.enabled }.map { variable ->
                        StateJournalVariableRuntime(
                            key = variable.key,
                            name = variable.name,
                            value = variable.defaultValue,
                            maximum = variable.maxValue,
                            display = variable.display
                        )
                    },
                    activeStageKey = initialStage?.key.orEmpty(),
                    activeStageName = initialStage?.name.orEmpty(),
                    stageReason = "使用初始阶段",
                    updatedAt = now
                )
            },
            updatedAt = now
        )
    }

    fun parseAnalysis(raw: String): StateJournalAnalysis? {
        val jsonText = raw.trim()
            .replace(Regex("(?is)^```(?:json)?\\s*"), "")
            .replace(Regex("(?is)\\s*```$"), "")
            .replace(Regex("(?is)<think(?:ing)?>.*?</think(?:ing)?>"), "")
            .replace(Regex("(?is)<reasoning>.*?</reasoning>"), "")
            .let { text ->
                val start = text.indexOf('{')
                val end = text.lastIndexOf('}')
                if (start >= 0 && end > start) text.substring(start, end + 1) else text
            }
        val root = runCatching { AppJson.parseToJsonElement(jsonText) as? JsonObject }.getOrNull() ?: return null
        val updates = root["updates"] as? JsonObject ?: return null
        val display = root["display"] as? JsonObject ?: return null
        val rawVariables = updates["variables"] as? JsonArray ?: return null
        val variableUpdates = rawVariables.mapNotNull updateLoop@ { updateElement ->
            val update = updateElement as? JsonObject ?: return@updateLoop null
            val roleId = update.stringValue("roleId", "role_id")
            val key = update.stringValue("key", "var_key")
            val value = update.doubleValue("value")
            val delta = update.doubleValue("delta")
            if (roleId.isBlank() || key.isBlank() || (value == null && delta == null)) return@updateLoop null
            StateJournalVariableUpdate(roleId, key, value, delta, update.stringValue("reason"))
        }
        val characterSnapshots = (display["characters"] as? JsonArray).orEmpty().mapNotNull characterLoop@ { characterElement ->
            val character = characterElement as? JsonObject ?: return@characterLoop null
            val roleId = character.stringValue("roleId", "role_id")
            if (roleId.isBlank()) return@characterLoop null
            val fields = (character["fields"] as? JsonArray).orEmpty().mapNotNull fieldLoop@ { fieldElement ->
                val field = fieldElement as? JsonObject ?: return@fieldLoop null
                val key = field.stringValue("key", "field_key")
                val value = (field["value"] as? JsonPrimitive)?.contentOrNull?.trim().orEmpty()
                if (key.isBlank() || value.isBlank()) null else key to value
            }.toMap()
            StateJournalCharacterSnapshot(roleId, fields)
        }
        return StateJournalAnalysis(
            variableUpdates = variableUpdates,
            characterSnapshots = characterSnapshots,
            title = display.stringValue("title"),
            summary = display.stringValue("summary")
        )
    }

    fun applyAnalysis(
        config: StateJournalConfig,
        runtime: StateJournalRuntime,
        analysis: StateJournalAnalysis,
        now: Long = System.currentTimeMillis()
    ): StateJournalRuntime {
        if (!config.enabled) return runtime
        val nextTurn = runtime.turnOrdinal + 1
        val updateMap = analysis.variableUpdates.associateBy { it.roleId to it.key }
        val snapshotMap = analysis.characterSnapshots.associateBy { it.roleId }
        val currentRoles = runtime.roles.associateBy { it.roleId }
        val roles = config.roles.filter { it.enabled }.map { role ->
            val current = currentRoles[role.roleId]
                ?: initialize(StateJournalConfig(enabled = true, roles = listOf(role)), now).roles.single()
            val currentVariables = current.variables.associateBy { it.key }
            val variables = role.variables.filter { it.enabled }.map { definition ->
                val prior = currentVariables[definition.key] ?: StateJournalVariableRuntime(
                    key = definition.key,
                    name = definition.name,
                    value = definition.defaultValue,
                    maximum = definition.maxValue,
                    display = definition.display
                )
                val update = updateMap[role.roleId to definition.key]
                if (update == null) {
                    prior.copy(delta = 0.0, reason = "", display = definition.display)
                } else {
                    val requestedDelta = update.delta ?: update.value?.minus(prior.value) ?: 0.0
                    val deltaLower = definition.deltaMin ?: Double.NEGATIVE_INFINITY
                    val deltaUpper = definition.deltaMax ?: Double.POSITIVE_INFINITY
                    val boundedDelta = requestedDelta.coerceIn(minOf(deltaLower, deltaUpper), maxOf(deltaLower, deltaUpper))
                    val nextValue = (prior.value + boundedDelta).coerceIn(definition.minValue, definition.maxValue)
                    prior.copy(
                        name = definition.name,
                        value = nextValue,
                        maximum = definition.maxValue,
                        delta = nextValue - prior.value,
                        reason = update.reason.take(240),
                        display = definition.display
                    )
                }
            }
            val configuredSnapshots = role.snapshotFields.filter { it.enabled }.associateBy { it.key }
            val incomingSnapshots = snapshotMap[role.roleId]?.fields.orEmpty()
            val snapshots = current.snapshots.toMutableMap().apply {
                incomingSnapshots.forEach { (key, value) ->
                    if (configuredSnapshots.containsKey(key) && value.isNotBlank()) put(key, value.take(500))
                }
                if (configuredSnapshots.containsKey("summary") &&
                    !incomingSnapshots.containsKey("summary") && analysis.summary.isNotBlank()
                ) {
                    put("summary", analysis.summary.take(500))
                }
            }.filterKeys(configuredSnapshots::containsKey)
            evaluateStage(role, current.copy(variables = variables, snapshots = snapshots), nextTurn, now)
        }
        return runtime.copy(
            version = config.version,
            configSignature = configSignature(config),
            turnOrdinal = nextTurn,
            roles = roles,
            displayTitle = analysis.title.take(300),
            displaySummary = analysis.summary.take(1000),
            updatedAt = now
        )
    }

    fun activeStageTags(config: StateJournalConfig, runtime: StateJournalRuntime): Set<String> {
        if (!config.enabled) return emptySet()
        val runtimeRoles = runtime.roles.associateBy { it.roleId }
        val stageTags = config.roles.filter { it.enabled }.flatMap { role ->
            val stageKey = runtimeRoles[role.roleId]?.activeStageKey?.takeIf { it.isNotBlank() }
                ?: role.initialStage
            val stage = role.stages.firstOrNull { it.key == stageKey }
            val activeTag = stage?.activationTag?.takeIf { it.isNotBlank() }
                ?: stageKey.takeIf { it.isNotBlank() }?.let { "state_journal.stage.${role.roleId}.$it" }
            listOfNotNull(activeTag) + stage?.emitsTags.orEmpty()
        }
        return (config.activeStageTags + stageTags).filter { it.isNotBlank() }.toSet()
    }

    fun buildRuntimePrompt(config: StateJournalConfig, runtime: StateJournalRuntime): String {
        if (!config.enabled || runtime.roles.isEmpty()) return ""
        val definitions = config.roles.associateBy { it.roleId }
        return buildString {
            appendLine("以下是 StateJournal 当前运行时状态。它覆盖角色卡中的初始值；继续剧情时必须保持一致，不要在正文中输出本段结构。")
            runtime.roles.forEach { role ->
                val definition = definitions[role.roleId]
                appendLine()
                appendLine("${role.roleName} · ${role.activeStageName.ifBlank { role.activeStageKey }}")
                val variables = role.variables.filter { it.display }.joinToString("，") {
                    "${it.name}=${formatNumber(it.value)}"
                }
                if (variables.isNotBlank()) appendLine("变量：$variables")
                val labels = definition?.snapshotFields.orEmpty().associate { it.key to it.label }
                val snapshots = role.snapshots.entries.mapNotNull { (key, value) ->
                    value.takeIf { it.isNotBlank() }?.let { "${labels[key] ?: key}=$it" }
                }.joinToString("；")
                if (snapshots.isNotBlank()) appendLine("幕笺：$snapshots")
            }
        }.trim()
    }

    fun buildAnalysisPrompt(config: StateJournalConfig, runtime: StateJournalRuntime, assistantContent: String): String {
        if (!config.enabled || config.roles.none { it.enabled }) return ""
        val runtimeRoles = runtime.roles.associateBy { it.roleId }
        val roleConfig = buildJsonArray {
            config.roles.filter { it.enabled }.forEach { role ->
                val current = runtimeRoles[role.roleId]
                add(buildJsonObject {
                    put("role_id", role.roleId)
                    put("role_name", role.roleName)
                    put("active_stage", current?.activeStageKey.orEmpty())
                    putJsonArray("variables") {
                        role.variables.filter { it.enabled }.forEach { variable ->
                            val currentVariable = current?.variables?.firstOrNull { it.key == variable.key }
                            add(buildJsonObject {
                                put("var_key", variable.key)
                                put("var_name", variable.name)
                                put("current_value", currentVariable?.value ?: variable.defaultValue)
                                put("min_value", variable.minValue)
                                put("max_value", variable.maxValue)
                                variable.deltaMin?.let { put("delta_min", it) }
                                variable.deltaMax?.let { put("delta_max", it) }
                                put("instruction", variable.instruction)
                            })
                        }
                    }
                    putJsonArray("snapshotFields") {
                        role.snapshotFields.filter { it.enabled }.forEach { field ->
                            add(buildJsonObject {
                                put("key", field.key)
                                put("label", field.label)
                                put("instruction", field.instruction)
                            })
                        }
                    }
                })
            }
        }
        return """
            请根据本轮助手回复和 StateJournal 角色配置，只返回一个合法 JSON 对象，不输出 Markdown 或解释。
            根对象必须包含 updates 和 display：
            updates 固定为 {"schemaVersion":1,"variables":[]}；variables 每项只能使用已配置的 roleId 和 key，包含本轮后的 value 或 delta，可选 reason。严格遵守 delta_min、delta_max、min_value、max_value；没有明确变化的变量不要输出。
            不得输出或决定阶段，阶段由程序根据变量、本地条件、连续确认和冷却规则计算。
            display 固定为 {"title":"","summary":"","characters":[]}；characters 每项使用 {"roleId":"","name":"","fields":[]}，fields 只使用对应角色 snapshotFields 中已有的 key、label，并记录正文中可观察到的状态。不得替用户决定动作、台词、心理或选择。

            角色配置与当前值：
            $roleConfig

            助手回复：
            ${assistantContent.take(16000)}
        """.trimIndent()
    }

    fun configSignature(config: StateJournalConfig): String {
        val bytes = AppJson.encodeToString(StateJournalConfig.serializer(), config).toByteArray(Charsets.UTF_8)
        return MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    }

    private fun evaluateStage(
        role: StateJournalRoleDefinition,
        current: StateJournalRoleRuntime,
        turnOrdinal: Long,
        now: Long
    ): StateJournalRoleRuntime {
        val enabledStages = role.stages.filter { it.enabled }
        if (enabledStages.isEmpty()) return current.copy(updatedAt = now)
        val values = current.variables.associate { it.key to it.value }
        var target = enabledStages.sortedByDescending { it.priority }.firstOrNull { stageMatches(it, values) }
            ?: enabledStages.firstOrNull { it.key == role.initialStage }
            ?: enabledStages.first()
        val currentStage = enabledStages.firstOrNull { it.key == current.activeStageKey }
        var changed = currentStage != null && target.key != currentStage.key
        var reason = if (target.conditions.isEmpty()) "使用初始阶段" else "阶段条件已满足"
        var candidateKey = current.candidateStageKey
        var candidateCount = current.candidateCount
        var cooldownUntil = current.cooldownUntilTurn

        if (changed && currentStage != null) {
            val allowRegression = target.allowRegression ?: role.settings.allowRegression
            if (target.priority < currentStage.priority && !allowRegression) {
                target = currentStage
                changed = false
                reason = "目标阶段优先级较低且未允许回退"
            } else if (cooldownUntil > turnOrdinal) {
                target = currentStage
                changed = false
                reason = "阶段仍在冷却期"
            }
        }

        if (changed && currentStage != null) {
            val confirmTurns = target.confirmTurns ?: role.settings.confirmTurns
            candidateCount = if (candidateKey == target.key) candidateCount + 1 else 1
            candidateKey = target.key
            if (candidateCount < confirmTurns.coerceAtLeast(1)) {
                target = currentStage
                changed = false
                reason = "候选阶段等待连续确认（$candidateCount/${confirmTurns.coerceAtLeast(1)}）"
            } else {
                cooldownUntil = turnOrdinal + (target.cooldownTurns ?: role.settings.cooldownTurns).coerceAtLeast(0)
                candidateKey = ""
                candidateCount = 0
            }
        } else if (target.key == current.activeStageKey && reason != "阶段仍在冷却期") {
            candidateKey = ""
            candidateCount = 0
        }

        return current.copy(
            activeStageKey = target.key,
            activeStageName = target.name,
            previousStageKey = if (changed) current.activeStageKey else current.previousStageKey,
            previousStageName = if (changed) current.activeStageName else current.previousStageName,
            stageChanged = changed,
            candidateStageKey = candidateKey,
            candidateCount = candidateCount,
            cooldownUntilTurn = cooldownUntil,
            stageReason = reason,
            updatedAt = now
        )
    }

    private fun stageMatches(stage: StateJournalStageDefinition, values: Map<String, Double>): Boolean {
        if (stage.conditions.isEmpty()) return false
        val results = stage.conditions.map { condition ->
            val current = values[condition.variable] ?: return@map false
            val target = (condition.target as? JsonPrimitive)?.doubleOrNull ?: return@map false
            when (condition.operator) {
                ">" -> current > target
                ">=" -> current >= target
                "<" -> current < target
                "<=" -> current <= target
                "=" -> abs(current - target) < 0.000001
                "!=" -> abs(current - target) >= 0.000001
                else -> false
            }
        }
        return if (stage.conditionMode == "any") results.any { it } else results.all { it }
    }

    private fun formatNumber(value: Double): String {
        val whole = value.toLong()
        return if (abs(value - whole.toDouble()) < 0.000001) whole.toString()
        else value.toString().trimEnd('0').trimEnd('.')
    }

    private fun JsonObject.stringValue(vararg keys: String): String = keys.firstNotNullOfOrNull { key ->
        (this[key] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
    }.orEmpty()

    private fun JsonObject.doubleValue(vararg keys: String): Double? = keys.firstNotNullOfOrNull { key ->
        (this[key] as? JsonPrimitive)?.doubleOrNull
    }

    private fun JsonObject.intValue(vararg keys: String): Int? = keys.firstNotNullOfOrNull { key ->
        (this[key] as? JsonPrimitive)?.intOrNull
    }

    private fun JsonObject.booleanOrNull(vararg keys: String): Boolean? = keys.firstNotNullOfOrNull { key ->
        (this[key] as? JsonPrimitive)?.booleanOrNull
    }

    private fun JsonObject.booleanValue(vararg keys: String, default: Boolean): Boolean =
        booleanOrNull(*keys) ?: default

    private fun JsonElement?.asStringList(): List<String> = (this as? JsonArray).orEmpty().mapNotNull {
        (it as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf(String::isNotBlank)
    }

    companion object {
        const val ANALYSIS_SYSTEM_PROMPT =
            "你是 Fantareal StateJournal Worker，必须产生结构化 JSON；不得决定角色阶段。"
        private val ALLOWED_OPERATORS = setOf(">", ">=", "<", "<=", "=", "!=")
    }
}
