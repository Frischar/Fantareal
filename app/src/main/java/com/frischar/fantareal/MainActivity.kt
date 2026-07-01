package com.frischar.fantareal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.frischar.fantareal.ui.app.AppScaffold
import com.frischar.fantareal.ui.theme.FantarealTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Enable edge-to-edge for immersive UI experience
        enableEdgeToEdge()

        setContent {
            AppScaffold()
        }
    }
}
