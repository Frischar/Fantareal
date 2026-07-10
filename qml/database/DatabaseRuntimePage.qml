import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property var runtime: ({})
    property var databaseConfig: ({})
    property int currentView: 0
    property string selectedRoleId: ""
    property string historyRoleFilter: ""

    signal initializeRequested()
    signal openPageRequested(string page)

    implicitHeight: pageColumn.implicitHeight

    function asArray(value) {
        if (!value) {
            return [];
        }
        if (Array.isArray(value)) {
            return value;
        }
        const result = [];
        const length = Number(value.length || 0);
        for (let index = 0; index < length; ++index) {
            result.push(value[index]);
        }
        return result;
    }

    function roleConfigs() {
        return asArray((databaseConfig || {}).roles);
    }

    function roleConfig(roleId) {
        return roleConfigs().find(item =>
            String(item.role_id || item.roleId || "") === String(roleId || "")) || {};
    }

    function characterForRole(roleId) {
        return asArray(runtime.characters).find(item =>
            String(item.roleId || item.role_id || "") === String(roleId || "")) || {};
    }

    function roleItems() {
        const result = [];
        const seen = {};
        function append(roleId, roleName, mode) {
            roleId = String(roleId || "").trim();
            if (!roleId || seen[roleId]) {
                return;
            }
            seen[roleId] = true;
            result.push({
                "roleId": roleId,
                "roleName": String(roleName || roleId),
                "mode": String(mode || "")
            });
        }
        for (const role of roleConfigs()) {
            append(role.role_id || role.roleId, role.role_name || role.roleName, role.mode);
        }
        for (const character of asArray(runtime.characters)) {
            const roleId = character.roleId || character.role_id;
            const config = roleConfig(roleId);
            append(roleId, character.name || config.role_name || config.roleName, config.mode);
        }
        for (const item of asArray(runtime.variables).concat(asArray(runtime.stages))) {
            const config = roleConfig(item.roleId);
            append(item.roleId, config.role_name || config.roleName, config.mode);
        }
        return result;
    }

    function ensureSelectedRole() {
        const roles = roleItems();
        if (!roles.some(item => item.roleId === selectedRoleId)) {
            selectedRoleId = roles.length > 0 ? roles[0].roleId : "";
        }
    }

    function roleName(roleId) {
        const character = characterForRole(roleId);
        const config = roleConfig(roleId);
        return String(character.name || config.role_name || config.roleName || roleId || "角色");
    }

    function roleModeLabel(mode) {
        const labels = {
            "default": "默认记录",
            "variables": "变量与快照",
            "stages": "阶段与快照",
            "snapshot_only": "仅状态记录",
            "full": "完整数据库",
            "disabled": "不记录"
        };
        return labels[String(mode || "")] || "运行中";
    }

    function snapshotFieldConfigs() {
        const fields = asArray((databaseConfig || {}).snapshotFields).map(item => item);
        for (const role of roleConfigs()) {
            for (const field of asArray(role.snapshotFields)) {
                fields.push(field);
            }
        }
        return fields;
    }

    function variableConfigs() {
        const fields = asArray((databaseConfig || {}).variables).map(item => item);
        for (const role of roleConfigs()) {
            for (const field of asArray(role.variables)) {
                fields.push(field);
            }
        }
        return fields;
    }

    function fieldLabel(key, roleId) {
        key = String(key || "");
        const leafKey = key.includes(".") ? key.split(".").pop() : key;
        const known = {
            "name": "角色名",
            "location": "当前位置",
            "current_location": "当前位置",
            "scene": "所在场景",
            "mood": "当前心绪",
            "emotion": "情绪",
            "appearance": "外观姿态",
            "clothing": "衣着",
            "condition": "身体状态",
            "body_status": "身体状态",
            "summary": "状态摘要",
            "status_summary": "状态摘要",
            "posture": "姿态",
            "action": "动作",
            "interaction": "角色互动",
            "relationship_distance": "关系距离",
            "focus": "关注点",
            "sensory_field": "感官状态"
        };
        if (known[leafKey]) {
            return known[leafKey];
        }
        const configured = snapshotFieldConfigs().concat(variableConfigs()).find(item => {
            const itemKey = String(item.key || item.var_key || item.field_key || "");
            const itemRoleId = String(item.role_id || item.roleId || "");
            return itemKey === leafKey && (!roleId || !itemRoleId || itemRoleId === String(roleId));
        }) || {};
        return String(configured.label || configured.var_name || configured.name || leafKey || "状态");
    }

    function plainValue(value) {
        if (value === undefined || value === null || value === "") {
            return "未记录";
        }
        if (typeof value === "boolean") {
            return value ? "是" : "否";
        }
        if (Array.isArray(value)) {
            return value.length > 0 ? value.map(item => plainValue(item)).join("、") : "无";
        }
        if (typeof value === "object") {
            return String(value.label || value.name || value.summary || value.text || "已记录详细内容");
        }
        return String(value);
    }

    function readableFields(roleId) {
        const character = characterForRole(roleId);
        const result = [];
        for (const item of asArray(character.fields)) {
            const key = String(item.key || "");
            const value = item.value;
            if (value !== undefined && value !== null && value !== "") {
                result.push({
                    "key": key,
                    "label": String(item.label || fieldLabel(key, roleId)),
                    "value": plainValue(value)
                });
            }
        }
        if (result.length > 0) {
            return result;
        }
        const snapshot = asArray(runtime.snapshots)[0] || {};
        const payload = snapshot.payload || {};
        for (const key of Object.keys(payload)) {
            if (typeof payload[key] !== "object" || Array.isArray(payload[key])) {
                result.push({
                    "key": key,
                    "label": fieldLabel(key, roleId),
                    "value": plainValue(payload[key])
                });
            }
        }
        return result;
    }

    function variablesForRole(roleId) {
        const stored = asArray(runtime.variables).filter(item =>
            String(item.roleId || "") === String(roleId || ""));
        if (stored.length > 0) {
            return stored;
        }
        const character = characterForRole(roleId);
        return asArray(character.metrics).map(item => ({
            "roleId": roleId,
            "key": item.key,
            "label": item.label,
            "value": item.value,
            "maximum": item.maximum,
            "delta": item.delta,
            "reason": item.reason,
            "updatedAt": ""
        }));
    }

    function stagesForRole(roleId) {
        return asArray(runtime.stages).filter(item =>
            String(item.roleId || "") === String(roleId || ""));
    }

    function currentStage(roleId) {
        const stages = stagesForRole(roleId);
        return stages.find(item => (item.state || {}).active !== false) || stages[0] || {};
    }

    function currentStageName(roleId) {
        const stage = currentStage(roleId);
        const state = stage.state || {};
        const config = asArray(roleConfig(roleId).stages).find(item =>
            String(item.stage_key || item.stageKey || "") === String(stage.stageKey || "")) || {};
        return String(state.stageName || config.stage_name || config.stageName
            || stage.stageKey || "未进入阶段");
    }

    function runtimeValueText(item) {
        const value = plainValue((item || {}).value);
        if (item.maximum === undefined || item.maximum === null || item.maximum === "") {
            return value;
        }
        return `${value} / ${plainValue(item.maximum)}`;
    }

    function metricDeltaText(item) {
        if (item.delta === undefined || item.delta === null || item.delta === "") {
            return "无变化量";
        }
        const delta = Number(item.delta);
        return `${delta > 0 ? "+" : ""}${plainValue(item.delta)}`;
    }

    function metricOldValue(item) {
        const value = Number(item.value);
        const delta = Number(item.delta);
        return Number.isFinite(value) && Number.isFinite(delta) ? String(value - delta) : "上轮未记录";
    }

    function filteredMetricHistory() {
        return asArray(runtime.metricHistory).filter(item =>
            !historyRoleFilter || String(item.roleId || "") === historyRoleFilter);
    }

    function filteredStageHistory() {
        return asArray(runtime.stageHistory).filter(item =>
            !historyRoleFilter || String(item.roleId || "") === historyRoleFilter);
    }

    function conditionItems(values, roleId) {
        const result = [];
        for (const key of Object.keys(values || {})) {
            result.push({
                "label": fieldLabel(key, roleId),
                "value": plainValue(values[key])
            });
        }
        return result;
    }

    function relationshipTitle(item) {
        const roleA = String((item || {}).roleA || "").trim();
        const roleB = String((item || {}).roleB || "").trim();
        return roleA || roleB ? `${roleA || "未知角色"} → ${roleB || "未知角色"}`
            : String(item.pairKey || "未命名关系");
    }

    function timeText(value) {
        const text = String(value || "").replace("T", " ");
        return text.length > 19 ? text.substring(0, 19) : (text || "未记录时间");
    }

    function seasonLabel(value) {
        const labels = {
            "spring": "春",
            "summer": "夏",
            "autumn": "秋",
            "winter": "冬"
        };
        return labels[String(value || "")] || String(value || "季节未记录");
    }

    function timeSlotLabel(value) {
        const labels = {
            "dawn": "黎明",
            "morning": "上午",
            "noon": "正午",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "夜晚",
            "late_night": "深夜"
        };
        return labels[String(value || "")] || String(value || "时段未记录");
    }

    onRuntimeChanged: ensureSelectedRole()
    onDatabaseConfigChanged: ensureSelectedRole()
    Component.onCompleted: ensureSelectedRole()

    ColumnLayout {
        id: pageColumn
        width: root.width
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                HusText {
                    text: "角色状态"
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusText {
                    Layout.fillWidth: true
                    text: "查看角色当前状态、数值、长期关系和阶段变化。配置内容仍在角色卡页面维护。"
                    wrapMode: Text.Wrap
                    font.pixelSize: 12
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            HusButton {
                text: "编辑角色配置"
                type: HusButton.Type_Outlined
                onClicked: root.openPageRequested("cards")
            }

            HusButton {
                text: "初始化"
                type: HusButton.Type_Primary
                onClicked: root.initializeRequested()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: timeRow.implicitHeight + 22
            radius: 7
            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
            border.width: 1
            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.26)

            RowLayout {
                id: timeRow
                anchors.fill: parent
                anchors.margins: 11
                spacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    HusText {
                        text: "剧情时间"
                        font.pixelSize: 11
                        color: HusTheme.Primary.colorTextSecondary
                    }

                    HusText {
                        text: (root.runtime.storyTime || {}).currentTime || "尚未初始化"
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }
                }

                HusTag {
                    text: root.seasonLabel((root.runtime.storyTime || {}).season)
                    tagState: HusTag.State_Default
                }

                HusTag {
                    text: root.timeSlotLabel((root.runtime.storyTime || {}).timeSlot)
                    tagState: HusTag.State_Processing
                }

                HusText {
                    text: (root.runtime.storyTime || {}).lastDeltaText || "尚无推进记录"
                    font.pixelSize: 12
                    color: HusTheme.Primary.colorTextSecondary
                }
            }
        }

        HusSegmented {
            Layout.fillWidth: true
            options: [
                { label: "当前状态", value: "current" },
                { label: "数值变化", value: "metrics" },
                { label: "关系状态", value: "relationships" },
                { label: "阶段变化", value: "stages" }
            ]
            currentIndex: root.currentView
            onCurrentIndexChanged: root.currentView = currentIndex
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 72
            visible: root.currentView === 0 && root.roleItems().length === 0
            radius: 7
            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)

            HusText {
                anchors.centerIn: parent
                text: "还没有角色状态，点击“初始化”从当前角色卡建立初始数据。"
                font.pixelSize: 13
                color: HusTheme.Primary.colorTextSecondary
            }
        }

        GridLayout {
            Layout.fillWidth: true
            visible: root.currentView === 0 && root.roleItems().length > 0
            columns: root.width < 780 ? 1 : 2
            columnSpacing: 14
            rowSpacing: 14

            Rectangle {
                Layout.fillWidth: root.width < 780
                Layout.preferredWidth: root.width < 780 ? root.width : 250
                implicitHeight: roleListColumn.implicitHeight + 22
                radius: 7
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
                border.width: 1
                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.26)

                ColumnLayout {
                    id: roleListColumn
                    anchors.fill: parent
                    anchors.margins: 11
                    spacing: 8

                    HusText {
                        text: "角色列表"
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    Repeater {
                        model: root.roleItems()

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: roleItemColumn.implicitHeight + 18
                            radius: 6
                            color: root.selectedRoleId === modelData.roleId
                                ? HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.24 : 0.14)
                                : HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.12 : 0.34)
                            border.width: 1
                            border.color: root.selectedRoleId === modelData.roleId
                                ? HusThemeFunctions.alpha(Global.accentBlue, 0.42)
                                : HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.20)

                            ColumnLayout {
                                id: roleItemColumn
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 3

                                RowLayout {
                                    Layout.fillWidth: true

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.roleName
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                        elide: Text.ElideRight
                                    }

                                    HusTag {
                                        text: root.currentStageName(modelData.roleId)
                                        tagState: HusTag.State_Success
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: `${root.readableFields(modelData.roleId).length} 项状态 · `
                                        + `${root.variablesForRole(modelData.roleId).length} 项数值`
                                    font.pixelSize: 11
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedRoleId = modelData.roleId
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: roleDetailColumn.implicitHeight + 24
                radius: 7
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
                border.width: 1
                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.26)

                ColumnLayout {
                    id: roleDetailColumn
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            HusText {
                                text: root.roleName(root.selectedRoleId)
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                text: root.roleModeLabel((root.roleConfig(root.selectedRoleId) || {}).mode)
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextSecondary
                            }
                        }

                        HusTag {
                            text: root.currentStageName(root.selectedRoleId)
                            tagState: HusTag.State_Success
                        }
                    }

                    HusText {
                        text: "当前状态"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width < 880 ? 1 : 2
                        columnSpacing: 9
                        rowSpacing: 8

                        Repeater {
                            model: root.readableFields(root.selectedRoleId)

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: fieldColumn.implicitHeight + 16
                                radius: 6
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase,
                                    HusTheme.isDark ? 0.13 : 0.34)

                                ColumnLayout {
                                    id: fieldColumn
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 3

                                    HusText {
                                        text: modelData.label
                                        font.pixelSize: 11
                                        color: HusTheme.Primary.colorTextSecondary
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        text: modelData.value
                                        wrapMode: Text.Wrap
                                        font.pixelSize: 12
                                        color: HusTheme.Primary.colorTextPrimary
                                    }
                                }
                            }
                        }
                    }

                    HusText {
                        Layout.fillWidth: true
                        visible: root.readableFields(root.selectedRoleId).length === 0
                        text: "该角色还没有可读状态。完成一次状态记录后会在这里保留最近状态。"
                        wrapMode: Text.Wrap
                        font.pixelSize: 12
                        color: HusTheme.Primary.colorTextSecondary
                    }

                    HusText {
                        visible: root.variablesForRole(root.selectedRoleId).length > 0
                        text: "当前数值"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    Repeater {
                        model: root.variablesForRole(root.selectedRoleId)

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: variableRow.implicitHeight + 14
                            radius: 6
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase,
                                HusTheme.isDark ? 0.13 : 0.34)

                            RowLayout {
                                id: variableRow
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 9

                                HusText {
                                    Layout.fillWidth: true
                                    text: modelData.label || root.fieldLabel(modelData.key, root.selectedRoleId)
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    color: HusTheme.Primary.colorTextPrimary
                                    elide: Text.ElideRight
                                }

                                HusText {
                                    text: root.runtimeValueText(modelData)
                                    font.pixelSize: 13
                                    color: HusTheme.Primary.colorTextPrimary
                                }

                                HusTag {
                                    visible: modelData.delta !== undefined && modelData.delta !== null
                                    text: root.metricDeltaText(modelData)
                                    tagState: Number(modelData.delta || 0) < 0
                                        ? HusTag.State_Error : HusTag.State_Success
                                }
                            }
                        }
                    }

                    HusText {
                        visible: root.stagesForRole(root.selectedRoleId).length > 0
                        text: "阶段状态"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    Repeater {
                        model: root.stagesForRole(root.selectedRoleId)

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: stageColumn.implicitHeight + 16
                            radius: 6
                            color: HusThemeFunctions.alpha(Global.accentGreen, HusTheme.isDark ? 0.10 : 0.07)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(Global.accentGreen, 0.20)

                            ColumnLayout {
                                id: stageColumn
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 4

                                RowLayout {
                                    Layout.fillWidth: true

                                    HusText {
                                        Layout.fillWidth: true
                                        text: (modelData.state || {}).stageName
                                            || modelData.stageKey || "当前阶段"
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        color: HusTheme.Primary.colorTextPrimary
                                    }

                                    HusTag {
                                        text: (modelData.state || {}).active === false ? "候选" : "当前"
                                        tagState: (modelData.state || {}).active === false
                                            ? HusTag.State_Default : HusTag.State_Success
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: (modelData.state || {}).reason || "阶段状态已记录"
                                    wrapMode: Text.Wrap
                                    font.pixelSize: 12
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.currentView === 1
            spacing: 10

            Flow {
                Layout.fillWidth: true
                spacing: 7

                HusButton {
                    text: "全部角色"
                    type: root.historyRoleFilter === "" ? HusButton.Type_Primary : HusButton.Type_Outlined
                    onClicked: root.historyRoleFilter = ""
                }

                Repeater {
                    model: root.roleItems()

                    delegate: HusButton {
                        text: modelData.roleName
                        type: root.historyRoleFilter === modelData.roleId
                            ? HusButton.Type_Primary : HusButton.Type_Outlined
                        onClicked: root.historyRoleFilter = modelData.roleId
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 64
                visible: root.filteredMetricHistory().length === 0
                radius: 7
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)

                HusText {
                    anchors.centerIn: parent
                    text: "当前暂无数值变化记录。"
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            Repeater {
                model: root.filteredMetricHistory()

                delegate: Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: metricEventColumn.implicitHeight + 18
                    radius: 7
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(
                        Number(modelData.delta || 0) < 0 ? Global.accentRed : Global.accentGreen, 0.22)

                    ColumnLayout {
                        id: metricEventColumn
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true

                            HusText {
                                text: root.roleName(modelData.roleId)
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                text: modelData.label || root.fieldLabel(modelData.key, modelData.roleId)
                                font.pixelSize: 12
                                color: HusTheme.Primary.colorTextSecondary
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            HusText {
                                text: root.timeText(modelData.createdAt)
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextTertiary
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            HusText {
                                text: `${root.metricOldValue(modelData)} → ${root.plainValue(modelData.value)}`
                                font.pixelSize: 16
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusTag {
                                text: root.metricDeltaText(modelData)
                                tagState: Number(modelData.delta || 0) < 0
                                    ? HusTag.State_Error : HusTag.State_Success
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: modelData.reason || "本轮数值已更新"
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                                color: HusTheme.Primary.colorTextSecondary
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.currentView === 2
            spacing: 12

            RowLayout {
                Layout.fillWidth: true

                HusText {
                    Layout.fillWidth: true
                    text: "长期关系"
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                }

                HusTag {
                    text: `${root.asArray(root.runtime.relationships).length} 组`
                    tagState: HusTag.State_Processing
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 64
                visible: root.asArray(root.runtime.relationships).length === 0
                radius: 7
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)

                HusText {
                    anchors.centerIn: parent
                    text: "当前没有需要长期追踪的关系状态。"
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            Repeater {
                model: root.asArray(root.runtime.relationships)

                delegate: Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: relationshipColumn.implicitHeight + 20
                    radius: 7
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.22)

                    ColumnLayout {
                        id: relationshipColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 7

                        RowLayout {
                            Layout.fillWidth: true

                            HusText {
                                Layout.fillWidth: true
                                text: root.relationshipTitle(modelData)
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusTag {
                                text: modelData.stage || "关系已记录"
                                tagState: HusTag.State_Processing
                            }

                            HusText {
                                text: root.timeText(modelData.updatedAt)
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextTertiary
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            visible: Boolean(modelData.attitude)
                            text: `当前态度：${modelData.attitude}`
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: HusTheme.Primary.colorTextSecondary
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: modelData.summary || "关系状态已保存。"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: HusTheme.Primary.colorTextPrimary
                        }
                    }
                }
            }

            HusText {
                visible: root.asArray(root.runtime.relationshipHistory).length > 0
                text: "最近变化"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                color: HusTheme.Primary.colorTextPrimary
            }

            Repeater {
                model: root.asArray(root.runtime.relationshipHistory).slice(0, 30)

                delegate: Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: relationshipHistoryRow.implicitHeight + 16
                    radius: 6
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.13 : 0.34)

                    RowLayout {
                        id: relationshipHistoryRow
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 10

                        ColumnLayout {
                            Layout.preferredWidth: 220
                            spacing: 2

                            HusText {
                                Layout.fillWidth: true
                                text: root.relationshipTitle(modelData)
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                                elide: Text.ElideRight
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: modelData.previousStage
                                    ? `${modelData.previousStage} → ${modelData.stage || "新阶段"}`
                                    : (modelData.stage || "关系更新")
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextSecondary
                                elide: Text.ElideRight
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: modelData.change || modelData.summary || "关系状态已更新"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusText {
                            text: root.timeText(modelData.createdAt)
                            font.pixelSize: 11
                            color: HusTheme.Primary.colorTextTertiary
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.currentView === 3
            spacing: 10

            Flow {
                Layout.fillWidth: true
                spacing: 7

                HusButton {
                    text: "全部角色"
                    type: root.historyRoleFilter === "" ? HusButton.Type_Primary : HusButton.Type_Outlined
                    onClicked: root.historyRoleFilter = ""
                }

                Repeater {
                    model: root.roleItems()

                    delegate: HusButton {
                        text: modelData.roleName
                        type: root.historyRoleFilter === modelData.roleId
                            ? HusButton.Type_Primary : HusButton.Type_Outlined
                        onClicked: root.historyRoleFilter = modelData.roleId
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 64
                visible: root.filteredStageHistory().length === 0
                radius: 7
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.42)

                HusText {
                    anchors.centerIn: parent
                    text: "当前暂无阶段变化记录。"
                    color: HusTheme.Primary.colorTextSecondary
                }
            }

            Repeater {
                model: root.filteredStageHistory()

                delegate: Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: stageEventColumn.implicitHeight + 18
                    radius: 7
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.20 : 0.54)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(Global.accentGreen, 0.22)

                    ColumnLayout {
                        id: stageEventColumn
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true

                            HusText {
                                text: modelData.roleName || root.roleName(modelData.roleId)
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                Layout.fillWidth: true
                                text: `${modelData.fromStageName || modelData.fromStageKey || "未进入阶段"}`
                                    + ` → ${modelData.toStageName || modelData.toStageKey || "新阶段"}`
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                color: HusTheme.Primary.colorTextPrimary
                            }

                            HusText {
                                text: root.timeText(modelData.createdAt)
                                font.pixelSize: 11
                                color: HusTheme.Primary.colorTextTertiary
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: modelData.reason || "阶段条件已满足"
                            wrapMode: Text.Wrap
                            font.pixelSize: 12
                            color: HusTheme.Primary.colorTextSecondary
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.conditionItems(modelData.triggerValues, modelData.roleId).length > 0

                            Repeater {
                                model: root.conditionItems(modelData.triggerValues, modelData.roleId)

                                delegate: HusTag {
                                    text: `${modelData.label}：${modelData.value}`
                                    tagState: HusTag.State_Processing
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
