import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: pageColumn.implicitHeight + 88
        clip: true

        ColumnLayout {
            id: pageColumn
            width: Math.min(parent.width - 88, 1120)
            x: 44
            y: 44
            spacing: 20

            HusText {
                text: "插件状态"
                font.pixelSize: 34
                font.weight: Font.DemiBold
                color: HusTheme.Primary.colorTextPrimary
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 300
                accentColor: Global.accentCyan

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 14

                    RowLayout {
                        StatPill { text: "COMPAT"; accentColor: Global.accentCyan }
                        HusTag { text: "mods/*/mod.json"; presetColor: "cyan" }
                        HusTag { text: "mobile-chat / auto-saga / state-journal"; presetColor: "blue" }
                    }

                    HusText {
                        text: "旧插件运行态保全"
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        spacing: 10
                        HusTag { text: `${FantarealBridge.pluginManifestCount} 插件清单`; tagState: HusTag.State_Processing }
                        HusTag { text: `${FantarealBridge.cardFileCount} 卡片/角色文件`; tagState: HusTag.State_Default }
                    }

                    HusButton {
                        text: "刷新扫描"
                        type: HusButton.Type_Primary
                        onClicked: FantarealBridge.refreshLegacyScan()
                    }
                }
            }
        }

        ScrollBar.vertical: HusScrollBar { }
    }

    SmoothWheelArea {
        anchors.fill: scroller
        target: scroller
    }

}
