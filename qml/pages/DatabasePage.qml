import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    signal openPage(string page)

    readonly property var status: FantarealBridge.databaseStatus
    readonly property var runtime: FantarealBridge.databaseRuntime
    property int currentSection: 0
    property bool workerInitialized: false
    property string workerApiBaseUrl: ""
    property string workerApiKey: ""
    property string workerModel: ""
    property bool workerEnabled: true
    property bool workerAutoUpdate: true
    property real workerTemperature: 0.0
    property int workerRequestTimeout: 120
    property int workerInputTurnCount: 3
    property int workerMaxRepairAttempts: 1
    property bool storyTimeInitialized: false
    property bool storyTimeEnabled: false
    property bool storyTimeShowInRecord: true
    property string storyTimeBase: ""
    property string storyTimeCurrent: ""
    property string storyTimeAdvanceMode: "smart"
    property string storyTimeCustomType: "range"
    property int storyTimeCustomMinimum: 300
    property int storyTimeCustomMaximum: 900
    property string storyTimeDisplayMode: "datetime_minute"

    function applyWorkerDraft(draft) {
        workerInitialized = false;
        draft = draft || {};
        workerEnabled = draft.enabled === undefined ? true : Boolean(draft.enabled);
        workerAutoUpdate = draft.autoUpdate === undefined ? true : Boolean(draft.autoUpdate);
        workerApiBaseUrl = draft.apiBaseUrl || "";
        workerApiKey = "";
        workerModel = draft.model || "";
        workerTemperature = Number(draft.temperature || 0);
        workerRequestTimeout = Number(draft.requestTimeout || 120);
        workerInputTurnCount = Number(draft.inputTurnCount || 3);
        workerMaxRepairAttempts = Number(draft.maxRepairAttempts || 1);
        workerInitialized = true;
    }

    function applyStoryTime(state) {
        storyTimeInitialized = false;
        state = state || {};
        storyTimeEnabled = Boolean(state.enabled);
        storyTimeShowInRecord = state.showInRecord === undefined ? true : Boolean(state.showInRecord);
        storyTimeBase = state.baseTime || "";
        storyTimeCurrent = state.currentTime || "";
        storyTimeAdvanceMode = state.advanceMode || "smart";
        storyTimeCustomType = state.customAdvanceType === "fixed" ? "fixed" : "range";
        storyTimeCustomMinimum = Number(state.customAdvanceMinSeconds || 300);
        storyTimeCustomMaximum = Number(state.customAdvanceMaxSeconds || 900);
        storyTimeDisplayMode = state.displayMode || "datetime_minute";
        storyTimeInitialized = true;
    }

    function refreshStatus(showNotice) {
        const result = FantarealBridge.refreshDatabaseStatus();
        applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
        applyStoryTime((FantarealBridge.databaseRuntime || {}).storyTime);
        if (showNotice === false) {
            return;
        }
        if (result.ok) {
            message.success("数据库内容已刷新");
        } else {
            message.error(result.message || "数据库刷新失败", 5000);
        }
    }

    function initializeRuntime() {
        const result = FantarealBridge.initializeDatabaseRuntime();
        if (result.ok) {
            message.success(result.message || "当前角色运行状态已初始化");
        } else {
            message.error(result.message || "运行状态初始化失败", 5000);
        }
    }

    function generateLatestStateRecord() {
        const result = FantarealBridge.generateLatestDatabaseTurn();
        if (result.ok) {
            message.success(result.message || "正在生成最新状态记录");
        } else {
            message.error(result.message || "状态记录生成失败", 5000);
        }
    }

    function retryStateRecord(messageId) {
        const result = FantarealBridge.retryDatabaseTurn(messageId || "");
        if (result.ok) {
            message.success(result.message || "状态记录已重新排队");
        } else {
            message.error(result.message || "状态记录重试失败", 5000);
        }
    }

    function saveWorkerDraft() {
        const result = FantarealBridge.saveDatabaseWorkerDraft({
            "enabled": workerEnabled,
            "autoUpdate": workerAutoUpdate,
            "apiBaseUrl": workerApiBaseUrl,
            "apiKey": workerApiKey,
            "model": workerModel,
            "temperature": workerTemperature,
            "requestTimeout": workerRequestTimeout,
            "inputTurnCount": workerInputTurnCount,
            "maxRepairAttempts": workerMaxRepairAttempts
        });
        if (result.ok) {
            message.success(result.message || "数据库记录模型配置已保存");
            applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
        } else {
            message.error(result.message || "数据库记录模型配置保存失败", 5000);
        }
    }

    function saveStoryTime(action) {
        const result = FantarealBridge.saveDatabaseStoryTimeDraft({
            "action": action || "configure",
            "enabled": storyTimeEnabled,
            "showInRecord": storyTimeShowInRecord,
            "baseTime": storyTimeBase,
            "currentTime": storyTimeCurrent,
            "advanceMode": storyTimeAdvanceMode,
            "customAdvanceType": storyTimeCustomType,
            "customAdvanceMinSeconds": storyTimeCustomMinimum,
            "customAdvanceMaxSeconds": storyTimeCustomMaximum,
            "displayMode": storyTimeDisplayMode
        });
        if (result.ok) {
            message.success(result.message || "剧情时间设置已保存");
            applyStoryTime((FantarealBridge.databaseRuntime || {}).storyTime);
        } else {
            message.error(result.message || "剧情时间设置保存失败", 5000);
        }
    }

    function copyMainModel() {
        const result = FantarealBridge.copyMainModelToDatabaseWorker();
        if (result.ok) {
            message.success(result.message || "已复制主聊天模型配置");
            applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
        } else {
            message.error(result.message || "复制失败", 5000);
        }
    }

    function clearWorkerKey() {
        const result = FantarealBridge.clearDatabaseWorkerApiKey();
        if (result.ok) {
            message.success(result.message || "数据库记录模型密钥已清除");
            applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
        } else {
            message.error(result.message || "密钥清除失败", 5000);
        }
    }

    function fetchWorkerModels() {
        const result = FantarealBridge.fetchDatabaseWorkerModels();
        if (!result.ok) {
            message.error(result.message || "模型列表获取失败", 5000);
        }
    }

    function testWorkerConnection() {
        const result = FantarealBridge.testDatabaseWorkerConnection();
        if (!result.ok) {
            message.error(result.message || "连接测试失败", 5000);
        }
    }

    function statusText(statusValue) {
        if (statusValue === "ready") {
            return "已生成";
        }
        if (statusValue === "pending") {
            return "生成中";
        }
        if (statusValue === "error") {
            return "失败";
        }
        return "已跳过";
    }

    function statusState(statusValue) {
        if (statusValue === "ready") {
            return HusTag.State_Success;
        }
        if (statusValue === "error") {
            return HusTag.State_Error;
        }
        if (statusValue === "pending") {
            return HusTag.State_Processing;
        }
        return HusTag.State_Default;
    }

    function valueText(value) {
        if (value === undefined || value === null || value === "") {
            return "未记录";
        }
        if (typeof value === "boolean") {
            return value ? "是" : "否";
        }
        if (Array.isArray(value)) {
            return value.length > 0 ? value.map(item => valueText(item)).join("、") : "无";
        }
        if (typeof value === "object") {
            return Object.keys(value).map(key => `${fieldLabel(key)}：${valueText(value[key])}`).join("；") || "未记录";
        }
        return String(value);
    }

    function fieldLabel(key) {
        const labels = {
            "entryId": "条目标识",
            "entry_id": "条目标识",
            "entryType": "类型",
            "entry_type": "类型",
            "title": "标题",
            "status": "状态",
            "condition": "推进条件",
            "summary": "当前摘要",
            "evidence": "判断依据",
            "locked": "锁定",
            "reason": "判断依据",
            "active": "当前生效",
            "candidateCount": "连续确认",
            "cooldownUntilTurn": "冷却至回合",
            "previousStageName": "上一阶段"
        };
        return labels[String(key || "")] || String(key || "扩展字段");
    }

    function objectItems(value) {
        value = value || {};
        const result = [];
        for (const key of Object.keys(value)) {
            result.push({
                "key": key,
                "label": fieldLabel(key),
                "value": value[key]
            });
        }
        return result;
    }

    function sceneItems(scene) {
        scene = scene || {};
        const labels = {
            "time": "剧情时间",
            "timeSlot": "时段",
            "season": "季节",
            "location": "地点",
            "weather": "天气",
            "atmosphere": "氛围",
            "characters": "在场人物",
            "timeDelta": "时间推进",
            "eventSummary": "本轮事件"
        };
        const result = [];
        for (const key of ["time", "timeSlot", "season", "location", "weather", "atmosphere",
                           "characters", "timeDelta", "eventSummary"]) {
            const value = String(scene[key] || "").trim();
            if (value) {
                result.push({
                    "label": labels[key],
                    "value": value
                });
            }
        }
        return result;
    }

    function metricText(metric) {
        metric = metric || {};
        let result = metric.value === undefined ? "未记录" : String(metric.value);
        if (metric.maximum !== undefined && metric.maximum !== null && metric.maximum !== "") {
            result += ` / ${metric.maximum}`;
        }
        if (metric.delta !== undefined && metric.delta !== null && metric.delta !== "") {
            const delta = Number(metric.delta);
            result += `（${delta > 0 ? "+" : ""}${metric.delta}）`;
        }
        return result;
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
            root.applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
            root.applyStoryTime((FantarealBridge.databaseRuntime || {}).storyTime);
        }
    }

    Component.onCompleted: {
        applyWorkerDraft(FantarealBridge.databaseWorkerDraft);
        applyStoryTime((FantarealBridge.databaseRuntime || {}).storyTime);
        refreshStatus(false);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                RowLayout {
                    spacing: 8

                    HusText {
                        text: "数据库"
                        font.pixelSize: 28
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    HusTag {
                        text: root.status.ok ? "就绪" : "异常"
                        tagState: root.status.ok ? HusTag.State_Success : HusTag.State_Error
                    }
                }

                HusText {
                    Layout.fillWidth: true
                    text: "查看状态记录、角色运行状态、剧情账本，并配置独立的数据库记录模型。"
                    wrapMode: Text.Wrap
                    font.pixelSize: 13
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            HusButton {
                text: "刷新"
                type: HusButton.Type_Outlined
                onClicked: root.refreshStatus(true)
            }

            HusButton {
                text: "排错"
                type: HusButton.Type_Outlined
                onClicked: root.openPage("databaseDebug")
            }
        }

        HusSegmented {
            Layout.fillWidth: true
            options: [
                { label: "角色状态", value: "runtime" },
                { label: "状态记录", value: "records" },
                { label: "剧情账本", value: "ledger" },
                { label: "模型设置", value: "model" }
            ]
            currentIndex: root.currentSection
            onCurrentIndexChanged: root.currentSection = currentIndex
        }

        Flickable {
            id: scroller
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: contentColumn.implicitHeight + 12
            clip: true

            ColumnLayout {
                id: contentColumn
                width: scroller.width
                spacing: 14

                DatabaseRuntimePage {
                    Layout.fillWidth: true
                    visible: root.currentSection === 0
                    runtime: root.runtime
                    databaseConfig: (FantarealBridge.cardDraft || {}).databaseConfig || ({})
                    onInitializeRequested: root.initializeRuntime()
                    onOpenPageRequested: page => root.openPage(page)
                }


                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.currentSection === 1
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            HusText {
                                text: "状态记录"
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: "每条记录包含标题状态、场景、角色字段、数值变化、关系变化和阶段变化。"
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                                color: HusTheme.Primary.colorTextSecondary
                            }
                        }

                        HusButton {
                            text: "生成最新记录"
                            type: HusButton.Type_Primary
                            onClicked: root.generateLatestStateRecord()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 58
                        visible: FantarealBridge.databaseRecentTurns.length === 0
                        radius: 8
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.22 : 0.58)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.28)

                        HusText {
                            anchors.centerIn: parent
                            text: "还没有状态记录。完成一轮聊天后会在这里出现。"
                            font.pixelSize: 13
                            color: HusTheme.Primary.colorTextSecondary
                        }
                    }

                    Repeater {
                        model: FantarealBridge.databaseRecentTurns

                        delegate: Rectangle {
                            id: turnCard
                            Layout.fillWidth: true
                            implicitHeight: turnColumn.implicitHeight + 24
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)
                            property bool expanded: index === 0
                            property var turnData: modelData
                            property var titleData: turnData.titleCard || ({})
                            property var recordData: turnData.recordCard || ({})

                            ColumnLayout {
                                id: turnColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2

                                        HusText {
                                            Layout.fillWidth: true
                                            text: turnCard.titleData.title
                                                || `第 ${Number(turnCard.turnData.turnIndex || index + 1)} 条状态记录`
                                            font.pixelSize: 16
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                            elide: Text.ElideRight
                                        }

                                        HusText {
                                            Layout.fillWidth: true
                                            text: turnCard.titleData.subtitle
                                                || turnCard.recordData.summary
                                                || ((turnCard.turnData.error || {}).message)
                                                || "等待数据库记录模型生成内容。"
                                            maximumLineCount: turnCard.expanded ? 4 : 1
                                            elide: Text.ElideRight
                                            wrapMode: Text.Wrap
                                            font.pixelSize: 12
                                            color: HusTheme.Primary.colorTextSecondary
                                        }
                                    }

                                    HusTag {
                                        text: root.statusText(turnCard.turnData.status)
                                        tagState: root.statusState(turnCard.turnData.status)
                                    }

                                    HusText {
                                        text: turnCard.expanded ? "收起" : "展开"
                                        font.pixelSize: 12
                                        color: Global.accentBlue
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: turnCard.expanded = !turnCard.expanded
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: turnCard.expanded
                                    spacing: 10

                                    GridLayout {
                                        Layout.fillWidth: true
                                        visible: root.sceneItems(turnCard.titleData.scene).length > 0
                                        columns: scroller.width < 820 ? 1 : 2
                                        columnSpacing: 12
                                        rowSpacing: 7

                                        Repeater {
                                            model: root.sceneItems(turnCard.titleData.scene)

                                            delegate: RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8

                                                HusText {
                                                    Layout.preferredWidth: 76
                                                    text: modelData.label
                                                    font.pixelSize: 12
                                                    font.weight: Font.DemiBold
                                                    color: HusTheme.Primary.colorTextSecondary
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: modelData.value
                                                    wrapMode: Text.Wrap
                                                    font.pixelSize: 13
                                                    color: HusTheme.Primary.colorTextPrimary
                                                }
                                            }
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: String(turnCard.recordData.summary || "").length > 0
                                        text: turnCard.recordData.summary || ""
                                        wrapMode: Text.Wrap
                                        font.pixelSize: 13
                                        lineHeight: 1.2
                                        color: HusTheme.Primary.colorTextSecondary
                                    }

                                    Repeater {
                                        model: turnCard.recordData.characters || []

                                        delegate: Rectangle {
                                            id: characterCard
                                            Layout.fillWidth: true
                                            implicitHeight: characterColumn.implicitHeight + 20
                                            radius: 7
                                            color: HusThemeFunctions.alpha(Global.accentViolet, HusTheme.isDark ? 0.10 : 0.07)
                                            border.width: 1
                                            border.color: HusThemeFunctions.alpha(Global.accentViolet, 0.18)
                                            property var characterData: modelData

                                            ColumnLayout {
                                                id: characterColumn
                                                anchors.fill: parent
                                                anchors.margins: 10
                                                spacing: 7

                                                RowLayout {
                                                    Layout.fillWidth: true

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        text: characterCard.characterData.name || "角色"
                                                        font.pixelSize: 14
                                                        font.weight: Font.DemiBold
                                                        color: HusTheme.Primary.colorTextPrimary
                                                    }

                                                    HusTag {
                                                        text: `${(characterCard.characterData.fields || []).length} 字段`
                                                        tagState: HusTag.State_Default
                                                    }
                                                }

                                                Repeater {
                                                    model: characterCard.characterData.fields || []

                                                    delegate: RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        HusText {
                                                            Layout.preferredWidth: 130
                                                            text: modelData.label || modelData.key
                                                            font.pixelSize: 12
                                                            font.weight: Font.DemiBold
                                                            color: HusTheme.Primary.colorTextSecondary
                                                            elide: Text.ElideRight
                                                        }

                                                        HusText {
                                                            Layout.fillWidth: true
                                                            text: root.valueText(modelData.value)
                                                            wrapMode: Text.Wrap
                                                            font.pixelSize: 13
                                                            color: HusTheme.Primary.colorTextPrimary
                                                        }
                                                    }
                                                }

                                                Flow {
                                                    Layout.fillWidth: true
                                                    visible: (characterCard.characterData.metrics || []).length > 0
                                                    spacing: 7

                                                    Repeater {
                                                        model: characterCard.characterData.metrics || []

                                                        delegate: Rectangle {
                                                            implicitWidth: metricChip.implicitWidth + 24
                                                            implicitHeight: metricReason.visible ? 52 : 34
                                                            radius: 7
                                                            color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.13 : 0.09)
                                                            border.width: 1
                                                            border.color: HusThemeFunctions.alpha(Global.accentGold, 0.20)

                                                            Column {
                                                                anchors.centerIn: parent
                                                                spacing: 1

                                                                HusText {
                                                                    id: metricChip
                                                                    text: `${modelData.label || modelData.key}：${root.metricText(modelData)}`
                                                                    font.pixelSize: 12
                                                                    color: HusTheme.Primary.colorTextPrimary
                                                                }

                                                                HusText {
                                                                    id: metricReason
                                                                    visible: String(modelData.reason || "").length > 0
                                                                    text: modelData.reason || ""
                                                                    font.pixelSize: 10
                                                                    color: HusTheme.Primary.colorTextTertiary
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        visible: (turnCard.recordData.metrics || []).length > 0
                                        spacing: 7

                                        HusText {
                                            text: "本轮数值变化"
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                        }

                                        Flow {
                                            Layout.fillWidth: true
                                            spacing: 7

                                            Repeater {
                                                model: turnCard.recordData.metrics || []

                                                delegate: HusTag {
                                                    text: `${modelData.label || modelData.key}：${root.metricText(modelData)}`
                                                    tagState: Number(modelData.delta || 0) < 0
                                                        ? HusTag.State_Error : HusTag.State_Processing
                                                }
                                            }
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        visible: (turnCard.recordData.relationships || []).length > 0
                                        spacing: 7

                                        HusText {
                                            text: "关系与阶段变化"
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                            color: HusTheme.Primary.colorTextPrimary
                                        }

                                        Repeater {
                                            model: turnCard.recordData.relationships || []

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: relationshipColumn.implicitHeight + 16
                                                radius: 7
                                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.13 : 0.38)

                                                ColumnLayout {
                                                    id: relationshipColumn
                                                    anchors.fill: parent
                                                    anchors.margins: 8
                                                    spacing: 3

                                                    RowLayout {
                                                        Layout.fillWidth: true

                                                        HusText {
                                                            Layout.fillWidth: true
                                                            text: modelData.pair || "关系"
                                                            font.pixelSize: 13
                                                            font.weight: Font.DemiBold
                                                            color: HusTheme.Primary.colorTextPrimary
                                                        }

                                                        HusTag {
                                                            visible: String(modelData.stage || "").length > 0
                                                            text: modelData.stage || ""
                                                            tagState: HusTag.State_Success
                                                        }
                                                    }

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        visible: String(modelData.change || "").length > 0
                                                        text: modelData.change || ""
                                                        wrapMode: Text.Wrap
                                                        font.pixelSize: 12
                                                        color: HusTheme.Primary.colorTextSecondary
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: Boolean(turnCard.turnData.canRetry)

                                        Item {
                                            Layout.fillWidth: true
                                        }

                                        HusButton {
                                            text: "重新生成"
                                            type: HusButton.Type_Outlined
                                            onClicked: root.retryStateRecord(turnCard.turnData.messageId)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.currentSection === 2
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: storyTimeColumn.implicitHeight + 28
                        radius: 8
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                        ColumnLayout {
                            id: storyTimeColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 12

                            RowLayout {
                                Layout.fillWidth: true

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    HusText {
                                        text: "剧情时间"
                                        font.pixelSize: 20
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: (root.runtime.storyTime || {}).displayTime
                                            || (root.runtime.storyTime || {}).currentTime
                                            || "尚未初始化"
                                        wrapMode: Text.Wrap
                                        font.pixelSize: 13
                                        color: HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                HusSwitch {
                                    checked: root.storyTimeEnabled
                                    checkedText: "启用"
                                    uncheckedText: "关闭"
                                    onToggled: root.storyTimeEnabled = checked
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: scroller.width < 850 ? 1 : 2
                                columnSpacing: 16
                                rowSpacing: 12

                                SettingField {
                                    title: "基准时间"
                                    description: "格式：年-月-日 时:分:秒。"

                                    HusInput {
                                        width: parent.width
                                        text: root.storyTimeBase
                                        placeholderText: "2026-01-01 08:00:00"
                                        onTextEdited: root.storyTimeBase = text
                                    }
                                }

                                SettingField {
                                    title: "当前时间"
                                    description: "校准时使用此值。"

                                    HusInput {
                                        width: parent.width
                                        text: root.storyTimeCurrent
                                        placeholderText: "2026-01-01 08:00:00"
                                        onTextEdited: root.storyTimeCurrent = text
                                    }
                                }

                                SettingField {
                                    Layout.columnSpan: scroller.width < 850 ? 1 : 2
                                    title: "推进方式"

                                    HusSegmented {
                                        width: Math.min(parent.width, 560)
                                        options: [
                                            { label: "智能判断", value: "smart" },
                                            { label: "明确时间", value: "explicit" },
                                            { label: "自定义", value: "custom" },
                                            { label: "手动", value: "manual" }
                                        ]
                                        currentIndex: root.storyTimeAdvanceMode === "explicit" ? 1
                                            : (root.storyTimeAdvanceMode === "custom" ? 2
                                            : (root.storyTimeAdvanceMode === "manual" ? 3 : 0))
                                        onCurrentIndexChanged: root.storyTimeAdvanceMode
                                            = ["smart", "explicit", "custom", "manual"][currentIndex]
                                    }
                                }

                                SettingField {
                                    visible: root.storyTimeAdvanceMode === "custom"
                                    Layout.columnSpan: scroller.width < 850 ? 1 : 2
                                    title: "自定义推进秒数"

                                    RowLayout {
                                        width: parent.width
                                        spacing: 10

                                        HusSegmented {
                                            Layout.preferredWidth: 210
                                            options: [
                                                { label: "固定", value: "fixed" },
                                                { label: "范围", value: "range" }
                                            ]
                                            currentIndex: root.storyTimeCustomType === "fixed" ? 0 : 1
                                            onCurrentIndexChanged: root.storyTimeCustomType
                                                = currentIndex === 0 ? "fixed" : "range"
                                        }

                                        HusInputNumber {
                                            Layout.fillWidth: true
                                            value: root.storyTimeCustomMinimum
                                            min: 0
                                            max: 86400
                                            step: 60
                                            precision: 0
                                            onValueModified: root.storyTimeCustomMinimum = Math.round(value)
                                        }

                                        HusInputNumber {
                                            Layout.fillWidth: true
                                            visible: root.storyTimeCustomType === "range"
                                            value: root.storyTimeCustomMaximum
                                            min: 0
                                            max: 86400
                                            step: 60
                                            precision: 0
                                            onValueModified: root.storyTimeCustomMaximum = Math.round(value)
                                        }
                                    }
                                }

                                SettingField {
                                    Layout.columnSpan: scroller.width < 850 ? 1 : 2
                                    title: "状态记录展示"

                                    RowLayout {
                                        width: parent.width
                                        spacing: 12

                                        HusSwitch {
                                            checked: root.storyTimeShowInRecord
                                            checkedText: "显示"
                                            uncheckedText: "隐藏"
                                            onToggled: root.storyTimeShowInRecord = checked
                                        }

                                        HusSegmented {
                                            Layout.fillWidth: true
                                            options: [
                                                { label: "精确到分钟", value: "datetime_minute" },
                                                { label: "精确到秒", value: "datetime_second" },
                                                { label: "天数与时段", value: "day_slot" }
                                            ]
                                            currentIndex: root.storyTimeDisplayMode === "datetime_second" ? 1
                                                : (root.storyTimeDisplayMode === "day_slot" ? 2 : 0)
                                            onCurrentIndexChanged: root.storyTimeDisplayMode
                                                = ["datetime_minute", "datetime_second", "day_slot"][currentIndex]
                                        }
                                    }
                                }
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 8

                                HusButton {
                                    text: "保存"
                                    type: HusButton.Type_Primary
                                    onClicked: root.saveStoryTime("configure")
                                }

                                HusButton {
                                    text: "初始化"
                                    type: HusButton.Type_Outlined
                                    onClicked: root.saveStoryTime("initialize")
                                }

                                HusButton {
                                    text: "校准"
                                    type: HusButton.Type_Outlined
                                    enabled: root.storyTimeCurrent.length > 0
                                    onClicked: root.saveStoryTime("calibrate")
                                }

                                HusButton {
                                    text: "重置"
                                    type: HusButton.Type_Outlined
                                    enabled: root.storyTimeBase.length > 0
                                    onClicked: root.saveStoryTime("reset")
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: ledgerColumn.implicitHeight + 28
                        radius: 8
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                        ColumnLayout {
                            id: ledgerColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true

                                HusText {
                                    Layout.fillWidth: true
                                    text: "剧情账本"
                                    font.pixelSize: 20
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                HusTag {
                                    text: `${(root.runtime.ledger || []).length} 条`
                                    tagState: HusTag.State_Processing
                                }
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: "只记录仍会影响后续剧情的事件、任务、线索和关键物品。"
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                                color: HusTheme.Primary.colorTextSecondary
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 52
                                visible: (root.runtime.ledger || []).length === 0
                                radius: 7
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.40)

                                HusText {
                                    anchors.centerIn: parent
                                    text: "当前没有需要持续追踪的剧情事项。"
                                    font.pixelSize: 13
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }

                            Repeater {
                                model: root.runtime.ledger || []

                                delegate: Rectangle {
                                    id: ledgerCard
                                    Layout.fillWidth: true
                                    implicitHeight: ledgerItemColumn.implicitHeight + 18
                                    radius: 7
                                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
                                    border.width: 1
                                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.24)
                                    property bool expanded: false
                                    property var ledgerData: modelData

                                    ColumnLayout {
                                        id: ledgerItemColumn
                                        anchors.fill: parent
                                        anchors.margins: 9
                                        spacing: 6

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            HusTag {
                                                text: ledgerCard.ledgerData.entryType || "事件"
                                                tagState: HusTag.State_Default
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: ledgerCard.ledgerData.content || "未命名事项"
                                                maximumLineCount: ledgerCard.expanded ? 6 : 1
                                                elide: Text.ElideRight
                                                wrapMode: Text.Wrap
                                                font.pixelSize: 13
                                                color: HusTheme.Primary.colorTextPrimary
                                            }

                                            HusText {
                                                text: ledgerCard.expanded ? "收起" : "展开"
                                                font.pixelSize: 12
                                                color: Global.accentBlue
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: ledgerCard.expanded = !ledgerCard.expanded
                                            }
                                        }

                                        Repeater {
                                            model: ledgerCard.expanded
                                                ? root.objectItems(ledgerCard.ledgerData.payload) : []

                                            delegate: RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 10

                                                HusText {
                                                    Layout.preferredWidth: 130
                                                    text: modelData.label || modelData.key
                                                    font.pixelSize: 12
                                                    font.weight: Font.DemiBold
                                                    color: HusTheme.Primary.colorTextSecondary
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: root.valueText(modelData.value)
                                                    wrapMode: Text.Wrap
                                                    font.pixelSize: 12
                                                    color: HusTheme.Primary.colorTextPrimary
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: scroller.width < 900 ? 1 : 2
                        columnSpacing: 14
                        rowSpacing: 14

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: storyHistoryColumn.implicitHeight + 24
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                            ColumnLayout {
                                id: storyHistoryColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                HusText {
                                    text: "时间推进记录"
                                    font.pixelSize: 16
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                Repeater {
                                    model: (root.runtime.storyTimeHistory || []).slice(0, 20)

                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: storyHistoryItem.implicitHeight + 16
                                        radius: 7
                                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.40)

                                        ColumnLayout {
                                            id: storyHistoryItem
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 3

                                            HusText {
                                                Layout.fillWidth: true
                                                text: `${modelData.oldTime || "未记录"} → ${modelData.newTime || "未记录"}`
                                                wrapMode: Text.Wrap
                                                font.pixelSize: 12
                                                font.weight: Font.DemiBold
                                                color: HusTheme.Primary.colorTextPrimary
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: modelData.reason || modelData.deltaText || "时间已推进"
                                                wrapMode: Text.Wrap
                                                font.pixelSize: 11
                                                color: HusTheme.Primary.colorTextSecondary
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: stageHistoryColumn.implicitHeight + 24
                            radius: 8
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                            ColumnLayout {
                                id: stageHistoryColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                HusText {
                                    text: "阶段变化记录"
                                    font.pixelSize: 16
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                Repeater {
                                    model: (root.runtime.stageHistory || []).slice(0, 20)

                                    delegate: Rectangle {
                                        id: stageHistoryCard
                                        Layout.fillWidth: true
                                        implicitHeight: stageHistoryItem.implicitHeight + 16
                                        radius: 7
                                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.40)
                                        property bool expanded: false
                                        property var stageData: modelData

                                        ColumnLayout {
                                            id: stageHistoryItem
                                            anchors.fill: parent
                                            anchors.margins: 8
                                            spacing: 4

                                            RowLayout {
                                                Layout.fillWidth: true

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: `${stageHistoryCard.stageData.roleName
                                                        || stageHistoryCard.stageData.roleId || "角色"}：${stageHistoryCard.stageData.fromStageName
                                                        || stageHistoryCard.stageData.fromStageKey || "未进入阶段"} → ${stageHistoryCard.stageData.toStageName
                                                        || stageHistoryCard.stageData.toStageKey || "阶段"}`
                                                    wrapMode: Text.Wrap
                                                    font.pixelSize: 12
                                                    font.weight: Font.DemiBold
                                                    color: HusTheme.Primary.colorTextPrimary
                                                }

                                                HusText {
                                                    text: stageHistoryCard.expanded ? "收起" : "展开"
                                                    font.pixelSize: 11
                                                    color: Global.accentBlue
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: stageHistoryCard.expanded = !stageHistoryCard.expanded
                                                }
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                text: stageHistoryCard.stageData.reason || "阶段条件已满足"
                                                wrapMode: Text.Wrap
                                                font.pixelSize: 11
                                                color: HusTheme.Primary.colorTextSecondary
                                            }

                                            HusText {
                                                Layout.fillWidth: true
                                                visible: stageHistoryCard.expanded
                                                text: root.valueText(stageHistoryCard.stageData.triggerValues)
                                                wrapMode: Text.WrapAnywhere
                                                font.family: "Consolas"
                                                font.pixelSize: 11
                                                color: HusTheme.Primary.colorTextTertiary
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    visible: root.currentSection === 3
                    implicitHeight: workerColumn.implicitHeight + 28
                    radius: 8
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.24 : 0.62)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.30)

                    ColumnLayout {
                        id: workerColumn
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                HusText {
                                    text: "数据库记录模型"
                                    font.pixelSize: 20
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: "独立于主聊天模型，用于快速提取结构化状态、变量和剧情账本。"
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 12
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }

                            HusButton {
                                text: "保存"
                                type: HusButton.Type_Primary
                                onClicked: root.saveWorkerDraft()
                            }
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: scroller.width < 850 ? 1 : 2
                            columnSpacing: 16
                            rowSpacing: 14

                            SettingField {
                                title: "运行方式"

                                RowLayout {
                                    width: parent.width
                                    spacing: 12

                                    HusSwitch {
                                        checked: root.workerEnabled
                                        checkedText: "启用"
                                        uncheckedText: "关闭"
                                        onToggled: root.workerEnabled = checked
                                    }

                                    HusSwitch {
                                        checked: root.workerAutoUpdate
                                        checkedText: "自动生成"
                                        uncheckedText: "手动生成"
                                        onToggled: root.workerAutoUpdate = checked
                                    }
                                }
                            }

                            SettingField {
                                title: "API 地址"

                                HusInput {
                                    width: parent.width
                                    text: root.workerApiBaseUrl
                                    placeholderText: "https://api.example.com/v1"
                                    clearEnabled: "active"
                                    iconSource: HusIcon.ApiOutlined
                                    iconPosition: HusInput.Position_Left
                                    onTextEdited: root.workerApiBaseUrl = text
                                }
                            }

                            SettingField {
                                title: "模型"

                                ColumnLayout {
                                    width: parent.width
                                    spacing: 8

                                    HusInput {
                                        Layout.fillWidth: true
                                        text: root.workerModel
                                        placeholderText: "flash / mini / fast-json"
                                        clearEnabled: "active"
                                        iconSource: HusIcon.RobotOutlined
                                        iconPosition: HusInput.Position_Left
                                        onTextEdited: root.workerModel = text
                                    }

                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        visible: FantarealBridge.databaseWorkerModels.length > 0

                                        Repeater {
                                            model: FantarealBridge.databaseWorkerModels

                                            delegate: HusButton {
                                                text: modelData
                                                type: modelData === root.workerModel
                                                    ? HusButton.Type_Primary : HusButton.Type_Outlined
                                                onClicked: root.workerModel = modelData
                                            }
                                        }
                                    }
                                }
                            }

                            SettingField {
                                title: "API Key"
                                description: FantarealBridge.databaseWorkerDraft.apiKeyConfigured
                                    ? "已配置，输入新值会覆盖。" : "未配置。"

                                HusInput {
                                    width: parent.width
                                    text: root.workerApiKey
                                    placeholderText: FantarealBridge.databaseWorkerDraft.apiKeyConfigured
                                        ? "已配置" : "未配置"
                                    echoMode: HusInput.Password
                                    clearEnabled: "active"
                                    iconSource: HusIcon.KeyOutlined
                                    iconPosition: HusInput.Position_Left
                                    onTextEdited: root.workerApiKey = text
                                }
                            }

                            SettingField {
                                title: "温度"

                                HusInputNumber {
                                    width: parent.width
                                    value: root.workerTemperature
                                    min: 0
                                    max: 2
                                    step: 0.1
                                    precision: 2
                                    onValueModified: root.workerTemperature = value
                                }
                            }

                            SettingField {
                                title: "请求参数"

                                RowLayout {
                                    width: parent.width
                                    spacing: 8

                                    HusInputNumber {
                                        Layout.fillWidth: true
                                        value: root.workerRequestTimeout
                                        min: 10
                                        max: 600
                                        step: 5
                                        precision: 0
                                        suffix: " 秒"
                                        onValueModified: root.workerRequestTimeout = Math.round(value)
                                    }

                                    HusInputNumber {
                                        Layout.fillWidth: true
                                        value: root.workerInputTurnCount
                                        min: 1
                                        max: 20
                                        step: 1
                                        precision: 0
                                        suffix: " 轮"
                                        onValueModified: root.workerInputTurnCount = Math.round(value)
                                    }

                                    HusInputNumber {
                                        Layout.fillWidth: true
                                        value: root.workerMaxRepairAttempts
                                        min: 0
                                        max: 1
                                        step: 1
                                        precision: 0
                                        suffix: " 次修复"
                                        onValueModified: root.workerMaxRepairAttempts = Math.round(value)
                                    }
                                }
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8

                            HusButton {
                                text: "复制主聊天模型"
                                type: HusButton.Type_Outlined
                                onClicked: root.copyMainModel()
                            }

                            HusButton {
                                text: "获取模型"
                                type: HusButton.Type_Outlined
                                onClicked: root.fetchWorkerModels()
                            }

                            HusButton {
                                text: "测试连接"
                                type: HusButton.Type_Outlined
                                onClicked: root.testWorkerConnection()
                            }

                            HusButton {
                                text: "清除密钥"
                                type: HusButton.Type_Outlined
                                onClicked: root.clearWorkerKey()
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: FantarealBridge.databaseWorkerStatus.message || "等待操作"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: FantarealBridge.databaseWorkerStatus.ok === false
                                ? HusTheme.Primary.colorError : HusTheme.Primary.colorTextSecondary
                        }
                    }
                }
            }

            ScrollBar.vertical: HusScrollBar {}
        }
    }
}
