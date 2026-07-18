package com.frischar.fantareal.domain.llm

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Test

class ModelCatalogTest {
    @Test
    fun openAiProviderFetchesAndDeduplicatesAvailableModels() = runBlocking {
        val server = MockWebServer()
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(
                    """{"data":[{"id":"chat-model"},{"id":"chat-model"},{"id":"text-embedding-3-small"},{"owned_by":"test"}]}"""
                )
        )
        server.start()

        try {
            val models = OpenAiProvider(
                server.url("/v1/chat/completions").toString(),
                "test-key"
            ).fetchAvailableModels()

            assertEquals(listOf("chat-model", "text-embedding-3-small"), models)
            val request = server.takeRequest()
            assertEquals("/v1/models", request.path)
            assertEquals("Bearer test-key", request.getHeader("Authorization"))
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun preferredChatModelUsesSafeSelectionOrder() {
        assertEquals(
            "current-chat",
            choosePreferredChatModel(
                currentModel = "current-chat",
                recommendedModel = "recommended-chat",
                availableModels = listOf("recommended-chat", "current-chat")
            )
        )
        assertEquals(
            "recommended-chat",
            choosePreferredChatModel(
                currentModel = "missing-chat",
                recommendedModel = "recommended-chat",
                availableModels = listOf("recommended-chat", "other-chat")
            )
        )
        assertEquals(
            "only-chat",
            choosePreferredChatModel(
                currentModel = "",
                recommendedModel = "",
                availableModels = listOf("text-embedding-3-small", "only-chat")
            )
        )
        assertEquals(
            "",
            choosePreferredChatModel(
                currentModel = "missing-chat",
                recommendedModel = "missing-recommended",
                availableModels = listOf("chat-a", "chat-b", "text-embedding-3-small")
            )
        )
    }

    @Test
    fun providerSwitchClearsOnlyCredentialsThatWouldCrossServiceBoundaries() {
        assertEquals(
            true,
            shouldClearApiKeyForProviderSwitch(
                currentBaseUrl = "https://api.openai.com/v1",
                nextBaseUrl = "https://api.deepseek.com/v1",
                apiKey = "openai-key"
            )
        )
        assertEquals(
            false,
            shouldClearApiKeyForProviderSwitch(
                currentBaseUrl = "https://api.openai.com/v1/chat/completions",
                nextBaseUrl = "https://api.openai.com/v1/",
                apiKey = "openai-key"
            )
        )
        assertEquals(
            false,
            shouldClearApiKeyForProviderSwitch(
                currentBaseUrl = "https://api.openai.com/v1",
                nextBaseUrl = "https://api.deepseek.com/v1",
                apiKey = ""
            )
        )
    }
}
