package com.frischar.fantareal

import androidx.compose.ui.graphics.Color
import com.frischar.fantareal.ui.theme.darkAppColorScheme
import com.frischar.fantareal.ui.theme.lightAppColorScheme
import org.junit.Assert.assertEquals
import org.junit.Test

class ThemeTextColorTest {
    @Test
    fun nonChatThemeUsesWhiteTextInDarkMode() {
        val scheme = darkAppColorScheme()

        assertEquals(Color.White, scheme.onPrimary)
        assertEquals(Color.White, scheme.onSecondary)
        assertEquals(Color.White, scheme.onTertiary)
        assertEquals(Color.White, scheme.onBackground)
        assertEquals(Color.White, scheme.onSurface)
        assertEquals(Color.White, scheme.onSurfaceVariant)
    }

    @Test
    fun nonChatThemeUsesBlackTextInLightMode() {
        val scheme = lightAppColorScheme()

        assertEquals(Color.Black, scheme.onPrimary)
        assertEquals(Color.Black, scheme.onSecondary)
        assertEquals(Color.Black, scheme.onTertiary)
        assertEquals(Color.Black, scheme.onBackground)
        assertEquals(Color.Black, scheme.onSurface)
        assertEquals(Color.Black, scheme.onSurfaceVariant)
    }
}
