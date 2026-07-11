import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    signal openPage(string page)

    readonly property var status: FantarealBridge.databaseStatus
    property string selectedTable: ""
    property var tableView: ({})
    property int pageSize: 25

    function loadTable(tableName, offset) {
        if (!tableName) {
            return;
        }
        selectedTable = tableName;
        tableView = FantarealBridge.loadDatabaseDebugTable(tableName, Math.max(0, offset || 0), pageSize);
        if (!tableView.ok) {
            message.error(tableView.message || "物理表读取失败", 5000);
        }
    }

    function refreshAll() {
        FantarealBridge.refreshDatabaseStatus();
        const tableName = selectedTable || (((root.status.tables || [])[0] || {}).name || "");
        if (tableName) {
            loadTable(tableName, 0);
        }
    }

    function valueText(value) {
        if (value === undefined || value === null) {
            return "null";
        }
        if (typeof value === "object") {
            return JSON.stringify(value, null, 2);
        }
        return String(value);
    }

    Component.onCompleted: refreshAll()

    HusMessage {
        id: message
        z: 999
        width: root.width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            HusIconButton {
                iconSource: HusIcon.ArrowLeftOutlined
                type: HusButton.Type_Outlined
                contentDescription: "返回数据库"
                onClicked: root.openPage("database")
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                HusText {
                    text: "数据库排错"
                    font.pixelSize: 28
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusText {
                    Layout.fillWidth: true
                    text: "用于查看 SQLite 路径、Schema、物理表与原始行。这里只读，不执行任意 SQL。"
                    wrapMode: Text.Wrap
                    font.pixelSize: 13
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            HusButton {
                text: "刷新"
                type: HusButton.Type_Outlined
                onClicked: root.refreshAll()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: statusRow.implicitHeight + 22
            radius: 8
            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.28 : 0.66)
            border.width: 1
            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.32)

            RowLayout {
                id: statusRow
                anchors.fill: parent
                anchors.margins: 11
                spacing: 10

                HusTag {
                    text: root.status.ok ? "数据库就绪" : "数据库异常"
                    tagState: root.status.ok ? HusTag.State_Success : HusTag.State_Error
                }

                HusTag {
                    text: `Schema v${Number(root.status.schemaVersion || 0)}`
                    tagState: HusTag.State_Processing
                }

                HusText {
                    Layout.fillWidth: true
                    text: root.status.databasePath || ""
                    elide: Text.ElideMiddle
                    color: HusTheme.Primary.colorTextSecondary
                    font.pixelSize: 12
                }

                HusText {
                    text: root.status.fileSizeText || "0 B"
                    color: HusTheme.Primary.colorTextTertiary
                    font.pixelSize: 12
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            Rectangle {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                radius: 8
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.22 : 0.58)
                border.width: 1
                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 9

                    HusText {
                        text: "物理表"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    ListView {
                        id: tableList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 6
                        clip: true
                        model: root.status.tables || []

                        delegate: Rectangle {
                            width: tableList.width
                            implicitHeight: tableItem.implicitHeight + 18
                            radius: 7
                            color: root.selectedTable === modelData.name
                                ? HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.24 : 0.14)
                                : HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                            border.width: 1
                            border.color: root.selectedTable === modelData.name
                                ? HusThemeFunctions.alpha(Global.accentBlue, 0.44)
                                : HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)

                            RowLayout {
                                id: tableItem
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 8

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.label || modelData.name
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.name
                                        font.pixelSize: 11
                                        color: HusTheme.Primary.colorTextTertiary
                                        elide: Text.ElideRight
                                    }
                                }

                                HusTag {
                                    text: `${Number(modelData.rowCount || 0)} 行`
                                    tagState: Number(modelData.rowCount || 0) > 0
                                        ? HusTag.State_Processing : HusTag.State_Default
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.loadTable(modelData.name, 0)
                            }
                        }

                        ScrollBar.vertical: HusScrollBar {}
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.22 : 0.58)
                border.width: 1
                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 1

                            HusText {
                                text: root.tableView.label || "选择物理表"
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                text: root.tableView.tableName || ""
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextTertiary
                            }
                        }

                        HusTag {
                            visible: Boolean(root.tableView.tableName)
                            text: `${Number(root.tableView.totalRows || 0)} 行`
                            tagState: HusTag.State_Processing
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 52
                        visible: Boolean(root.tableView.tableName)
                            && (root.tableView.rows || []).length === 0
                        radius: 7
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.40)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.22)

                        HusText {
                            anchors.centerIn: parent
                            text: root.tableView.ok ? "当前角色在这张表中没有数据" : (root.tableView.message || "读取失败")
                            color: HusTheme.Primary.colorTextSecondary
                            font.pixelSize: 13
                        }
                    }

                    ListView {
                        id: rowList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        clip: true
                        model: root.tableView.rows || []

                        delegate: Rectangle {
                            id: rowCard
                            width: rowList.width
                            implicitHeight: rowContent.implicitHeight + 20
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.26)
                            property bool expanded: false

                            ColumnLayout {
                                id: rowContent
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 7

                                Item {
                                    Layout.fillWidth: true
                                    implicitHeight: rowHeader.implicitHeight

                                    RowLayout {
                                        id: rowHeader
                                        anchors.fill: parent

                                        HusText {
                                            Layout.fillWidth: true
                                            text: `第 ${Number(root.tableView.offset || 0) + index + 1} 行`
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                        }

                                        HusText {
                                            text: rowCard.expanded ? "收起" : "展开"
                                            font.pixelSize: 12
                                            color: Global.accentBlue
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: rowCard.expanded = !rowCard.expanded
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: JSON.stringify(modelData)
                                    visible: !rowCard.expanded
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                    wrapMode: Text.WrapAnywhere
                                    font.pixelSize: 12
                                    color: HusTheme.Primary.colorTextSecondary
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: rowCard.expanded
                                    spacing: 6

                                    Repeater {
                                        model: root.tableView.columns || []

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: cellContent.implicitHeight + 16
                                            radius: 6
                                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.36)

                                            ColumnLayout {
                                                id: cellContent
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                spacing: 3

                                                HusText {
                                                    text: modelData
                                                    font.pixelSize: 11
                                                    font.weight: Font.DemiBold
                                                    color: Global.accentCyan
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: root.valueText(rowCard.rowValue(modelData))
                                                    wrapMode: Text.WrapAnywhere
                                                    textFormat: Text.PlainText
                                                    font.family: "Consolas"
                                                    font.pixelSize: 12
                                                    color: HusTheme.Primary.colorTextSecondary
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            function rowValue(columnName) {
                                return modelData[columnName];
                            }
                        }

                        ScrollBar.vertical: HusScrollBar {}
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: Boolean(root.tableView.tableName)
                        spacing: 8

                        HusButton {
                            text: "上一页"
                            type: HusButton.Type_Outlined
                            enabled: Number(root.tableView.offset || 0) > 0
                            onClicked: root.loadTable(root.selectedTable,
                                Math.max(0, Number(root.tableView.offset || 0) - root.pageSize))
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: {
                                const total = Number(root.tableView.totalRows || 0);
                                const offset = Number(root.tableView.offset || 0);
                                if (total === 0) {
                                    return "0 / 0";
                                }
                                return `${offset + 1}-${Math.min(total, offset + root.pageSize)} / ${total}`;
                            }
                            horizontalAlignment: Text.AlignHCenter
                            color: HusTheme.Primary.colorTextSecondary
                            font.pixelSize: 12
                        }

                        HusButton {
                            text: "下一页"
                            type: HusButton.Type_Outlined
                            enabled: Number(root.tableView.offset || 0) + root.pageSize
                                < Number(root.tableView.totalRows || 0)
                            onClicked: root.loadTable(root.selectedTable,
                                Number(root.tableView.offset || 0) + root.pageSize)
                        }
                    }
                }
            }
        }
    }
}
