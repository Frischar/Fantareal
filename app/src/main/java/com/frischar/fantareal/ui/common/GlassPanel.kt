package com.frischar.fantareal.ui.common

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun GlassPanel(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(24.dp),
    color: Color = Color.Unspecified,
    borderWidth: Dp = 1.dp,
    borderColor: Color = Color.Unspecified,
    content: @Composable () -> Unit
) {
    val actualColor = if (color == Color.Unspecified) MaterialTheme.colorScheme.surface.copy(alpha = 0.6f) else color
    val actualBorder = if (borderColor == Color.Unspecified) MaterialTheme.colorScheme.outline.copy(alpha = 0.2f) else borderColor
    Surface(
        modifier = modifier,
        shape = shape,
        color = actualColor,
        contentColor = MaterialTheme.colorScheme.onSurface,
        border = BorderStroke(borderWidth, actualBorder),
        content = content
    )
}
