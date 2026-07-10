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
    property string presetId: ""
    property string presetName: ""
    property bool presetEnabled: true
    property var moduleStates: ({})
    property var moduleItems: []
    property var subPresetStates: ({})
    property var subPresetItems: []

    function cloneMap(source) {
        const result = {};
        for (const key in source) {
            result[key] = Boolean(source[key]);
        }
        return result;
    }

    function statesFromItems(items) {
        const result = {};
        for (const item of items) {
            result[item.key] = Boolean(item.enabled);
        }
        return result;
    }

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function applyMutex(states, key) {
        if (!states[key]) {
            return states;
        }
        if (key === "short_paragraph") {
            states.long_paragraph = false;
        } else if (key === "long_paragraph") {
            states.short_paragraph = false;
        } else if (key === "second_person") {
            states.third_person = false;
        } else if (key === "third_person") {
            states.second_person = false;
        }
        return states;
    }

    function setModule(key, value) {
        const next = cloneMap(moduleStates);
        next[key] = Boolean(value);
        moduleStates = applyMutex(next, key);
        markDirty();
    }

    function setSubPreset(key, value) {
        const next = cloneMap(subPresetStates);
        next[key] = Boolean(value);
        subPresetStates = next;
        markDirty();
    }

    function applyDraft(draft) {
        initialized = false;
        presetId = draft.id || draft.active_preset_id || "";
        presetName = draft.name || "";
        presetEnabled = draft.enabled === undefined ? true : Boolean(draft.enabled);
        moduleStates = cloneMap(draft.modules || {});
        moduleItems = draft.moduleItems || [];
        subPresetItems = draft.subPresetItems || [];
        subPresetStates = statesFromItems(subPresetItems);
        dirty = false;
        initialized = true;
    }

    function saveDraft() {
        const result = FantarealBridge.savePresetDraft({
            "id": presetId,
            "name": presetName,
            "enabled": presetEnabled,
            "modules": moduleStates,
            "subPresets": subPresetStates
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.presetDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function importPreset(path) {
        if (root.dirty) {
            message.warning("请先保存或还原当前预设，再导入。", 5000);
            return;
        }
        const result = FantarealBridge.importPresetFile(path);
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.presetDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    Component.onCompleted: applyDraft(FantarealBridge.presetDraft)

    FileDialog {
        id: presetImportDialog
        title: "导入预设 JSON"
        nameFilters: ["JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.importPreset(selectedFile.toString())
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.presetDraft);
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
                    text: "预设"
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
                    onClicked: presetImportDialog.open()
                }

                HusButton {
                    text: "还原"
                    enabled: root.dirty
                    onClicked: root.applyDraft(FantarealBridge.presetDraft)
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
                            text: "活动预设"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: root.presetEnabled ? "已启用" : "未启用"
                            tagState: root.presetEnabled ? HusTag.State_Success : HusTag.State_Warning
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "预设名称"

                            HusInput {
                                width: parent.width
                                text: root.presetName
                                placeholderText: "默认预设"
                                clearEnabled: "active"
                                iconSource: HusIcon.EditOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.presetName = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "启用状态"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusSwitch {
                                    checked: root.presetEnabled
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.presetEnabled = checked;
                                        root.markDirty();
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.presetEnabled ? "开启" : "关闭"
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorSplit, 0.42)
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "模块开关"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 16
                        rowSpacing: 16

                        Repeater {
                            model: root.moduleItems

                            delegate: Rectangle {
                                id: moduleCard

                                required property var modelData

                                Layout.fillWidth: true
                                implicitHeight: moduleContent.implicitHeight + 28
                                radius: 8
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(root.moduleStates[modelData.key] ? Global.accentViolet : HusTheme.Primary.colorBorder, root.moduleStates[modelData.key] ? 0.52 : 0.34)

                                ColumnLayout {
                                    id: moduleContent
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        HusSwitch {
                                            checked: Boolean(root.moduleStates[moduleCard.modelData.key])
                                            checkedText: "开"
                                            uncheckedText: "关"
                                            onToggled: root.setModule(moduleCard.modelData.key, checked)
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: moduleCard.modelData.label
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        visible: root.subPresetItems.length > 0
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorSplit, 0.42)
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.subPresetItems.length > 0
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "子预设开关"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.subPresetItems.length} 个`
                            presetColor: "purple"
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.subPresetItems.length > 0
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 16
                        rowSpacing: 16

                        Repeater {
                            model: root.subPresetItems

                            delegate: Rectangle {
                                id: subPresetCard

                                required property var modelData

                                Layout.fillWidth: true
                                implicitHeight: subPresetContent.implicitHeight + 28
                                radius: 8
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.38)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(root.subPresetStates[modelData.key] ? Global.accentViolet : HusTheme.Primary.colorBorder, root.subPresetStates[modelData.key] ? 0.52 : 0.30)

                                ColumnLayout {
                                    id: subPresetContent
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        HusSwitch {
                                            checked: Boolean(root.subPresetStates[subPresetCard.modelData.key])
                                            checkedText: "开"
                                            uncheckedText: "关"
                                            onToggled: root.setSubPreset(subPresetCard.modelData.key, checked)
                                        }

                                        HusTag {
                                            text: subPresetCard.modelData.typeLabel
                                            presetColor: "purple"
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: subPresetCard.modelData.label
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: (subPresetCard.modelData.preview || "").length > 0
                                        text: subPresetCard.modelData.preview || ""
                                        color: HusTheme.Primary.colorTextTertiary
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }
                                }
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
