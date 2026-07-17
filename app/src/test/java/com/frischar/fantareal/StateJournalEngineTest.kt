package com.frischar.fantareal

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.statejournal.StateJournalEngine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class StateJournalEngineTest {
    private val engine = StateJournalEngine()

    @Test
    fun initializesConfiguredRolesVariablesAndInitialStage() {
        val config = engine.parseConfig(AppJson.parseToJsonElement(TEST_CONFIG))
        val runtime = engine.initialize(config, now = 100L)

        assertTrue(config.enabled)
        assertEquals(2, runtime.roles.size)
        assertEquals("stage_a", runtime.role("shen_qixue").activeStageKey)
        assertEquals(38.0, runtime.role("shen_qixue").variable("trust").value, 0.001)
        assertEquals("stage_a", runtime.role("lu_qingyuan").activeStageKey)
        assertEquals(68.0, runtime.role("lu_qingyuan").variable("guard").value, 0.001)
        assertEquals(
            setOf(
                "state_journal.stage.shen_qixue.stage_a",
                "state_journal.stage.lu_qingyuan.stage_a"
            ),
            engine.activeStageTags(config, runtime)
        )
    }

    @Test
    fun clampsPerTurnDeltasThenMovesBothRolesToStageB() {
        val config = engine.parseConfig(AppJson.parseToJsonElement(TEST_CONFIG))
        val initial = engine.initialize(config, now = 100L)
        val analysis = requireNotNull(engine.parseAnalysis(ANALYSIS_TO_B))

        val updated = engine.applyAnalysis(config, initial, analysis, now = 200L)

        val shen = updated.role("shen_qixue")
        assertEquals(41.0, shen.variable("trust").value, 0.001)
        assertEquals(31.0, shen.variable("warmth").value, 0.001)
        assertEquals("stage_b", shen.activeStageKey)
        assertEquals("温和而专注", shen.snapshots["emotion"])
        assertEquals("整理药箱", shen.snapshots["care_action"])

        val lu = updated.role("lu_qingyuan")
        assertEquals(27.0, lu.variable("trust").value, 0.001)
        assertEquals(64.0, lu.variable("guard").value, 0.001)
        assertEquals("stage_b", lu.activeStageKey)
        assertEquals(1L, updated.turnOrdinal)
        assertEquals(
            setOf(
                "state_journal.stage.shen_qixue.stage_b",
                "state_journal.stage.lu_qingyuan.stage_b"
            ),
            engine.activeStageTags(config, updated)
        )
    }

    @Test
    fun selectsHighestMatchingStageAndDoesNotRegressByDefault() {
        val config = engine.parseConfig(AppJson.parseToJsonElement(TEST_CONFIG))
        val initial = engine.initialize(config, now = 100L)
        val middle = engine.applyAnalysis(
            config,
            initial,
            requireNotNull(engine.parseAnalysis(ANALYSIS_TO_B)),
            now = 150L
        )
        val high = engine.applyAnalysis(
            config,
            middle,
            requireNotNull(engine.parseAnalysis(ANALYSIS_TO_C)),
            now = 200L
        )

        assertEquals("stage_c", high.role("shen_qixue").activeStageKey)

        val attemptedRegression = engine.applyAnalysis(
            config,
            high,
            requireNotNull(engine.parseAnalysis(ANALYSIS_REGRESSION)),
            now = 300L
        )
        assertEquals("stage_c", attemptedRegression.role("shen_qixue").activeStageKey)
    }

    @Test
    fun rejectsMalformedAnalysisWithoutInventingUpdates() {
        assertNull(engine.parseAnalysis("```json\n{not valid}\n```"))
        assertNull(engine.parseAnalysis("{\"display\":{}}"))
    }

    @Test
    fun promptsContainCurrentValuesAndLockStageDecisionToLocalRules() {
        val config = engine.parseConfig(AppJson.parseToJsonElement(TEST_CONFIG))
        val runtime = engine.applyAnalysis(
            config,
            engine.initialize(config, now = 100L),
            requireNotNull(engine.parseAnalysis(ANALYSIS_TO_B)),
            now = 200L
        )

        val context = engine.buildRuntimePrompt(config, runtime)
        val analysisPrompt = engine.buildAnalysisPrompt(config, runtime, "她把药箱推到桌边。")

        assertTrue(context.contains("沈栖雪 · B阶段"))
        assertTrue(context.contains("信任=41"))
        assertTrue(context.contains("情绪=温和而专注"))
        assertTrue(analysisPrompt.contains("不得输出或决定阶段"))
        assertTrue(analysisPrompt.contains("delta_min"))
        assertTrue(analysisPrompt.contains("她把药箱推到桌边"))
    }

    private fun com.frischar.fantareal.domain.statejournal.StateJournalRuntime.role(id: String) =
        roles.single { it.roleId == id }

    private fun com.frischar.fantareal.domain.statejournal.StateJournalRoleRuntime.variable(key: String) =
        variables.single { it.key == key }

    companion object {
        private val TEST_CONFIG = """
            {
              "version": 1,
              "enabled": true,
              "roles": [
                {
                  "role_id": "shen_qixue",
                  "role_name": "沈栖雪",
                  "enabled": true,
                  "initial_stage": "stage_a",
                  "variables": [
                    {"var_key":"trust","var_name":"信任","enabled":true,"default_value":38,"min_value":0,"max_value":100,"delta_min":-2,"delta_max":3,"display":true,"stage_relevant":true},
                    {"var_key":"warmth","var_name":"温度","enabled":true,"default_value":28,"min_value":0,"max_value":100,"delta_min":-1,"delta_max":3,"display":true,"stage_relevant":true},
                    {"var_key":"worry","var_name":"担忧","enabled":true,"default_value":32,"min_value":0,"max_value":100,"delta_min":-2,"delta_max":4,"display":true,"stage_relevant":true}
                  ],
                  "stages": [
                    {"stage_key":"stage_a","stage_name":"A阶段","enabled":true,"priority":10,"condition_mode":"all","conditions":[{"var":"trust","op":"<","value":42}],"allow_regression":false,"confirm_turns":1,"cooldown_turns":1,"activation_tag":"state_journal.stage.shen_qixue.stage_a"},
                    {"stage_key":"stage_b","stage_name":"B阶段","enabled":true,"priority":30,"condition_mode":"all","conditions":[{"var":"trust","op":">=","value":40},{"var":"warmth","op":">=","value":29}],"allow_regression":false,"confirm_turns":1,"cooldown_turns":1,"activation_tag":"state_journal.stage.shen_qixue.stage_b"},
                    {"stage_key":"stage_c","stage_name":"C阶段","enabled":true,"priority":60,"condition_mode":"all","conditions":[{"var":"trust","op":">=","value":44},{"var":"warmth","op":">=","value":34},{"var":"worry","op":">=","value":30}],"allow_regression":false,"confirm_turns":1,"cooldown_turns":1,"activation_tag":"state_journal.stage.shen_qixue.stage_c"}
                  ],
                  "snapshotFields": [
                    {"key":"emotion","label":"情绪","enabled":true,"display":true},
                    {"key":"care_action","label":"照料动作","enabled":true,"display":true},
                    {"key":"summary","label":"摘要","enabled":true,"display":true}
                  ],
                  "settings":{"allow_regression":false,"confirm_turns":1,"cooldown_turns":1}
                },
                {
                  "role_id": "lu_qingyuan",
                  "role_name": "陆青鸢",
                  "enabled": true,
                  "initial_stage": "stage_a",
                  "variables": [
                    {"var_key":"trust","var_name":"信任","enabled":true,"default_value":24,"min_value":0,"max_value":100,"delta_min":-3,"delta_max":3,"display":true,"stage_relevant":true},
                    {"var_key":"guard","var_name":"戒备","enabled":true,"default_value":68,"min_value":0,"max_value":100,"delta_min":-4,"delta_max":3,"display":true,"stage_relevant":true},
                    {"var_key":"respect","var_name":"认可","enabled":true,"default_value":30,"min_value":0,"max_value":100,"delta_min":-2,"delta_max":3,"display":true,"stage_relevant":true}
                  ],
                  "stages": [
                    {"stage_key":"stage_a","stage_name":"A阶段","enabled":true,"priority":10,"conditions":[{"var":"guard","op":">","value":55}],"activation_tag":"state_journal.stage.lu_qingyuan.stage_a"},
                    {"stage_key":"stage_b","stage_name":"B阶段","enabled":true,"priority":35,"conditions":[{"var":"trust","op":">=","value":27},{"var":"guard","op":"<=","value":65}],"activation_tag":"state_journal.stage.lu_qingyuan.stage_b"}
                  ],
                  "snapshotFields": [{"key":"emotion","label":"情绪","enabled":true,"display":true}],
                  "settings":{"allow_regression":false,"confirm_turns":1,"cooldown_turns":1}
                }
              ]
            }
        """.trimIndent()

        private val ANALYSIS_TO_B = """
            {
              "updates": {
                "schemaVersion": 1,
                "variables": [
                  {"roleId":"shen_qixue","key":"trust","value":99,"delta":50,"reason":"接受帮助"},
                  {"roleId":"shen_qixue","key":"warmth","value":31,"delta":3},
                  {"roleId":"lu_qingyuan","key":"trust","value":27,"delta":3},
                  {"roleId":"lu_qingyuan","key":"guard","value":64,"delta":-4}
                ]
              },
              "display": {
                "title":"药室中的试探",
                "summary":"两人的态度都有所缓和。",
                "characters":[
                  {"roleId":"shen_qixue","name":"沈栖雪","fields":[{"key":"emotion","label":"情绪","value":"温和而专注"},{"key":"care_action","label":"照料动作","value":"整理药箱"}]},
                  {"roleId":"lu_qingyuan","name":"陆青鸢","fields":[{"key":"emotion","label":"情绪","value":"戒备稍缓"}]}
                ]
              }
            }
        """.trimIndent()

        private val ANALYSIS_TO_C = """
            {"updates":{"schemaVersion":1,"variables":[
              {"roleId":"shen_qixue","key":"trust","delta":6},
              {"roleId":"shen_qixue","key":"warmth","delta":6},
              {"roleId":"shen_qixue","key":"worry","delta":0}
            ]},"display":{"summary":"关系快速推进","characters":[]}}
        """.trimIndent()

        private val ANALYSIS_REGRESSION = """
            {"updates":{"schemaVersion":1,"variables":[
              {"roleId":"shen_qixue","key":"trust","delta":-2},
              {"roleId":"shen_qixue","key":"warmth","delta":-1}
            ]},"display":{"summary":"短暂疏离","characters":[]}}
        """.trimIndent()
    }
}
