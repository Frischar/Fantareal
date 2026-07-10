import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    signal openPage(string page)

    property var status: FantarealBridge.databaseStatus

    function refreshStatus() {
        const result = FantarealBridge.refreshDatabaseStatus();
        status = result;
        if (result.ok) {
            message.success("数据库状态已刷新");
        } else {
            message.error(result.message || "数据库状态刷新失败", 5000);
        }
    }

    function tableState(rowCount) {
        return Number(rowCount || 0) > 0 ? HusTag.State_Processing : HusTag.State_Default;
    }

    HusMessage {
        id: message
        z: 999
        width: root.width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }

    Connections {
        target: FantarealBridge

        function onScanChanged() {
            root.status = FantarealBridge.databaseStatus;
        }
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: pageColumn.implicitHeight + 72
        clip: true

        ColumnLayout {
            id: pageColumn
            width: Math.min(parent.width - 72, 1180)
            x: 36
            y: 36
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                HusText {
                    Layout.fillWidth: true
                    text: "数据库"
                    font.pixelSize: 32
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    text: root.status.ok ? "就绪" : "异常"
                    tagState: root.status.ok ? HusTag.State_Success : HusTag.State_Error
                }

                HusButton {
                    text: "刷新"
                    onClicked: root.refreshStatus()
                }

                HusButton {
                    text: "写卡器"
                    type: HusButton.Type_Filled
                    onClicked: root.openPage("cardAuthoring")
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: overviewContent.implicitHeight + 56
                accentColor: Global.accentGreen

                ColumnLayout {
                    id: overviewContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 16

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        StatPill {
                            text: "数据库运行状态"
                            accentColor: Global.accentGreen
                        }
                        HusTag {
                            text: root.status.relativePath || "data/database/database.db"
                            presetColor: "green"
                        }
                        HusTag {
                            text: `架构 v${Number(root.status.schemaVersion || 0)}`
                            tagState: HusTag.State_Processing
                        }
                    }

                    SummaryRows {
                        Layout.fillWidth: true
                        rows: FantarealBridge.databaseRows
                        labelWidth: 150
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(360, tableColumn.implicitHeight + 56)
                spacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    accentColor: Global.accentCyan

                    ColumnLayout {
                        id: tableColumn
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        HusText {
                            Layout.fillWidth: true
                            text: "核心表"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        Repeater {
                            model: root.status.tables || []

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: Math.max(64, tableRow.implicitHeight + 18)
                                radius: 8
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.48)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                                RowLayout {
                                    id: tableRow
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Rectangle {
                                        Layout.preferredWidth: 34
                                        Layout.preferredHeight: 34
                                        radius: 8
                                        color: HusThemeFunctions.alpha(Global.accentCyan, HusTheme.isDark ? 0.28 : 0.16)

                                        HusIconText {
                                            anchors.centerIn: parent
                                            iconSource: HusIcon.DatabaseOutlined
                                            iconSize: 18
                                            colorIcon: Global.accentCyan
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        HusText {
                                            Layout.fillWidth: true
                                            text: modelData.label || modelData.name
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: modelData.name
                                            font.pixelSize: 12
                                            color: HusTheme.Primary.colorTextSecondary
                                            elide: Text.ElideRight
                                        }
                                    }

                                    HusTag {
                                        text: `${Number(modelData.rowCount || 0)} 行`
                                        tagState: root.tableState(modelData.rowCount)
                                    }
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.preferredWidth: 360
                    Layout.fillHeight: true
                    accentColor: Global.accentGold

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 12

                        HusText {
                            Layout.fillWidth: true
                            text: "运行分区"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        SummaryRows {
                            Layout.fillWidth: true
                            labelWidth: 112
                            rows: [`状态快照：${Number((root.status.tableCounts || {}).database_state_snapshots || 0)}`, `阶段状态：${Number((root.status.tableCounts || {}).database_stage_state || 0)}`, `剧情账本：${Number((root.status.tableCounts || {}).database_plot_ledger || 0)}`, `文件大小：${root.status.fileSizeText || "0 B"}`]
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.42)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.26)

                            HusText {
                                anchors.fill: parent
                                anchors.margins: 16
                                text: root.status.databasePath || ""
                                color: HusTheme.Primary.colorTextSecondary
                                wrapMode: Text.WrapAnywhere
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: HusScrollBar {}
    }

    SmoothWheelArea {
        anchors.fill: scroller
        target: scroller
    }
}
