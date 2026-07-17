package com.frischar.fantareal

import com.frischar.fantareal.domain.chat.ConversationMessage
import com.frischar.fantareal.domain.chat.MessageRole
import com.frischar.fantareal.domain.prompt.PromptBuildInput
import com.frischar.fantareal.domain.prompt.PromptBuilder
import com.frischar.fantareal.domain.rolecard.PersonaRuntime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PromptBuilderTest {
    @Test
    fun longTermMemoriesAreInjectedAndSystemHistoryIsExcluded() {
        val history = listOf(
            ConversationMessage("user-1", MessageRole.User, "上一轮用户消息", 1L),
            ConversationMessage("status", MessageRole.System, "记忆压缩失败提示", 2L),
            ConversationMessage("assistant-1", MessageRole.Assistant, "上一轮助手消息", 3L)
        )

        val result = PromptBuilder().build(
            PromptBuildInput(
                systemRules = "系统规则",
                persona = PersonaRuntime(name = "测试角色", systemPrompt = "角色设定"),
                memories = listOf("第一轮长期记忆", "第二轮长期记忆"),
                history = history,
                latestUserInput = "第三轮用户消息"
            )
        )

        val system = result.system.orEmpty()
        assertTrue(system.contains("## Long Term Memory"))
        assertTrue(system.contains("第一轮长期记忆"))
        assertTrue(system.contains("第二轮长期记忆"))
        assertFalse(result.messages.any { it.content.contains("记忆压缩失败提示") })
        assertEquals(
            listOf("上一轮用户消息", "上一轮助手消息", "第三轮用户消息"),
            result.messages.map { it.content }
        )
    }

    @Test
    fun onlyTheConfiguredRecentHistoryIsSentWithTheLatestInput() {
        val history = (1..12).map { index ->
            ConversationMessage(
                id = "message-$index",
                role = if (index % 2 == 0) MessageRole.Assistant else MessageRole.User,
                content = "消息-$index",
                createdAt = index.toLong()
            )
        }

        val result = PromptBuilder().build(
            PromptBuildInput(
                systemRules = "系统规则",
                persona = PersonaRuntime(systemPrompt = "角色设定"),
                history = history,
                latestUserInput = "最新消息",
                maxHistoryMessages = 10
            )
        )

        assertEquals(11, result.messages.size)
        assertEquals("消息-3", result.messages.first().content)
        assertEquals("最新消息", result.messages.last().content)
    }
}
