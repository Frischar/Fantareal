package com.frischar.fantareal.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = NightHighlight,
    secondary = NightEmotional,
    tertiary = NightFantasy,
    background = NightBackground,
    surface = NightMainPanel,
    surfaceVariant = NightSecondaryPanel,
    error = NightError,
    onPrimary = NightTextMain,
    onSecondary = NightTextMain,
    onTertiary = NightTextMain,
    onBackground = NightTextMain,
    onSurface = NightTextMain,
    onSurfaceVariant = NightTextSecondary,
    outline = NightStroke
)

private val LightColorScheme = lightColorScheme(
    primary = DayHighlight,
    secondary = DayEmotional,
    tertiary = DayFantasy,
    background = DayBackground,
    surface = DayMainPanel,
    surfaceVariant = DaySecondaryPanel,
    error = DayError,
    onPrimary = DayBackground,
    onSecondary = DayBackground,
    onTertiary = DayBackground,
    onBackground = DayTextMain,
    onSurface = DayTextMain,
    onSurfaceVariant = DayTextSecondary,
    outline = DayStroke
)

@Composable
fun FantarealTheme(
    darkTheme: Boolean = false, // Default to light mode (浅蓝色主题)
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        content = content
    )
}
