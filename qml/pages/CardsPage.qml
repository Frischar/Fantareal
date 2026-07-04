import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property bool initialized: false
    property bool dirty: false
    property string sourceName: ""
    property string cardUid: ""
    property string cardName: ""
    property string tagsText: ""
    property string descriptionText: ""
    property string personalityText: ""
    property string scenarioText: ""
    property string firstMessageText: ""
    property string messageExampleText: ""
    property string creatorNotesText: ""
    property string creatorCommentText: ""
    property bool stateJournalEnabled: true
    property bool creativeWorkshopEnabled: true
    property bool openingEnabled: false
    property int personaCount: 0
    property int dynamicSceneCount: 0

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function updateTextField(key, value) {
        if (root[key] !== value) {
            root[key] = value;
            root.markDirty();
        }
    }

    function applyDraft(draft) {
        initialized = false;
        sourceName = draft.source_name || "";
        cardUid = draft.card_uid || "";
        cardName = draft.name || "";
        tagsText = draft.tagsText || "";
        descriptionText = draft.description || "";
        personalityText = draft.personality || "";
        scenarioText = draft.scenario || "";
        firstMessageText = draft.first_mes || "";
        messageExampleText = draft.mes_example || "";
        creatorNotesText = draft.creator_notes || "";
        creatorCommentText = draft.creator_comment || "";
        stateJournalEnabled = draft.stateJournalEnabled === undefined ? true : Boolean(draft.stateJournalEnabled);
        creativeWorkshopEnabled = draft.creativeWorkshopEnabled === undefined ? true : Boolean(draft.creativeWorkshopEnabled);
        openingEnabled = Boolean(draft.openingEnabled);
        personaCount = Number(draft.personaCount || 0);
        dynamicSceneCount = Number(draft.dynamicSceneCount || 0);
        dirty = false;
        initialized = true;
    }

    function saveDraft() {
        const result = FantarealBridge.saveCardDraft({
            "name": cardName,
            "tagsText": tagsText,
            "description": descriptionText,
            "personality": personalityText,
            "scenario": scenarioText,
            "first_mes": firstMessageText,
            "mes_example": messageExampleText,
            "creator_notes": creatorNotesText,
            "creator_comment": creatorCommentText,
            "stateJournalEnabled": stateJournalEnabled,
            "creativeWorkshopEnabled": creativeWorkshopEnabled,
            "openingEnabled": openingEnabled
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function syncPersona() {
        if (root.dirty) {
            message.warning("请先保存角色卡，再同步人设。", 5000);
            return;
        }
        const result = FantarealBridge.syncCurrentCardToPersona();
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function importRoleCard(path) {
        if (root.dirty) {
            message.warning("请先保存或还原当前编辑内容，再导入角色卡。", 5000);
            return;
        }
        const result = FantarealBridge.importRoleCardFile(path);
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.cardDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    Component.onCompleted: applyDraft(FantarealBridge.cardDraft)

    FileDialog {
        id: roleCardImportDialog
        title: "导入角色卡 JSON"
        nameFilters: ["JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.importRoleCard(selectedFile.toString())
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.cardDraft);
            }
        }
    }

    HusMessage {
        id: message
        z: 999
        width: root.width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }

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

            RowLayout {
                width: parent.width
                spacing: 12

                HusText {
                    Layout.fillWidth: true
                    text: "角色卡"
                    font.pixelSize: 28
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    visible: root.dirty
                    text: "未保存"
                    tagState: HusTag.State_Warning
                }

                HusButton {
                    text: "刷新"
                    onClicked: FantarealBridge.refreshLegacyScan()
                }

                HusButton {
                    text: "导入"
                    type: HusButton.Type_Filled
                    enabled: !root.dirty
                    onClicked: roleCardImportDialog.open()
                }

                HusButton {
                    text: "还原"
                    enabled: root.dirty
                    onClicked: root.applyDraft(FantarealBridge.cardDraft)
                }

                HusButton {
                    text: "同步人设"
                    type: HusButton.Type_Filled
                    enabled: !root.dirty
                    onClicked: root.syncPersona()
                }

                HusButton {
                    text: "保存"
                    type: HusButton.Type_Primary
                    enabled: root.dirty
                    onClicked: root.saveDraft()
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: editorContent.implicitHeight + 44
                accentColor: Global.accentViolet

                ColumnLayout {
                    id: editorContent
                    anchors.fill: parent
                    anchors.margins: 22
                    spacing: 18

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "基础信息"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "角色名"

                            HusInput {
                                width: parent.width
                                text: root.cardName
                                placeholderText: "例如：艾莲"
                                clearEnabled: "active"
                                iconSource: HusIcon.UserOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.cardName = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "标签"

                            HusInput {
                                width: parent.width
                                text: root.tagsText
                                placeholderText: "幻想, 女主角, 长篇"
                                clearEnabled: "active"
                                iconSource: HusIcon.TagsOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.tagsText = text;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 3
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "状态日志"

                            HusSwitch {
                                checked: root.stateJournalEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.stateJournalEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "演出工坊"

                            HusSwitch {
                                checked: root.creativeWorkshopEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.creativeWorkshopEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "开场演出"

                            HusSwitch {
                                checked: root.openingEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.openingEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorSplit, 0.42)
                    }

                    HusText {
                        Layout.fillWidth: true
                        text: "角色文本"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "Description"

                        HusTextArea {
                            id: descriptionInput
                            width: parent.width
                            minRows: 4
                            maxRows: 8
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.descriptionText
                            placeholderText: "角色定义与外观背景"
                            onTextChanged: root.updateTextField("descriptionText", text)
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "Personality"

                        HusTextArea {
                            id: personalityInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.personalityText
                            placeholderText: "性格、语气、行为偏好"
                            onTextChanged: root.updateTextField("personalityText", text)
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "Scenario"

                        HusTextArea {
                            id: scenarioInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.scenarioText
                            placeholderText: "世界观、当前场景和互动前提"
                            onTextChanged: root.updateTextField("scenarioText", text)
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "First Message"

                        HusTextArea {
                            id: firstMessageInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.firstMessageText
                            placeholderText: "角色第一条开场消息"
                            onTextChanged: root.updateTextField("firstMessageText", text)
                        }
                    }

                    SettingField {
                        Layout.fillWidth: true
                        title: "Message Example"

                        HusTextArea {
                            id: messageExampleInput
                            width: parent.width
                            minRows: 3
                            maxRows: 7
                            maxLength: 12000
                            autoSize: true
                            resizable: true
                            text: root.messageExampleText
                            placeholderText: "示例对话"
                            onTextChanged: root.updateTextField("messageExampleText", text)
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "Creator Notes"

                            HusTextArea {
                                id: creatorNotesInput
                                width: parent.width
                                minRows: 3
                                maxRows: 6
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.creatorNotesText
                                placeholderText: "作者备注"
                                onTextChanged: root.updateTextField("creatorNotesText", text)
                            }
                        }

                        SettingField {
                            title: "Creator Comment"

                            HusTextArea {
                                id: creatorCommentInput
                                width: parent.width
                                minRows: 3
                                maxRows: 6
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.creatorCommentText
                                placeholderText: "作者评论或导入说明"
                                onTextChanged: root.updateTextField("creatorCommentText", text)
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
        childTargets: [descriptionInput, personalityInput, scenarioInput, firstMessageInput, messageExampleInput, creatorNotesInput, creatorCommentInput]
    }

}
