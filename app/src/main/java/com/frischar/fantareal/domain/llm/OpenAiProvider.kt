package com.frischar.fantareal.domain.llm

import android.util.Log
import com.frischar.fantareal.core.AppJson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.BufferedReader
import java.util.concurrent.TimeUnit

@Serializable
data class OpenAiRequest(
    val model: String,
    val messages: List<OpenAiMessage>,
    val temperature: Double?,
    val stream: Boolean
)

@Serializable
data class OpenAiMessage(val role: String, val content: String)


@Serializable
data class OpenAiChunk(val choices: List<OpenAiChoice>? = null)

@Serializable
data class OpenAiChoice(
    val delta: OpenAiDelta? = null,
    val message: OpenAiResponseMessage? = null,
    val text: String? = null
)

@Serializable
data class OpenAiResponseMessage(
    val content: JsonElement? = null
)

@Serializable
data class OpenAiDelta(
    val content: String? = null,
    val reasoning_content: String? = null,
    val reasoning: String? = null,
    val thought: String? = null
)

class OpenAiProvider(
    private val baseUrl: String,
    private val apiKey: String
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(60, TimeUnit.SECONDS)
        .connectTimeout(60, TimeUnit.SECONDS)
        .build()

    fun stream(request: LlmRequest): Flow<LlmStreamEvent> = flow {
        val messages = mutableListOf<OpenAiMessage>()
        if (request.system != null) {
            messages.add(OpenAiMessage("system", request.system))
        }
        messages.addAll(request.messages.map { OpenAiMessage(it.role, it.content) })

        val openAiReq = OpenAiRequest(
            model = request.model,
            messages = messages,
            temperature = request.temperature,
            stream = request.stream
        )

        try {
            val jsonBody = AppJson.encodeToString(openAiReq)
            val httpReq = Request.Builder()
                .url(normalizeEndpoint(baseUrl))
                .apply {
                    if (apiKey.isNotBlank()) {
                        addHeader("Authorization", "Bearer $apiKey")
                    }
                }
                .post(jsonBody.toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(httpReq).execute().use { response ->
                if (!response.isSuccessful) {
                    val errorBody = response.body?.string()?.replace(Regex("\\s+"), " ")?.trim()?.take(500).orEmpty()
                    val suffix = if (errorBody.isBlank()) "" else ": $errorBody"
                    emit(LlmStreamEvent.Error("HTTP Error: ${response.code}$suffix"))
                    return@use
                }

                val body = response.body
                if (body == null) {
                    emit(LlmStreamEvent.Error("Empty body"))
                    return@use
                }

                if (!request.stream) {
                    val content = extractNonStreamingContent(body.string())
                    if (content.isBlank()) {
                        emit(LlmStreamEvent.Error("Empty assistant response"))
                    } else {
                        emit(LlmStreamEvent.Token(content))
                        emit(LlmStreamEvent.Done)
                    }
                    return@use
                }

                val reader = BufferedReader(body.charStream())
                var line: String?
                var inReasoning = false
                var emittedContent = false
                while (reader.readLine().also { line = it } != null) {
                    val currentLine = line ?: continue
                    if (currentLine.startsWith("data: ")) {
                        val data = currentLine.removePrefix("data: ").trim()
                        if (data == "[DONE]") break
                        try {
                            val chunk = AppJson.decodeFromString<OpenAiChunk>(data)
                            val delta = chunk.choices?.firstOrNull()?.delta
                            val reasoning = delta?.reasoning_content ?: delta?.reasoning ?: delta?.thought
                            val content = delta?.content

                            if (!reasoning.isNullOrEmpty()) {
                                if (!inReasoning) {
                                    emit(LlmStreamEvent.Token("<think>\n"))
                                    inReasoning = true
                                }
                                emit(LlmStreamEvent.Token(reasoning))
                            }

                            if (!content.isNullOrEmpty()) {
                                if (inReasoning) {
                                    emit(LlmStreamEvent.Token("\n</think>\n"))
                                    inReasoning = false
                                }
                                emit(LlmStreamEvent.Token(content))
                                emittedContent = true
                            }
                        } catch (e: Exception) {
                            Log.e("OpenAiProvider", "Parse error: $data", e)
                        }
                    }
                }
                if (inReasoning) {
                    emit(LlmStreamEvent.Token("\n</think>\n"))
                }
                if (emittedContent) {
                    emit(LlmStreamEvent.Done)
                } else {
                    emit(LlmStreamEvent.Error("Empty assistant response"))
                }
            }
        } catch (e: Exception) {
            emit(LlmStreamEvent.Error(e.message ?: "Unknown error"))
        }
    }.flowOn(Dispatchers.IO)

    private fun normalizeEndpoint(value: String): String {
        val trimmed = value.trim().trimEnd('/')
        require(trimmed.isNotBlank()) { "API base URL is empty" }
        require(trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
            "API base URL must start with http:// or https://"
        }
        return if (trimmed.endsWith("/chat/completions")) {
            trimmed
        } else if (!trimmed.substringAfter("://", "").contains("/")) {
            "$trimmed/v1/chat/completions"
        } else {
            "$trimmed/chat/completions"
        }
    }

    private fun extractNonStreamingContent(responseText: String): String {
        return runCatching {
            val root = AppJson.parseToJsonElement(responseText) as? JsonObject ?: return@runCatching ""
            val choices = root["choices"] as? JsonArray ?: JsonArray(emptyList())
            val first = choices.firstOrNull() as? JsonObject
            val messageContent = first?.get("message")
                .let { it as? JsonObject }
                ?.get("content")
                ?.let(::extractContentText)
            val textContent = (first?.get("text") as? JsonPrimitive)?.contentOrNull
            messageContent
                ?: textContent
                ?: root["output_text"]?.let(::extractContentText)
                ?: root["reply"]?.let(::extractContentText)
                ?: ""
        }.getOrElse { error ->
            Log.e("OpenAiProvider", "Non-stream parse error", error)
            ""
        }
    }

    private fun extractContentText(value: JsonElement): String {
        return when (value) {
            is JsonPrimitive -> value.contentOrNull.orEmpty()
            is JsonArray -> value.mapNotNull { item ->
                when (item) {
                    is JsonPrimitive -> item.contentOrNull
                    is JsonObject -> item["text"]?.let(::extractContentText)
                    else -> null
                }
            }.joinToString("")
            is JsonObject -> value["value"]?.let(::extractContentText)
                ?: value["text"]?.let(::extractContentText)
                ?: ""
        }
    }
}
