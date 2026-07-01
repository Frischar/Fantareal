package com.frischar.fantareal.domain.worldbook

import kotlin.random.Random

class WorldbookEngine(
    private val random: Random = Random.Default,
    private val recursionLimit: Int = 3
) {
    private val stickyRemaining = mutableMapOf<String, Int>()
    private val cooldownRemaining = mutableMapOf<String, Int>()

    fun scan(
        entries: List<WorldbookEntry>,
        userInput: String,
        recentHistory: List<String>
    ): WorldbookScanResult {
        decrementTurnState()
        val sourceText = (recentHistory + userInput).joinToString("\n")
        val matched = mutableListOf<WorldbookEntry>()
        var scanText = sourceText

        repeat(recursionLimit.coerceAtLeast(1)) {
            val roundMatches = entries
                .filter { it.enabled }
                .filter { it.id !in matched.map(WorldbookEntry::id) }
                .filter { shouldInclude(it, scanText) }

            if (roundMatches.isEmpty()) return@repeat
            matched += roundMatches
            scanText += "\n" + roundMatches.joinToString("\n") { it.content }
        }

        val sorted = matched.sortedWith(compareByDescending<WorldbookEntry> { it.priority }.thenBy { it.title })
        sorted.forEach { entry ->
            if (entry.stickyTurns > 0) stickyRemaining[entry.id] = entry.stickyTurns
            if (entry.cooldownTurns > 0) cooldownRemaining[entry.id] = entry.cooldownTurns
        }

        return WorldbookScanResult(
            matches = sorted.map { WorldbookMatch(it, it.insertionPosition) }
        )
    }

    private fun shouldInclude(entry: WorldbookEntry, sourceText: String): Boolean {
        if (stickyRemaining.getOrDefault(entry.id, 0) > 0) return true
        if (cooldownRemaining.getOrDefault(entry.id, 0) > 0) return false
        if (entry.constant) return passesChance(entry)
        if (entry.primaryTriggers.isEmpty()) return false
        val primaryPasses = when (entry.primaryLogic) {
            TriggerLogic.All -> matchesAll(entry.primaryTriggers, entry, sourceText)
            TriggerLogic.Any -> matchesAny(entry.primaryTriggers, entry, sourceText)
        }
        if (!primaryPasses) return false

        val secondaryPasses = when {
            entry.secondaryTriggers.isEmpty() -> true
            entry.secondaryLogic == TriggerLogic.All -> matchesAll(entry.secondaryTriggers, entry, sourceText)
            else -> matchesAny(entry.secondaryTriggers, entry, sourceText)
        }

        return secondaryPasses && passesChance(entry)
    }

    private fun passesChance(entry: WorldbookEntry): Boolean {
        val chance = entry.chance.coerceIn(0.0, 1.0)
        return chance >= 1.0 || random.nextDouble() <= chance
    }

    private fun matchesAny(patterns: List<String>, entry: WorldbookEntry, sourceText: String): Boolean {
        return patterns.any { matches(it, entry, sourceText) }
    }

    private fun matchesAll(patterns: List<String>, entry: WorldbookEntry, sourceText: String): Boolean {
        return patterns.all { matches(it, entry, sourceText) }
    }

    private fun matches(pattern: String, entry: WorldbookEntry, sourceText: String): Boolean {
        if (pattern.isBlank()) return false
        return when (entry.triggerMode) {
            TriggerMode.Literal -> {
                if (!entry.wholeWord) {
                    sourceText.contains(pattern, ignoreCase = !entry.caseSensitive)
                } else {
                    val options = if (entry.caseSensitive) emptySet() else setOf(RegexOption.IGNORE_CASE)
                    val escaped = Regex.escape(pattern)
                    Regex("(?<![\\p{L}\\p{N}_])$escaped(?![\\p{L}\\p{N}_])", options).containsMatchIn(sourceText)
                }
            }
            TriggerMode.Regex -> runCatching {
                val options = if (entry.caseSensitive) emptySet() else setOf(RegexOption.IGNORE_CASE)
                Regex(pattern, options).containsMatchIn(sourceText)
            }.getOrDefault(false)
        }
    }

    private fun decrementTurnState() {
        decrement(stickyRemaining)
        decrement(cooldownRemaining)
    }

    private fun decrement(state: MutableMap<String, Int>) {
        val updated = state.mapValues { (_, turns) -> turns - 1 }
        state.clear()
        state.putAll(updated.filterValues { it > 0 })
    }
}
