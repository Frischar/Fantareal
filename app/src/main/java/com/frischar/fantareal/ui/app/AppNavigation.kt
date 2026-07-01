package com.frischar.fantareal.ui.app

enum class ScreenRoute(val route: String, val title: String) {
    Chat("chat", "对话（主界面）"),
    Settings("settings", "设置与模型"),
    RoleCard("roleCard", "角色卡（主人物）"),
    Memory("memory", "记忆（动态信息）"),
    Worldbook("worldbook", "世界书（设定索引）"),
    Preset("preset", "预设（指令集）")
}
