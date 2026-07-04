import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    signal openPage(string page)

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight + 84
        clip: true

        ColumnLayout {
            id: contentColumn
            width: Math.max(0, Math.min(scroller.width - 64, 1264))
            x: Math.max(32, (scroller.width - width) / 2)
            y: 42
            spacing: 28

            RowLayout {
                Layout.fillWidth: true
                spacing: 28

                HusAvatar {
                    Layout.preferredWidth: 70
                    Layout.preferredHeight: 70
                    size: 70
                    textSource: "F"
                    colorBg: HusTheme.isDark ? "#233142" : "#21364d"
                    colorText: "white"
                    textFont.pixelSize: 34
                    radiusBg.all: 12
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    HusText {
                        Layout.fillWidth: true
                        text: "Fantareal"
                        font.pixelSize: 58
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                        style: Text.Raised
                        styleColor: HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.58 : 0.28)
                    }

                }

                HusSegmented {
                    Layout.alignment: Qt.AlignTop
                    options: [
                        { label: "总览", value: "overview", iconSource: HusIcon.HomeOutlined },
                        { label: "数据", value: "data", iconSource: HusIcon.DatabaseOutlined },
                        { label: "数据", value: "data", iconSource: HusIcon.ProjectOutlined }
                    ]
                    currentIndex: 0
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 28

                GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 278
                    accentColor: Global.accentBlue

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 32
                        spacing: 18

                        RowLayout {
                            Layout.fillWidth: true
                            StatPill { text: "CHAT CORE"; accentColor: Global.accentBlue }
                            Item { Layout.fillWidth: true }
                            HusIconText {
                                iconSource: HusIcon.MessageOutlined
                                iconSize: 24
                                colorIcon: HusThemeFunctions.alpha("#ffffff", 0.86)
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: "继续创作工作流"
                            font.pixelSize: 28
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: "聊天页先承载消息列表、当前角色、Persona、活动预设和生成状态。旧 WebUI 不再作为新 UI 的隐藏依赖。"
                            wrapMode: Text.Wrap
                            color: HusTheme.Primary.colorTextSecondary
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            spacing: 12
                            HusButton {
                                text: "进入聊天"
                                type: HusButton.Type_Primary
                                onClicked: root.openPage("chat")
                            }
                            HusButton {
                                text: "角色卡"
                                type: HusButton.Type_Outlined
                                onClicked: root.openPage("cards")
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 278
                    accentColor: Global.accentViolet

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 32
                        spacing: 18

                        RowLayout {
                            Layout.fillWidth: true
                            StatPill { text: "LEGACY SCAN"; accentColor: Global.accentViolet }
                            Item { Layout.fillWidth: true }
                            HusIconText {
                                iconSource: HusIcon.DatabaseOutlined
                                iconSize: 24
                                colorIcon: HusThemeFunctions.alpha("#ffffff", 0.86)
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: "数据概览"
                            font.pixelSize: 28
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: FantarealBridge.scanSummary
                            wrapMode: Text.Wrap
                            color: HusTheme.Primary.colorTextSecondary
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            HusTag {
                                text: `${FantarealBridge.criticalFileFoundCount}/${FantarealBridge.criticalFileCount} 文件`
                                tagState: HusTag.State_Processing
                            }
                            HusTag {
                                text: `${FantarealBridge.assetDirFoundCount}/${FantarealBridge.assetDirCount} 目录`
                                tagState: HusTag.State_Success
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            HusProgress {
                                Layout.fillWidth: true
                                percent: FantarealBridge.criticalFilePercent
                                barThickness: 6
                                status: percent >= 100 ? HusProgress.Status_Success : HusProgress.Status_Active
                                formatter: () => `文件 ${Math.round(percent)}%`
                            }

                            HusProgress {
                                Layout.fillWidth: true
                                percent: FantarealBridge.assetDirPercent
                                barThickness: 6
                                status: percent >= 100 ? HusProgress.Status_Success : HusProgress.Status_Normal
                                formatter: () => `目录 ${Math.round(percent)}%`
                            }
                        }

                        Item { Layout.fillHeight: true }

                        RowLayout {
                            spacing: 12
                            HusButton {
                                text: "刷新扫描"
                                type: HusButton.Type_Primary
                                onClicked: FantarealBridge.refreshLegacyScan()
                            }
                            HusButton {
                                text: "模型路由"
                                type: HusButton.Type_Outlined
                                onClicked: root.openPage("routes")
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    HusText {
                        text: "重构模块"
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }
                }

                HusIconButton {
                    text: "打开设置"
                    type: HusButton.Type_Filled
                    iconSource: HusIcon.SettingOutlined
                    onClicked: root.openPage("settings")
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: scroller.width >= 1180 ? 3 : 2
                columnSpacing: 22
                rowSpacing: 22

                Repeater {
                    model: Global.moduleCards
                    delegate: GlassCard {
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.preferredHeight: 196
                        accentColor: modelData.color

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 24
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                StatPill { text: modelData.tag; accentColor: modelData.color }
                                Item { Layout.fillWidth: true }
                                HusIconText {
                                    iconSource: modelData.iconSource
                                    iconSize: 22
                                    colorIcon: modelData.color
                                }
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: modelData.title
                                font.pixelSize: 21
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: modelData.desc
                                wrapMode: Text.Wrap
                                color: HusTheme.Primary.colorTextSecondary
                            }

                            Item { Layout.fillHeight: true }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 5
                                radius: 3
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorTextBase, 0.10)

                                Rectangle {
                                    width: parent.width * 0.38
                                    height: parent.height
                                    radius: parent.radius
                                    color: modelData.color
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.openPage(modelData.key)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 22

                GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    accentColor: Global.accentGreen

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 12

                        HusText {
                            text: "已发现"
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                        }

                        ListView {
                            id: foundLegacyList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            visible: count > 0
                            model: FantarealBridge.foundLegacyItems
                            delegate: HusText {
                                required property string modelData
                                width: ListView.view.width
                                text: `• ${modelData}`
                                color: HusTheme.Primary.colorTextSecondary
                                elide: Text.ElideMiddle
                            }
                            ScrollBar.vertical: HusScrollBar { }
                        }

                        HusEmpty {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: FantarealBridge.foundLegacyItems.length === 0
                            imageStyle: HusEmpty.Style_Simple
                            description: "暂无已发现项目"
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 250
                    accentColor: Global.accentGold

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 22
                        spacing: 12

                        HusText {
                            text: "待补齐"
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                        }

                        ListView {
                            id: missingLegacyList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            visible: count > 0
                            model: FantarealBridge.missingLegacyItems
                            delegate: HusText {
                                required property string modelData
                                width: ListView.view.width
                                text: `• ${modelData}`
                                color: HusTheme.Primary.colorTextSecondary
                                elide: Text.ElideMiddle
                            }
                            ScrollBar.vertical: HusScrollBar { }
                        }

                        HusEmpty {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: FantarealBridge.missingLegacyItems.length === 0
                            imageStyle: HusEmpty.Style_Simple
                            description: "关键数据已就绪"
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: HusScrollBar { }
    }

    SmoothWheelArea {
        anchors.fill: scroller
        target: scroller
        childTargets: [foundLegacyList, missingLegacyList]
    }

}
