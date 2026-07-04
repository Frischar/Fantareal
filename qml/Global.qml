pragma Singleton

import QtQuick
import HuskarUI.Basic

QtObject {
    readonly property color accentBlue: "#1677ff"
    readonly property color accentViolet: "#8b5cf6"
    readonly property color accentPink: "#f6a6d8"
    readonly property color accentGreen: "#52c41a"
    readonly property color accentGold: "#faad14"
    readonly property color accentCyan: "#00bcd4"
    readonly property color accentRed: "#f74658"
    readonly property color cardDark: "#26345fcc"
    readonly property color cardLight: "#d7e5ffcc"
    readonly property var navItems: [
        { key: "home", label: "首页", shortLabel: "首页", iconSource: HusIcon.HomeOutlined, state: "online" },
        { key: "chat", label: "聊天", shortLabel: "聊天", iconSource: HusIcon.MessageOutlined, state: "online" },
        { key: "cards", label: "角色卡", shortLabel: "角色", iconSource: HusIcon.IdcardOutlined, state: "online" },
        { key: "preset", label: "预设", shortLabel: "预设", iconSource: HusIcon.ProjectOutlined, state: "online" },
        { key: "memory", label: "记忆", shortLabel: "记忆", iconSource: HusIcon.DatabaseOutlined, state: "pending" },
        { key: "worldbook", label: "世界书", shortLabel: "世界", iconSource: HusIcon.BookOutlined, state: "online" },
        { key: "routes", label: "模型路由", shortLabel: "路由", iconSource: HusIcon.ApiOutlined, state: "warning" },
        { key: "workshop", label: "演出工坊", shortLabel: "工坊", iconSource: HusIcon.ThunderboltOutlined, state: "pending" },
        { key: "plugins", label: "插件状态", shortLabel: "插件", iconSource: HusIcon.AppstoreOutlined, state: "pending" },
        { key: "settings", label: "设置", shortLabel: "设置", iconSource: HusIcon.SettingOutlined, state: "online" }
    ]
    readonly property var navMenuModel: [
        navItems[1],
        navItems[2],
        navItems[3],
        navItems[4],
        navItems[5],
        navItems[8],
        navItems[9]
    ]
    readonly property var moduleCards: [
        { key: "cards", title: "角色卡", desc: "读取 cards、当前角色卡与 Tavern 卡模板状态。", color: accentBlue, tag: "P0", iconSource: HusIcon.IdcardOutlined },
        { key: "preset", title: "预设", desc: "保留 active preset、提示词规则与事件预设素材。", color: accentRed, tag: "P0", iconSource: HusIcon.ProjectOutlined },
        { key: "memory", title: "记忆", desc: "角色记忆、摘要与检索状态。", color: accentGreen, tag: "P1", iconSource: HusIcon.DatabaseOutlined },
        { key: "worldbook", title: "世界书", desc: "读取 worldbook 与 runtime state，预留关键词触发预览。", color: accentGold, tag: "P0", iconSource: HusIcon.BookOutlined },
        { key: "workshop", title: "演出工坊", desc: "演出素材、事件预设与导演注记。", color: accentViolet, tag: "P1", iconSource: HusIcon.ThunderboltOutlined },
        { key: "plugins", title: "插件状态", desc: "mods、mobile-chat、auto-saga 与状态日志兼容检查。", color: accentCyan, tag: "P1", iconSource: HusIcon.AppstoreOutlined }
    ]
}
