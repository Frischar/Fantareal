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
    property bool entryDirty: false
    property bool worldbookEnabled: true
    property int maxHits: 3
    property string entryType: "keyword"
    property int defaultChance: 100
    property int entryCount: 0
    property int enabledEntryCount: 0
    property var entryDrafts: []
    property int selectedEntryIndex: -1
    property bool entryEnabled: true
    property string entryTitle: ""
    property string entryTrigger: ""
    property string entryDraftType: "keyword"
    property string entryContent: ""
    property string entryGroup: ""
    property int entryChance: 100
    property string entryComment: ""

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function markEntryDirty() {
        if (initialized) {
            entryDirty = true;
        }
    }

    function buttonType(currentValue, value) {
        return currentValue === value ? HusButton.Type_Primary : HusButton.Type_Outlined;
    }

    function applyDraft(draft) {
        initialized = false;
        worldbookEnabled = draft.enabled === undefined ? true : Boolean(draft.enabled);
        maxHits = Number(draft.max_hits || 3);
        entryType = draft.default_entry_type || "keyword";
        defaultChance = Number(draft.default_chance === undefined ? 100 : draft.default_chance);
        entryCount = Number(draft.entryCount || 0);
        enabledEntryCount = Number(draft.enabledEntryCount || 0);
        dirty = false;
        if (!entryDirty) {
            refreshEntryDrafts(selectedEntryIndex);
        }
        initialized = true;
    }

    function applyEntryDraft(entry) {
        initialized = false;
        selectedEntryIndex = Number(entry.index);
        entryEnabled = entry.enabled === undefined ? true : Boolean(entry.enabled);
        entryTitle = entry.title || "";
        entryTrigger = entry.trigger || "";
        entryDraftType = entry.entry_type || "keyword";
        entryContent = entry.content || "";
        entryGroup = entry.group || "";
        entryChance = Number(entry.chance === undefined ? root.defaultChance : entry.chance);
        entryComment = entry.comment || "";
        entryDirty = false;
        initialized = true;
    }

    function refreshEntryDrafts(preferredIndex) {
        entryDrafts = FantarealBridge.worldbookEntryDrafts;
        if (entryDrafts.length === 0) {
            newEntry(false);
            return;
        }
        const targetIndex = preferredIndex === undefined || preferredIndex < 0 ? Number(entryDrafts[0].index) : Number(preferredIndex);
        selectEntryByIndex(targetIndex, true);
    }

    function selectEntryByIndex(index, force) {
        if (entryDirty && !force) {
            message.warning("请先保存当前词条。", 4000);
            return;
        }
        const targetIndex = Number(index);
        for (const entry of entryDrafts) {
            if (Number(entry.index) === targetIndex) {
                applyEntryDraft(entry);
                return;
            }
        }
        if (entryDrafts.length > 0) {
            applyEntryDraft(entryDrafts[0]);
        } else {
            newEntry(false);
        }
    }

    function newEntry(markAsDirty) {
        if (entryDirty && markAsDirty) {
            message.warning("请先保存当前词条。", 4000);
            return;
        }
        initialized = false;
        selectedEntryIndex = -1;
        entryEnabled = true;
        entryTitle = "";
        entryTrigger = "";
        entryDraftType = root.entryType === "constant" ? "constant" : "keyword";
        entryContent = "";
        entryGroup = "";
        entryChance = root.defaultChance;
        entryComment = "";
        entryDirty = Boolean(markAsDirty);
        initialized = true;
    }

    function saveEntry() {
        const result = FantarealBridge.saveWorldbookEntry(selectedEntryIndex, {
            "enabled": entryEnabled,
            "title": entryTitle,
            "trigger": entryTrigger,
            "entry_type": entryDraftType,
            "content": entryContent,
            "group": entryGroup,
            "chance": entryChance,
            "comment": entryComment
        });
        if (result.ok) {
            message.success(result.message);
            entryDirty = false;
            entryDrafts = FantarealBridge.worldbookEntryDrafts;
            selectEntryByIndex(Number(result.entryIndex), true);
        } else {
            message.error(result.message, 5000);
        }
    }

    function saveDraft() {
        const result = FantarealBridge.saveWorldbookDraft({
            "enabled": worldbookEnabled,
            "max_hits": maxHits,
            "default_entry_type": entryType,
            "default_chance": defaultChance
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.worldbookDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function importWorldbook(path) {
        if (dirty || entryDirty) {
            message.warning("请先保存或还原当前修改，再导入世界书。", 5000);
            return;
        }
        const result = FantarealBridge.importWorldbookFile(path);
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.worldbookDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    Component.onCompleted: applyDraft(FantarealBridge.worldbookDraft)

    FileDialog {
        id: worldbookImportDialog
        title: "导入世界书 JSON"
        nameFilters: ["JSON 文件 (*.json)", "所有文件 (*)"]
        onAccepted: root.importWorldbook(selectedFile.toString())
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (!root.dirty && !root.entryDirty) {
                root.applyDraft(FantarealBridge.worldbookDraft);
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
            width: Math.min(parent.width - 88, 1180)
            x: 44
            y: 44
            spacing: 18

            RowLayout {
                width: parent.width
                spacing: 12

                HusText {
                    Layout.fillWidth: true
                    text: "世界书"
                    font.pixelSize: 28
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    visible: root.dirty || root.entryDirty
                    text: root.entryDirty ? "词条未保存" : "未保存"
                    tagState: HusTag.State_Warning
                }

                HusTag {
                    text: `${root.enabledEntryCount}/${root.entryCount}`
                    presetColor: "blue"
                }

                HusButton {
                    text: "导入"
                    type: HusButton.Type_Filled
                    enabled: !root.dirty && !root.entryDirty
                    onClicked: worldbookImportDialog.open()
                }

                HusButton {
                    text: "新建"
                    type: HusButton.Type_Primary
                    onClicked: root.newEntry(true)
                }

                HusButton {
                    text: "刷新"
                    onClicked: FantarealBridge.refreshLegacyScan()
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: settingsContent.implicitHeight + 36
                accentColor: Global.accentBlue

                GridLayout {
                    id: settingsContent
                    anchors.fill: parent
                    anchors.margins: 18
                    columns: pageColumn.width < 900 ? 1 : 4
                    columnSpacing: 16
                    rowSpacing: 14

                    SettingField {
                        title: "启用"

                        HusSwitch {
                            checked: root.worldbookEnabled
                            checkedText: "开启"
                            uncheckedText: "关闭"
                            onToggled: {
                                root.worldbookEnabled = checked;
                                root.markDirty();
                            }
                        }
                    }

                    SettingField {
                        title: "最大命中"

                        HusInputNumber {
                            width: parent.width
                            value: root.maxHits
                            min: 1
                            max: 20
                            step: 1
                            precision: 0
                            onValueModified: {
                                root.maxHits = Math.round(value);
                                root.markDirty();
                            }
                        }
                    }

                    SettingField {
                        title: "默认类型"

                        RowLayout {
                            width: parent.width
                            spacing: 8

                            HusButton {
                                text: "keyword"
                                type: root.buttonType(root.entryType, "keyword")
                                onClicked: {
                                    root.entryType = "keyword";
                                    root.markDirty();
                                }
                            }

                            HusButton {
                                text: "constant"
                                type: root.buttonType(root.entryType, "constant")
                                onClicked: {
                                    root.entryType = "constant";
                                    root.markDirty();
                                }
                            }
                        }
                    }

                    SettingField {
                        title: "默认概率"

                        HusInputNumber {
                            width: parent.width
                            value: root.defaultChance
                            min: 0
                            max: 100
                            step: 1
                            precision: 0
                            onValueModified: {
                                root.defaultChance = Math.round(value);
                                root.markDirty();
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.columnSpan: settingsContent.columns
                        implicitHeight: 34

                        HusButton {
                            anchors.right: parent.right
                            text: "保存设置"
                            type: HusButton.Type_Primary
                            enabled: root.dirty
                            onClicked: root.saveDraft()
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: managerContent.implicitHeight + 36
                accentColor: Global.accentCyan

                GridLayout {
                    id: managerContent
                    anchors.fill: parent
                    anchors.margins: 18
                    columns: pageColumn.width < 980 ? 1 : 2
                    columnSpacing: 18
                    rowSpacing: 18

                    ColumnLayout {
                        Layout.fillWidth: managerContent.columns === 1
                        Layout.preferredWidth: managerContent.columns === 1 ? pageColumn.width - 36 : 330
                        spacing: 10

                        HusText {
                            Layout.fillWidth: true
                            text: "词条"
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 520
                            radius: 12
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(Global.accentCyan, 0.22)
                            clip: true

                            HusEmpty {
                                anchors.centerIn: parent
                                width: 240
                                height: 150
                                visible: root.entryDrafts.length === 0
                                imageStyle: HusEmpty.Style_Simple
                            }

                            ListView {
                                id: entryList
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
                                model: root.entryDrafts
                                visible: root.entryDrafts.length > 0
                                clip: true

                                delegate: Rectangle {
                                    id: entryCard
                                    required property var modelData

                                    width: ListView.view.width
                                    implicitHeight: entryCardContent.implicitHeight + 18
                                    radius: 10
                                    color: HusThemeFunctions.alpha(Number(modelData.index) === root.selectedEntryIndex ? Global.accentCyan : HusTheme.Primary.colorBgBase, Number(modelData.index) === root.selectedEntryIndex ? 0.24 : 0.10)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(Number(modelData.index) === root.selectedEntryIndex ? Global.accentCyan : HusTheme.Primary.colorBorder, 0.34)

                                    ColumnLayout {
                                        id: entryCardContent
                                        anchors.fill: parent
                                        anchors.margins: 9
                                        spacing: 5

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            HusTag {
                                                text: entryCard.modelData.enabled ? "启用" : "停用"
                                                tagState: entryCard.modelData.enabled ? HusTag.State_Success : HusTag.State_Warning
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: entryCard.modelData.title || "未命名词条"
                                                font.pixelSize: 15
                                                font.weight: Font.DemiBold
                                                color: HusTheme.Primary.colorTextPrimary
                                                elide: Text.ElideRight
                                            }
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: entryCard.modelData.trigger || entryCard.modelData.preview || "常驻词条"
                                            color: HusTheme.Primary.colorTextTertiary
                                            font.pixelSize: 12
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: root.selectEntryByIndex(entryCard.modelData.index, false)
                                    }
                                }

                                ScrollBar.vertical: HusScrollBar {}
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            HusText {
                                Layout.fillWidth: true
                                text: root.selectedEntryIndex < 0 ? "新词条" : `编辑词条 ${root.selectedEntryIndex + 1}`
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusTag {
                                text: root.entryEnabled ? "启用" : "停用"
                                tagState: root.entryEnabled ? HusTag.State_Success : HusTag.State_Warning
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: pageColumn.width < 980 ? 1 : 2
                            columnSpacing: 14
                            rowSpacing: 14

                            SettingField {
                                title: "标题"

                                HusInput {
                                    width: parent.width
                                    text: root.entryTitle
                                    clearEnabled: "active"
                                    placeholderText: "词条标题"
                                    onTextEdited: {
                                        root.entryTitle = text;
                                        root.markEntryDirty();
                                    }
                                }
                            }

                            SettingField {
                                title: "启用"

                                HusSwitch {
                                    checked: root.entryEnabled
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.entryEnabled = checked;
                                        root.markEntryDirty();
                                    }
                                }
                            }

                            SettingField {
                                title: "类型"

                                RowLayout {
                                    width: parent.width
                                    spacing: 8

                                    HusButton {
                                        text: "keyword"
                                        type: root.buttonType(root.entryDraftType, "keyword")
                                        onClicked: {
                                            root.entryDraftType = "keyword";
                                            root.markEntryDirty();
                                        }
                                    }

                                    HusButton {
                                        text: "constant"
                                        type: root.buttonType(root.entryDraftType, "constant")
                                        onClicked: {
                                            root.entryDraftType = "constant";
                                            root.markEntryDirty();
                                        }
                                    }
                                }
                            }

                            SettingField {
                                title: "概率"

                                HusInputNumber {
                                    width: parent.width
                                    value: root.entryChance
                                    min: 0
                                    max: 100
                                    step: 1
                                    precision: 0
                                    onValueModified: {
                                        root.entryChance = Math.round(value);
                                        root.markEntryDirty();
                                    }
                                }
                            }

                            SettingField {
                                Layout.columnSpan: pageColumn.width < 980 ? 1 : 2
                                Layout.fillWidth: true
                                title: "触发词"

                                HusInput {
                                    width: parent.width
                                    text: root.entryTrigger
                                    clearEnabled: "active"
                                    placeholderText: root.entryDraftType === "keyword" ? "例如：王都, 北境" : "常驻词条可留空"
                                    onTextEdited: {
                                        root.entryTrigger = text;
                                        root.markEntryDirty();
                                    }
                                }
                            }

                            SettingField {
                                Layout.columnSpan: pageColumn.width < 980 ? 1 : 2
                                Layout.fillWidth: true
                                title: "分组"

                                HusInput {
                                    width: parent.width
                                    text: root.entryGroup
                                    clearEnabled: "active"
                                    placeholderText: "角色 / 地理 / 历史 / 规则"
                                    onTextEdited: {
                                        root.entryGroup = text;
                                        root.markEntryDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            Layout.fillWidth: true
                            title: "内容"

                            HusTextArea {
                                id: entryContentInput
                                width: parent.width
                                minRows: 8
                                maxRows: 16
                                maxLength: 12000
                                autoSize: true
                                resizable: true
                                text: root.entryContent
                                placeholderText: "世界书正文"
                                onTextChanged: {
                                    if (text !== root.entryContent) {
                                        root.entryContent = text;
                                        root.markEntryDirty();
                                    }
                                }
                            }
                        }

                        SettingField {
                            Layout.fillWidth: true
                            title: "备注"

                            HusTextArea {
                                id: entryCommentInput
                                width: parent.width
                                minRows: 2
                                maxRows: 5
                                maxLength: 240
                                autoSize: true
                                resizable: true
                                text: root.entryComment
                                placeholderText: "可选"
                                onTextChanged: {
                                    if (text !== root.entryComment) {
                                        root.entryComment = text;
                                        root.markEntryDirty();
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Item { Layout.fillWidth: true }

                            HusButton {
                                text: "还原词条"
                                enabled: root.entryDirty && root.selectedEntryIndex >= 0
                                onClicked: root.selectEntryByIndex(root.selectedEntryIndex, true)
                            }

                            HusButton {
                                text: "保存词条"
                                type: HusButton.Type_Primary
                                enabled: root.entryDirty
                                onClicked: root.saveEntry()
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
        childTargets: [entryList, entryContentInput, entryCommentInput]
    }
}
