package com.frischar.fantareal.data.rolecard

import android.util.Base64
import java.nio.ByteBuffer
import java.nio.ByteOrder

object PngUtils {
    val PNG_SIGNATURE = byteArrayOf(
        0x89.toByte(), 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
    )

    fun extractTavernPngJson(bytes: ByteArray): String {
        require(bytes.size > PNG_SIGNATURE.size && bytes.take(PNG_SIGNATURE.size).toByteArray().contentEquals(PNG_SIGNATURE)) {
            "Not a PNG card"
        }

        var offset = PNG_SIGNATURE.size
        while (offset + 8 <= bytes.size) {
            val length = ByteBuffer.wrap(bytes, offset, 4).order(ByteOrder.BIG_ENDIAN).int
            if (length < 0) break
            val type = bytes.copyOfRange(offset + 4, offset + 8).toString(Charsets.US_ASCII)
            val dataStart = offset + 8
            val dataEnd = dataStart + length
            if (dataEnd > bytes.size) break

            val data = bytes.copyOfRange(dataStart, dataEnd)
            if (type == "tEXt" || type == "iTXt") {
                parseTextChunk(type, data)?.let { return it }
            }

            offset = dataEnd + 4
        }

        error("PNG does not contain Tavern metadata")
    }

    private fun parseTextChunk(type: String, data: ByteArray): String? {
        val separator = data.indexOf(0)
        if (separator <= 0) return null

        val keyword = data.copyOfRange(0, separator).toString(Charsets.ISO_8859_1)
        if (!keyword.equals("chara", ignoreCase = true)) return null

        val encodedBytes = if (type == "iTXt") {
            extractInternationalText(data, separator + 1) ?: return null
        } else {
            data.copyOfRange(separator + 1, data.size)
        }
        val encoded = encodedBytes.toString(Charsets.ISO_8859_1)
        return Base64.decode(encoded, Base64.DEFAULT).toString(Charsets.UTF_8)
    }

    private fun extractInternationalText(data: ByteArray, start: Int): ByteArray? {
        if (start + 2 > data.size) return null
        val compressionFlag = data[start].toInt()
        if (compressionFlag != 0) return null

        var offset = start + 2 // compression flag + compression method
        repeat(2) {
            val next = data.indexOf(0, offset)
            if (next == -1) return null
            offset = next + 1
        }
        return if (offset <= data.size) data.copyOfRange(offset, data.size) else null
    }

    private fun ByteArray.indexOf(value: Int, startIndex: Int = 0): Int {
        for (index in startIndex until size) {
            if (this[index].toInt() == value) return index
        }
        return -1
    }
}
