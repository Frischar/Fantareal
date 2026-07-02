package com.frischar.fantareal.data.storage

import com.frischar.fantareal.core.AppJson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.KSerializer
import java.io.File
import java.io.FileOutputStream
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption

class JsonStore {
    private val mutex = Mutex()

    suspend fun <T> read(file: File, serializer: KSerializer<T>, defaultValue: T): T {
        return withContext(Dispatchers.IO) {
            if (!file.exists()) return@withContext defaultValue

            runCatching {
                AppJson.decodeFromString(serializer, file.readText(Charsets.UTF_8))
            }.getOrElse {
                defaultValue
            }
        }
    }

    suspend fun <T> write(file: File, serializer: KSerializer<T>, value: T) {
        val encoded = AppJson.encodeToString(serializer, value)

        withContext(Dispatchers.IO) {
            mutex.withLock {
                file.parentFile?.mkdirs()
                val tempFile = File(file.parentFile, "${file.name}.tmp")
                FileOutputStream(tempFile).use { output ->
                    output.write(encoded.toByteArray(Charsets.UTF_8))
                    output.fd.sync()
                }

                try {
                    Files.move(
                        tempFile.toPath(),
                        file.toPath(),
                        StandardCopyOption.REPLACE_EXISTING,
                        StandardCopyOption.ATOMIC_MOVE
                    )
                } catch (_: AtomicMoveNotSupportedException) {
                    Files.move(
                        tempFile.toPath(),
                        file.toPath(),
                        StandardCopyOption.REPLACE_EXISTING
                    )
                }
            }
        }
    }
}
