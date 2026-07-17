package com.frischar.fantareal

import androidx.compose.ui.graphics.Color
import com.frischar.fantareal.ui.chat.defaultChatTextColor
import org.junit.Assert.assertEquals
import org.junit.Test

class ChatTextColorTest {
    @Test
    fun defaultChatTextColorFollowsThemeContrast() {
        assertEquals(Color.White, defaultChatTextColor(darkMode = true))
        assertEquals(Color.Black, defaultChatTextColor(darkMode = false))
    }
}
