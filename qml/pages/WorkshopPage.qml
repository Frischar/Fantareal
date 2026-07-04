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
                text: "演出工坊"
                font.pixelSize: 34
                font.weight: Font.DemiBold
                color: HusTheme.Primary.colorTextPrimary
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 278
                accentColor: Global.accentViolet

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 14

                    RowLayout {
                        StatPill { text: "STAGE TOOLS"; accentColor: Global.accentViolet }
                        HusTag { text: "creative_workshop_state.json"; presetColor: "purple" }
                    }

                    HusText {
                        text: "演出素材"
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }

                    RowLayout {
                        spacing: 10
                        HusTag { text: `${FantarealBridge.assetFileCount} 素材文件`; tagState: HusTag.State_Processing }
                        HusTag { text: `${FantarealBridge.assetDirFoundCount}/${FantarealBridge.assetDirCount} 目录`; tagState: HusTag.State_Success }
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
