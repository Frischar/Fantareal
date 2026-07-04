import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property bool initialized: false
    property bool dirty: false
    property bool routeEnabled: false
    property bool hookAllPosts: true
    property bool failoverEnabled: true
    property bool rotateKeys: true
    property int retryAttempts: 3
    property string strategy: "priority"
    property var providers: []
    property var providerKeyDrafts: ({})
    property int selectedProviderRow: -1
    property int providerEditIndex: -1
    property string providerIdDraft: ""
    property string providerNameDraft: ""
    property string providerBaseUrlDraft: ""
    property string providerModelDraft: ""
    property bool providerEnabledDraft: true
    property int providerPriorityDraft: 1
    property int providerWeightDraft: 1

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function applyDraft(draft) {
        initialized = false;
        routeEnabled = Boolean(draft.enabled);
        hookAllPosts = draft.hook_all_posts === undefined ? true : Boolean(draft.hook_all_posts);
        failoverEnabled = draft.failover_enabled === undefined ? true : Boolean(draft.failover_enabled);
        rotateKeys = draft.rotate_keys === undefined ? true : Boolean(draft.rotate_keys);
        retryAttempts = Number(draft.retry_attempts || 3);
        strategy = draft.strategy === "round_robin" ? "round_robin" : "priority";
        providers = draft.providers || [];
        providerKeyDrafts = {};
        dirty = false;
        initialized = true;
    }

    function providerKeyDraft(index) {
        const key = String(index);
        return providerKeyDrafts[key] || "";
    }

    function setProviderKeyDraft(index, value) {
        const next = {};
        for (const key in providerKeyDrafts) {
            next[key] = providerKeyDrafts[key];
        }
        next[String(index)] = value;
        providerKeyDrafts = next;
    }

    function clearProviderKeyDraft(index) {
        const next = {};
        const removeKey = String(index);
        for (const key in providerKeyDrafts) {
            if (key !== removeKey) {
                next[key] = providerKeyDrafts[key];
            }
        }
        providerKeyDrafts = next;
    }

    function saveDraft() {
        const result = FantarealBridge.saveRouteDraft({
            "enabled": routeEnabled,
            "hook_all_posts": hookAllPosts,
            "failover_enabled": failoverEnabled,
            "rotate_keys": rotateKeys,
            "retry_attempts": retryAttempts,
            "strategy": strategy
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.routeDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function providerAt(row) {
        if (row >= 0 && row < root.providers.length) {
            return root.providers[row];
        }
        return {};
    }

    function loadProvider(row) {
        const provider = root.providerAt(row);
        if (provider.index === undefined) {
            root.newProvider();
            return;
        }
        root.selectedProviderRow = row;
        root.providerEditIndex = provider.index;
        root.providerIdDraft = provider.id || "";
        root.providerNameDraft = provider.name || "";
        root.providerBaseUrlDraft = provider.base_url || "";
        root.providerModelDraft = provider.model || "";
        root.providerEnabledDraft = provider.enabled !== false;
        root.providerPriorityDraft = Number(provider.priority || row + 1);
        root.providerWeightDraft = Number(provider.weight || 1);
    }

    function newProvider() {
        root.selectedProviderRow = -1;
        root.providerEditIndex = -1;
        root.providerIdDraft = "";
        root.providerNameDraft = "";
        root.providerBaseUrlDraft = "";
        root.providerModelDraft = "";
        root.providerEnabledDraft = true;
        root.providerPriorityDraft = root.providers.length + 1;
        root.providerWeightDraft = 1;
    }

    function reloadProviderEditor() {
        if (root.providerEditIndex < 0) {
            root.newProvider();
            return;
        }
        for (let i = 0; i < root.providers.length; ++i) {
            const provider = root.providers[i];
            if (provider.index === root.providerEditIndex) {
                root.loadProvider(i);
                return;
            }
        }
        root.newProvider();
    }

    function saveProviderDraft() {
        const result = FantarealBridge.saveRouteProviderDraft(root.providerEditIndex, {
            id: root.providerIdDraft,
            name: root.providerNameDraft,
            base_url: root.providerBaseUrlDraft,
            model: root.providerModelDraft,
            enabled: root.providerEnabledDraft,
            priority: root.providerPriorityDraft,
            weight: root.providerWeightDraft
        });
        if (result.ok) {
            message.success(result.message);
            root.providerEditIndex = result.providerIndex;
            root.applyDraft(FantarealBridge.routeDraft);
            Qt.callLater(root.reloadProviderEditor);
        } else {
            message.error(result.message, 5000);
        }
    }

    function deleteProviderDraft() {
        if (root.providerEditIndex < 0) {
            message.warning("先选择一个 Provider。", 3000);
            return;
        }
        const result = FantarealBridge.deleteRouteProvider(root.providerEditIndex);
        if (result.ok) {
            message.warning(result.message, 3000);
            root.applyDraft(FantarealBridge.routeDraft);
            root.newProvider();
        } else {
            message.error(result.message, 5000);
        }
    }

    function saveProviderKey(index) {
        const result = FantarealBridge.saveRouteProviderKey(index, root.providerKeyDraft(index));
        if (result.ok) {
            message.success(result.message);
            root.clearProviderKeyDraft(index);
            root.applyDraft(FantarealBridge.routeDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    Component.onCompleted: {
        applyDraft(FantarealBridge.routeDraft);
        if (root.providers.length > 0) {
            root.loadProvider(0);
        } else {
            root.newProvider();
        }
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.routeDraft);
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
                    text: "模型路由"
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    visible: root.dirty
                    text: "未保存"
                    tagState: HusTag.State_Warning
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: routesContent.implicitHeight + 56
                accentColor: Global.accentBlue

                ColumnLayout {
                    id: routesContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 14

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        StatPill { text: "MODEL ROUTES"; accentColor: Global.accentBlue }
                        HusTag { text: "route_forwarding.json"; presetColor: "blue" }
                        HusTag { text: FantarealBridge.routeStatus; tagState: HusTag.State_Processing }
                        HusTag {
                            text: root.routeEnabled ? "路由已启用" : "路由未启用"
                            tagState: root.routeEnabled ? HusTag.State_Success : HusTag.State_Default
                        }
                    }

                    HusText {
                        text: "Provider / Failover / Key Rotate"
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }

                    SummaryRows {
                        Layout.fillWidth: true
                        rows: FantarealBridge.routeRows
                        labelWidth: 160
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusButton {
                            text: "刷新扫描"
                            onClicked: FantarealBridge.refreshLegacyScan()
                        }

                        HusButton {
                            text: "还原表单"
                            enabled: root.dirty
                            onClicked: root.applyDraft(FantarealBridge.routeDraft)
                        }

                        Item { Layout.fillWidth: true }

                        HusButton {
                            text: "保存路由"
                            type: HusButton.Type_Primary
                            enabled: root.dirty
                            onClicked: root.saveDraft()
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: editorContent.implicitHeight + 56
                accentColor: Global.accentViolet

                ColumnLayout {
                    id: editorContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 22

                    HusText {
                        Layout.fillWidth: true
                        text: "全局路由策略"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: pageColumn.width < 880 ? 1 : 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "路由总开关"
                            description: "开启后旧业务会优先使用 Provider 路由转发。"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusSwitch {
                                    checked: root.routeEnabled
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.routeEnabled = checked;
                                        root.markDirty();
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.routeEnabled ? "模型请求会进入路由链路" : "保持直接使用设置页模型配置"
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        SettingField {
                            title: "Hook 全部 POST"
                            description: "旧业务用于拦截外部 HTTP POST。"

                            HusSwitch {
                                checked: root.hookAllPosts
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.hookAllPosts = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "故障转移"
                            description: "Provider 失败时尝试下一个候选。"

                            HusSwitch {
                                checked: root.failoverEnabled
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.failoverEnabled = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Key 轮换"
                            description: "Provider 有多个 Key 时轮换使用。"

                            HusSwitch {
                                checked: root.rotateKeys
                                checkedText: "开启"
                                uncheckedText: "关闭"
                                onToggled: {
                                    root.rotateKeys = checked;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "重试次数"
                            description: "保存时夹取到 1-10。"

                            HusInputNumber {
                                width: parent.width
                                value: root.retryAttempts
                                min: 1
                                max: 10
                                step: 1
                                precision: 0
                                onValueModified: {
                                    root.retryAttempts = Math.round(value);
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "策略"
                            description: "priority 按优先级排序；round_robin 按候选轮询。"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusButton {
                                    text: "priority"
                                    type: root.strategy === "priority" ? HusButton.Type_Primary : HusButton.Type_Outlined
                                    onClicked: {
                                        root.strategy = "priority";
                                        root.markDirty();
                                    }
                                }

                                HusButton {
                                    text: "round_robin"
                                    type: root.strategy === "round_robin" ? HusButton.Type_Primary : HusButton.Type_Outlined
                                    onClicked: {
                                        root.strategy = "round_robin";
                                        root.markDirty();
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: providerContent.implicitHeight + 56
                accentColor: Global.accentCyan

                ColumnLayout {
                    id: providerContent
                    anchors.fill: parent
                    anchors.margins: 28
                    spacing: 16

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "Provider 管理"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: `${root.providers.length} 个 Provider`
                            presetColor: "cyan"
                        }

                        HusButton {
                            text: "新增 Provider"
                            type: HusButton.Type_Primary
                            onClicked: root.newProvider()
                        }
                    }

                    HusText {
                        Layout.fillWidth: true
                        text: "可编辑 Provider 安全字段；密钥仍走单独输入框，不回显旧 Key。启用的 Provider 必须填写 Base URL 和模型名。"
                        wrapMode: Text.Wrap
                        color: HusTheme.Primary.colorTextSecondary
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: providerEditorColumn.implicitHeight + 28
                        radius: 18
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.54)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(Global.accentCyan, 0.26)

                        ColumnLayout {
                            id: providerEditorColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.providerEditIndex < 0 ? "新增 Provider" : `编辑 Provider #${root.providerEditIndex + 1}`
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                HusSwitch {
                                    checked: root.providerEnabledDraft
                                    checkedText: "启用"
                                    uncheckedText: "停用"
                                    onCheckedChanged: root.providerEnabledDraft = checked
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: pageColumn.width < 900 ? 1 : 2
                                columnSpacing: 12
                                rowSpacing: 12

                                HusInput {
                                    Layout.fillWidth: true
                                    placeholderText: "Provider ID，可留空自动生成"
                                    clearEnabled: "active"
                                    text: root.providerIdDraft
                                    onTextChanged: root.providerIdDraft = text
                                }

                                HusInput {
                                    Layout.fillWidth: true
                                    placeholderText: "Provider 名称"
                                    clearEnabled: "active"
                                    text: root.providerNameDraft
                                    onTextChanged: root.providerNameDraft = text
                                }

                                HusInput {
                                    Layout.fillWidth: true
                                    placeholderText: "Base URL，例如 https://api.example.com/v1"
                                    clearEnabled: "active"
                                    text: root.providerBaseUrlDraft
                                    onTextChanged: root.providerBaseUrlDraft = text
                                }

                                HusInput {
                                    Layout.fillWidth: true
                                    placeholderText: "模型名"
                                    clearEnabled: "active"
                                    text: root.providerModelDraft
                                    onTextChanged: root.providerModelDraft = text
                                }

                                HusInputNumber {
                                    Layout.fillWidth: true
                                    value: root.providerPriorityDraft
                                    min: 1
                                    max: 999
                                    step: 1
                                    precision: 0
                                    prefix: "Priority "
                                    onValueModified: {
                                        root.providerPriorityDraft = Math.round(value);
                                    }
                                }

                                HusInputNumber {
                                    Layout.fillWidth: true
                                    value: root.providerWeightDraft
                                    min: 1
                                    max: 999
                                    step: 1
                                    precision: 0
                                    prefix: "Weight "
                                    onValueModified: {
                                        root.providerWeightDraft = Math.round(value);
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8

                                Item { Layout.fillWidth: true }

                                HusButton {
                                    text: "删除"
                                    type: HusButton.Type_Outlined
                                    enabled: root.providerEditIndex >= 0
                                    onClicked: root.deleteProviderDraft()
                                }

                                HusButton {
                                    text: "保存 Provider"
                                    type: HusButton.Type_Primary
                                    enabled: root.providerNameDraft.trim().length > 0
                                             && (!root.providerEnabledDraft
                                                 || (root.providerBaseUrlDraft.trim().length > 0
                                                     && root.providerModelDraft.trim().length > 0))
                                    onClicked: root.saveProviderDraft()
                                }
                            }
                        }
                    }

                    HusEmpty {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 130
                        visible: root.providers.length === 0
                        description: "暂无 Provider"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: root.providers.length > 0
                        spacing: 12

                        Repeater {
                            model: root.providers

                            delegate: Rectangle {
                                id: providerCard

                                required property var modelData

                                Layout.fillWidth: true
                                implicitHeight: providerRow.implicitHeight + 28
                                radius: 8
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.36)

                                ColumnLayout {
                                    id: providerRow
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        HusText {
                                            Layout.fillWidth: true
                                            text: providerCard.modelData.name
                                            font.pixelSize: 15
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }

                                        HusTag {
                                            text: providerCard.modelData.enabled ? "已启用" : "已停用"
                                            tagState: providerCard.modelData.enabled ? HusTag.State_Success : HusTag.State_Default
                                        }

                                        HusTag {
                                            text: providerCard.modelData.keyStatus
                                            presetColor: providerCard.modelData.keyCount > 0 ? "green" : "orange"
                                        }

                                        HusButton {
                                            text: root.selectedProviderRow === index ? "编辑中" : "编辑"
                                            type: root.selectedProviderRow === index ? HusButton.Type_Primary : HusButton.Type_Outlined
                                            sizeHint: "small"
                                            onClicked: root.loadProvider(index)
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: `Base URL：${providerCard.modelData.base_url || "未配置"}`
                                        color: HusTheme.Primary.colorTextSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideMiddle
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: `Model：${providerCard.modelData.model || "未配置"} / Priority：${providerCard.modelData.priority} / Weight：${providerCard.modelData.weight}`
                                        color: HusTheme.Primary.colorTextSecondary
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        HusInput {
                                            Layout.fillWidth: true
                                            text: root.providerKeyDraft(providerCard.modelData.index)
                                            echoMode: HusInput.Password
                                            clearEnabled: "active"
                                            placeholderText: "输入新 Provider Key；留空保存则保留旧 Key"
                                            iconSource: HusIcon.KeyOutlined
                                            onTextChanged: root.setProviderKeyDraft(providerCard.modelData.index, text)
                                        }

                                        HusButton {
                                            Layout.preferredWidth: 108
                                            text: "保存 Key"
                                            type: root.providerKeyDraft(providerCard.modelData.index).trim().length > 0
                                                  ? HusButton.Type_Primary
                                                  : HusButton.Type_Outlined
                                            onClicked: root.saveProviderKey(providerCard.modelData.index)
                                        }
                                    }
                                }
                            }
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
    }

}
