import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property int selectedRow: -1
    property int editIndex: -1
    property string titleDraft: ""
    property string tagsDraft: ""
    property string contentDraft: ""
    property string notesDraft: ""
    property bool activeDraft: true

    function memoryAt(row) {
        if (row >= 0 && row < FantarealBridge.memoryDrafts.length) {
            return FantarealBridge.memoryDrafts[row];
        }
        return {};
    }

    function loadMemory(row) {
        const item = root.memoryAt(row);
        if (item.index === undefined) {
            root.newMemory();
            return;
        }
        root.selectedRow = row;
        root.editIndex = item.index;
        root.titleDraft = item.title === undefined ? "" : item.title;
        root.tagsDraft = item.tagsText === undefined ? "" : item.tagsText;
        root.contentDraft = item.content === undefined ? "" : item.content;
        root.notesDraft = item.notes === undefined ? "" : item.notes;
        root.activeDraft = item.active !== false;
    }

    function newMemory() {
        root.selectedRow = -1;
        root.editIndex = -1;
        root.titleDraft = "";
        root.tagsDraft = "";
        root.contentDraft = "";
        root.notesDraft = "";
        root.activeDraft = true;
    }

    function reloadSelected() {
        if (root.editIndex < 0) {
            root.newMemory();
            return;
        }
        for (let i = 0; i < FantarealBridge.memoryDrafts.length; ++i) {
            const item = FantarealBridge.memoryDrafts[i];
            if (item.index === root.editIndex) {
                root.loadMemory(i);
                return;
            }
        }
        root.newMemory();
    }

    function saveMemory() {
        const draft = {
            title: root.titleDraft,
            tagsText: root.tagsDraft,
            content: root.contentDraft,
            notes: root.notesDraft,
            active: root.activeDraft
        };
        const result = FantarealBridge.saveMemoryEntry(root.editIndex, draft);
        if (result.ok) {
            message.success(result.message);
            root.editIndex = result.entryIndex;
            Qt.callLater(root.reloadSelected);
        } else {
            message.error(result.message, 5000);
        }
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
            if (root.editIndex >= 0 && FantarealBridge.memoryDrafts.length === 0) {
                root.newMemory();
            }
        }
    }

    Component.onCompleted: {
        if (FantarealBridge.memoryDrafts.length > 0) {
            root.loadMemory(0);
        } else {
            root.newMemory();
        }
    }

    Flickable {
        id: scroller
        anchors.fill: parent
        contentWidth: width
        contentHeight: pageColumn.implicitHeight + 56
        clip: true

        ColumnLayout {
            id: pageColumn
            width: Math.min(parent.width - 56, 1320)
            x: 28
            y: 28
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                HusText {
                    Layout.fillWidth: true
                    text: "记忆"
                    font.pixelSize: 28
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusButton {
                    text: "新增记忆"
                    type: HusButton.Type_Primary
                    onClicked: root.newMemory()
                }

                HusButton {
                    text: "刷新"
                    type: HusButton.Type_Text
                    onClicked: FantarealBridge.refreshLegacyScan()
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(620, root.height - 118)
                spacing: 12

                GlassCard {
                    Layout.preferredWidth: 360
                    Layout.fillHeight: true
                    accentColor: Global.accentGreen
                    cornerRadius: 20

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 18
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.46)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(Global.accentGreen, 0.22)
                            clip: true

                            HusText {
                                anchors.centerIn: parent
                                width: parent.width - 36
                                visible: FantarealBridge.memoryDrafts.length === 0
                                text: "暂无记忆"
                                wrapMode: Text.Wrap
                                horizontalAlignment: Text.AlignHCenter
                                color: HusTheme.Primary.colorTextSecondary
                            }

                            ListView {
                                id: memoryList
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
                                clip: true
                                model: FantarealBridge.memoryDrafts
                                visible: FantarealBridge.memoryDrafts.length > 0

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: Math.max(88, memoryItemColumn.implicitHeight + 20)
                                    radius: 14
                                    color: root.selectedRow === index ? HusThemeFunctions.alpha(Global.accentGreen, HusTheme.isDark ? 0.30 : 0.18) : HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.62)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(root.selectedRow === index ? Global.accentGreen : HusTheme.Primary.colorBorder, 0.34)

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.loadMemory(index)
                                    }

                                    ColumnLayout {
                                        id: memoryItemColumn
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 6

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            HusText {
                                                Layout.fillWidth: true
                                                text: modelData.title
                                                font.pixelSize: 14
                                                font.weight: Font.DemiBold
                                                color: HusTheme.Primary.colorTextPrimary
                                                elide: Text.ElideRight
                                            }

                                            HusTag {
                                                text: modelData.active === false ? "归档" : "活跃"
                                                tagState: modelData.active === false ? HusTag.State_Default : HusTag.State_Success
                                            }
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: modelData.preview
                                            wrapMode: Text.Wrap
                                            maximumLineCount: 2
                                            elide: Text.ElideRight
                                            color: HusTheme.Primary.colorTextSecondary
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: modelData.tagsText
                                            visible: modelData.tagsText.length > 0
                                            color: HusTheme.Primary.colorTextTertiary
                                            font.pixelSize: 12
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                ScrollBar.vertical: HusScrollBar {}
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    accentColor: Global.accentBlue
                    cornerRadius: 22

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            HusText {
                                Layout.fillWidth: true
                                text: root.editIndex < 0 ? "新增长期记忆" : `编辑记忆 #${root.editIndex + 1}`
                                font.pixelSize: 24
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusSwitch {
                                checked: root.activeDraft
                                checkedText: "活跃"
                                uncheckedText: "归档"
                                onCheckedChanged: root.activeDraft = checked
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            HusInput {
                                id: titleInput
                                Layout.fillWidth: true
                                placeholderText: "标题"
                                clearEnabled: "active"
                                text: root.titleDraft
                                onTextChanged: root.titleDraft = text
                            }

                            HusInput {
                                id: tagsInput
                                Layout.preferredWidth: 320
                                placeholderText: "标签，用逗号分隔"
                                clearEnabled: "active"
                                text: root.tagsDraft
                                onTextChanged: root.tagsDraft = text
                            }
                        }

                        HusTextArea {
                            id: contentInput
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 300
                            placeholderText: "记忆内容"
                            maxLength: 12000
                            text: root.contentDraft
                            onTextChanged: root.contentDraft = text
                        }

                        HusTextArea {
                            id: notesInput
                            Layout.fillWidth: true
                            Layout.preferredHeight: 118
                            placeholderText: "备注"
                            maxLength: 2400
                            text: root.notesDraft
                            onTextChanged: root.notesDraft = text
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Item {
                                Layout.fillWidth: true
                            }

                            HusButton {
                                text: "还原"
                                type: HusButton.Type_Outlined
                                onClicked: root.reloadSelected()
                            }

                            HusButton {
                                text: "保存记忆"
                                type: HusButton.Type_Primary
                                enabled: root.contentDraft.trim().length > 0
                                onClicked: root.saveMemory()
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
        childTargets: [memoryList, contentInput, notesInput]
    }

}
