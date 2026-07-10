import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property string draftMessage: ""
    property bool generating: FantarealBridge.chatGenerating
    property bool clearDraftOnGenerationFinished: false
    property bool hasMessages: FantarealBridge.chatMessages.length > 0
    property bool outputSplittingEnabled: FantarealBridge.settingsDraft.output_splitting_enabled === undefined ? true : Boolean(FantarealBridge.settingsDraft.output_splitting_enabled)
    property bool memoryOrganizing: root.generating && String(FantarealBridge.chatGenerationStatus).indexOf("整理回忆") >= 0
    property real backgroundStrength: Math.max(0, Math.min(1, Number(FantarealBridge.backgroundImagePreviewOpacity)))
    property real composerGlassAlpha: HusTheme.isDark ? Math.max(0.025, 0.065 - root.backgroundStrength * 0.040) : Math.max(0.030, 0.095 - root.backgroundStrength * 0.060)
    property real inputGlassAlpha: HusTheme.isDark ? Math.max(0.035, 0.105 - root.backgroundStrength * 0.060) : Math.max(0.045, 0.145 - root.backgroundStrength * 0.085)
    property string revealingAssistantMessageId: ""
    property int revealingPartCount: 0
    property int revealingTotalParts: 0
    property bool waitingForAssistantReveal: false
    property int waitingAssistantMinIndex: -1
    property string loadingBubbleText: "......"
    property int bubbleRevealDelayMs: 3000

    signal openPage(string page)

    function activeRoleName() {
        const name = FantarealBridge.cardDraft.name || "";
        return name.trim().length > 0 ? name : "Fantareal";
    }

    function openingText() {
        const firstMessage = FantarealBridge.cardDraft.first_mes || "";
        if (firstMessage.trim().length > 0) {
            return firstMessage;
        }
        return "开始聊天。";
    }

    function submitMessage(withReply) {
        if (root.generating) {
            return;
        }
        if (root.draftMessage.trim().length === 0) {
            message.warning("先输入一条消息。", 3000);
            return;
        }
        const result = withReply ? FantarealBridge.startChatMessageWithReply(root.draftMessage) : FantarealBridge.sendChatMessage(root.draftMessage);
        if (withReply && result.ok && result.started) {
            root.clearDraftOnGenerationFinished = false;
            root.revealingAssistantMessageId = "";
            root.waitingForAssistantReveal = true;
            root.waitingAssistantMinIndex = FantarealBridge.chatMessages.length;
            bubbleRevealTimer.stop();
            root.draftMessage = "";
            input.clear();
            message.success(result.message);
            Qt.callLater(messageList.positionViewAtEnd);
            return;
        }
        if (result.ok) {
            message.success(result.message);
            root.draftMessage = "";
            input.clear();
            Qt.callLater(messageList.positionViewAtEnd);
        } else {
            message.error(result.message, 5000);
        }
    }

    function submitDemoMessage() {
        if (root.generating) {
            return;
        }
        if (root.draftMessage.trim().length === 0) {
            message.warning("先输入一条消息。", 3000);
            return;
        }
        const result = FantarealBridge.sendChatMessageDemoReply(root.draftMessage);
        if (result.ok) {
            message.success(result.message);
            root.draftMessage = "";
            input.clear();
            Qt.callLater(messageList.positionViewAtEnd);
        } else {
            message.error(result.message, 5000);
        }
    }

    function retryLastReply() {
        if (root.generating) {
            return;
        }
        if (FantarealBridge.chatMessages.length === 0) {
            message.warning("还没有可重试的聊天记录。", 3000);
            return;
        }
        const result = FantarealBridge.startRegenerateLastChatReply();
        if (result.ok && result.started) {
            root.clearDraftOnGenerationFinished = false;
            root.revealingAssistantMessageId = "";
            root.waitingForAssistantReveal = true;
            root.waitingAssistantMinIndex = FantarealBridge.chatMessages.length;
            bubbleRevealTimer.stop();
            message.success(result.message);
            return;
        }
        if (result.ok) {
            message.success(result.message);
            Qt.callLater(messageList.positionViewAtEnd);
        } else {
            message.error(result.message, 5000);
        }
    }

    function stopGeneration() {
        const result = FantarealBridge.stopChatGeneration();
        if (result.ok) {
            message.warning(result.message, 3000);
        } else {
            message.error(result.message, 4000);
        }
    }

    function endConversation() {
        if (root.generating) {
            message.warning("正在生成回复，暂时不能结束对话。", 3000);
            return;
        }
        if (!root.hasMessages) {
            message.warning("当前没有可结束的对话。", 3000);
            return;
        }
        bubbleRevealTimer.stop();
        root.revealingAssistantMessageId = "";
        root.revealingPartCount = 0;
        root.revealingTotalParts = 0;
        root.waitingForAssistantReveal = false;
        root.waitingAssistantMinIndex = -1;
        const result = FantarealBridge.endChatConversation();
        if (result.ok) {
            root.draftMessage = "";
            input.clear();
            message.success(result.message);
            Qt.callLater(messageList.positionViewAtEnd);
        } else {
            message.error(result.message, 6000);
        }
    }

    function handleInputReturn(event) {
        if ((event.modifiers & Qt.ShiftModifier) !== 0) {
            event.accepted = false;
            return;
        }
        if (event.modifiers !== Qt.NoModifier && event.modifiers !== Qt.KeypadModifier) {
            event.accepted = false;
            return;
        }
        event.accepted = true;
        root.submitMessage(true);
    }

    function partsForMessage(item) {
        const parts = item.parts && item.parts.length > 0 ? item.parts : [item.content];
        return parts;
    }

    function revealDelayForText(text) {
        return root.bubbleRevealDelayMs;
    }

    function revealingParts() {
        const messages = FantarealBridge.chatMessages;
        for (let i = messages.length - 1; i >= 0; --i) {
            const item = messages[i];
            if (item.message_id === root.revealingAssistantMessageId) {
                return item.parts && item.parts.length > 0 ? item.parts : [item.content];
            }
        }
        return [];
    }

    function finishAssistantReveal() {
        bubbleRevealTimer.stop();
        root.revealingAssistantMessageId = "";
        root.revealingPartCount = 0;
        root.revealingTotalParts = 0;
        root.waitingForAssistantReveal = false;
        root.waitingAssistantMinIndex = -1;
    }

    function scheduleNextBubbleReveal() {
        const parts = root.revealingParts();
        if (parts.length === 0 || root.revealingPartCount >= parts.length) {
            root.finishAssistantReveal();
            return;
        }
        const currentIndex = Math.max(0, Math.min(root.revealingPartCount - 1, parts.length - 1));
        bubbleRevealTimer.interval = root.revealDelayForText(parts[currentIndex]);
        bubbleRevealTimer.restart();
    }

    function shouldHideAssistantUntilSplit(item) {
        if (!root.waitingForAssistantReveal || !item.isAssistant || !item.message_id) {
            return false;
        }
        if (item.message_id === root.revealingAssistantMessageId) {
            return false;
        }
        return root.waitingAssistantMinIndex >= 0 && item.index >= root.waitingAssistantMinIndex;
    }

    function startAssistantReveal() {
        const messages = FantarealBridge.chatMessages;
        for (let i = messages.length - 1; i >= 0; --i) {
            const item = messages[i];
            const parts = item.parts && item.parts.length > 0 ? item.parts : [];
            if (item.isAssistant && parts.length > 1 && item.message_id) {
                root.revealingAssistantMessageId = item.message_id;
                root.revealingPartCount = 1;
                root.revealingTotalParts = parts.length;
                root.scheduleNextBubbleReveal();
                Qt.callLater(messageList.positionViewAtEnd);
                return;
            }
        }
        root.finishAssistantReveal();
    }

    function roleName(item) {
        if (item.isUser) {
            return "你";
        }
        if (item.isAssistant) {
            return root.activeRoleName();
        }
        return "System";
    }

    function avatarText(item) {
        if (item.isUser) {
            return "你";
        }
        const name = root.roleName(item).trim();
        return name.length > 0 ? name.charAt(0) : "F";
    }

    function stateRecordStatusText(record) {
        const status = String((record || {}).status || "");
        if (status === "ready") {
            return "已生成";
        }
        if (status === "pending") {
            return "生成中";
        }
        if (status === "error") {
            return "失败";
        }
        return "已跳过";
    }

    function stateRecordStatusState(record) {
        const status = String((record || {}).status || "");
        if (status === "ready") {
            return HusTag.State_Success;
        }
        if (status === "error") {
            return HusTag.State_Error;
        }
        if (status === "pending") {
            return HusTag.State_Processing;
        }
        return HusTag.State_Default;
    }

    function displayValue(value) {
        if (value === undefined || value === null) {
            return "";
        }
        if (Array.isArray(value)) {
            return value.map(item => root.displayValue(item)).filter(item => item.length > 0).join("、");
        }
        if (typeof value === "object") {
            return JSON.stringify(value);
        }
        return String(value).trim();
    }

    function sceneItems(scene) {
        scene = scene || {};
        const labels = {
            "time": "时间",
            "timeSlot": "时段",
            "season": "季节",
            "location": "地点",
            "weather": "天气",
            "atmosphere": "氛围",
            "characters": "在场",
            "timeDelta": "时间推进"
        };
        const keys = ["time", "timeSlot", "season", "location", "weather", "atmosphere", "characters", "timeDelta"];
        const items = [];
        for (let i = 0; i < keys.length; ++i) {
            const key = keys[i];
            const value = root.displayValue(scene[key]);
            if (value.length > 0) {
                items.push({
                    "key": key,
                    "label": labels[key],
                    "value": value
                });
            }
        }
        return items;
    }

    function metricDeltaText(metric) {
        metric = metric || {};
        if (metric.delta === undefined || metric.delta === null || String(metric.delta).trim().length === 0) {
            return "";
        }
        const delta = Number(metric.delta);
        if (Number.isFinite(delta)) {
            return delta >= 0 ? `+${delta}` : String(delta);
        }
        const text = String(metric.delta).trim();
        return text.charAt(0) === "+" || text.charAt(0) === "-" ? text : `+${text}`;
    }

    function metricText(metric) {
        metric = metric || {};
        const value = root.displayValue(metric.value);
        const maximum = root.displayValue(metric.maximum);
        const delta = root.metricDeltaText(metric);
        let result = value;
        if (maximum.length > 0) {
            result += `/${maximum}`;
        }
        if (delta.length > 0) {
            result += `（${delta}）`;
        }
        return result;
    }

    function characterMetricGroups(characters) {
        const groups = [];
        const source = characters || [];
        for (let i = 0; i < source.length; ++i) {
            const metrics = source[i].metrics || [];
            if (metrics.length > 0) {
                groups.push({
                    "name": source[i].name || "角色",
                    "metrics": metrics
                });
            }
        }
        return groups;
    }

    function stateRecordHasDetails(recordCard) {
        recordCard = recordCard || {};
        return String(recordCard.summary || "").trim().length > 0
            || (recordCard.characters || []).length > 0
            || (recordCard.metrics || []).length > 0
            || (recordCard.relationships || []).length > 0;
    }

    function retryStateRecord(messageId) {
        const result = FantarealBridge.retryDatabaseTurn(messageId || "");
        if (result.ok) {
            message.success(result.message || "状态记录已重新排队");
        } else {
            message.error(result.message || "状态记录重试失败", 5000);
        }
    }

    HusMessage {
        id: message
        z: 999
        width: root.width
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
    }

    Timer {
        id: bubbleRevealTimer
        interval: 420
        repeat: true
        onTriggered: {
            if (root.revealingPartCount >= root.revealingTotalParts) {
                root.finishAssistantReveal();
                return;
            }
            root.revealingPartCount += 1;
            Qt.callLater(messageList.positionViewAtEnd);
            if (root.revealingPartCount >= root.revealingTotalParts) {
                root.finishAssistantReveal();
                return;
            }
            root.scheduleNextBubbleReveal();
        }
    }

    Connections {
        target: FantarealBridge

        function onChatGenerationChanged() {
            if (root.generating) {
                Qt.callLater(messageList.positionViewAtEnd);
            }
        }

        function onChatGenerationFinished(result) {
            if (result.ok) {
                message.success(result.message);
                if (root.clearDraftOnGenerationFinished) {
                    root.draftMessage = "";
                    input.clear();
                }
                root.startAssistantReveal();
                Qt.callLater(messageList.positionViewAtEnd);
            } else {
                message.error(result.message, 5000);
                root.waitingForAssistantReveal = false;
                root.waitingAssistantMinIndex = -1;
            }
            root.clearDraftOnGenerationFinished = false;
        }
    }

    Component.onCompleted: Qt.callLater(() => input.forceActiveFocus())

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 4

        GlassCard {
            id: chatPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 0
            accentColor: Global.accentBlue
            cornerRadius: 22
            shadowAlphaDark: 0.10
            shadowAlphaLight: 0.08
            backgroundAlphaDark: 0.05
            backgroundAlphaLight: 0.12
            borderAlphaDark: 0.14
            borderAlphaLight: 0.18

            Rectangle {
                id: messageSurface
                anchors.fill: parent
                radius: 22
                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? Math.max(0.06, 0.12 - root.backgroundStrength * 0.06) : Math.max(0.16, 0.34 - root.backgroundStrength * 0.16))
                border.width: 1
                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.18)
                clip: true

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 1
                    radius: 21
                    color: "transparent"
                    border.width: 1
                    border.color: HusThemeFunctions.alpha("#ffffff", HusTheme.isDark ? 0.04 : 0.16)
                }

                Item {
                    id: emptyChatStage
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: composerSurface.top
                    anchors.margins: 22
                    visible: !root.hasMessages && !root.generating

                    Rectangle {
                        width: Math.min(parent.width, 1080)
                        height: Math.min(parent.height, Math.max(260, welcomeColumn.implicitHeight + 72))
                        anchors.centerIn: parent
                        radius: 24
                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? Math.max(0.12, 0.22 - root.backgroundStrength * 0.08) : Math.max(0.32, 0.56 - root.backgroundStrength * 0.20))
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.22)

                        ColumnLayout {
                            id: welcomeColumn
                            anchors.fill: parent
                            anchors.margins: 26
                            spacing: 0

                            HusText {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                text: root.openingText()
                                wrapMode: Text.Wrap
                                color: HusTheme.Primary.colorTextPrimary
                                font.pixelSize: root.width > 1180 ? 18 : 16
                                lineHeight: 1.24
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }

                ListView {
                    id: messageList
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    anchors.topMargin: 18
                    anchors.bottomMargin: composerSurface.height + 34
                    spacing: 16
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    maximumFlickVelocity: 9200
                    flickDeceleration: 1600
                    cacheBuffer: Math.max(0, height * 2)
                    model: FantarealBridge.chatMessages
                    visible: root.hasMessages || root.generating

                    delegate: Item {
                        id: messageDelegate
                        width: ListView.view.width
                        height: hiddenAssistant ? 0 : (systemMessage ? systemBubble.implicitHeight + 16 : Math.max(avatar.size, messageStack.implicitHeight) + 12)
                        visible: !hiddenAssistant

                        property bool userMessage: Boolean(modelData.isUser)
                        property bool systemMessage: Boolean(modelData.isSystem)
                        property bool hiddenAssistant: root.shouldHideAssistantUntilSplit(modelData)
                        property bool revealingMessage: modelData.message_id === root.revealingAssistantMessageId
                        property real bubbleMaxWidth: Math.min(width * 0.58, 780)
                        property real bubbleMinWidth: 52
                        property var stateRecord: modelData.stateRecord || ({})
                        property var stateTitleCard: stateRecord.titleCard || ({})
                        property var stateRecordCard: stateRecord.recordCard || ({})
                        property bool showStateRecord: !userMessage && !systemMessage && Boolean(modelData.stateRecord)

                        Behavior on height {
                            NumberAnimation {
                                duration: 180
                                easing.type: Easing.OutCubic
                            }
                        }

                        Text {
                            id: contentMeasure
                            visible: false
                            text: modelData.content
                            textFormat: Text.PlainText
                            font.pixelSize: 15
                        }

                        Rectangle {
                            id: systemBubble
                            visible: systemMessage
                            width: Math.min(parent.width * 0.62, Math.max(180, contentMeasure.implicitWidth + 34))
                            implicitHeight: systemText.implicitHeight + 18
                            anchors.horizontalCenter: parent.horizontalCenter
                            radius: 14
                            color: HusThemeFunctions.alpha(HusTheme.Primary.colorWarning, 0.13)
                            border.width: 1
                            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorWarning, 0.20)

                            HusText {
                                id: systemText
                                anchors.fill: parent
                                anchors.margins: 9
                                text: modelData.content
                                wrapMode: Text.Wrap
                                textFormat: Text.PlainText
                                horizontalAlignment: Text.AlignHCenter
                                color: HusTheme.Primary.colorTextSecondary
                                font.pixelSize: 13
                            }
                        }

                        HusAvatar {
                            id: avatar
                            visible: !systemMessage
                            size: 34
                            textSource: root.avatarText(modelData)
                            textSize: HusAvatar.Size_Auto
                            colorBg: userMessage ? Global.accentBlue : HusThemeFunctions.alpha(Global.accentViolet, 0.86)
                            colorText: "#ffffff"
                            x: userMessage ? parent.width - width : 0
                            y: 2
                        }

                        Column {
                            id: messageStack
                            visible: !systemMessage
                            spacing: 4
                            width: messageDelegate.bubbleMaxWidth
                            x: userMessage ? avatar.x - width - 10 : avatar.width + 10
                            y: 0

                            HusText {
                                width: parent.width
                                visible: !userMessage
                                text: root.roleName(modelData)
                                color: HusTheme.Primary.colorTextTertiary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                width: parent.width
                                visible: messageDelegate.showStateRecord
                                implicitHeight: stateTitleLayout.implicitHeight + 18
                                radius: 10
                                color: HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.18 : 0.10)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.24)

                                ColumnLayout {
                                    id: stateTitleLayout
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    spacing: 5

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        HusText {
                                            Layout.fillWidth: true
                                            text: messageDelegate.stateTitleCard.title || "本轮状态"
                                            color: HusTheme.Primary.colorTextPrimary
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                            elide: Text.ElideRight
                                        }

                                        HusTag {
                                            text: root.stateRecordStatusText(messageDelegate.stateRecord)
                                            tagState: root.stateRecordStatusState(messageDelegate.stateRecord)
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: String(messageDelegate.stateTitleCard.subtitle || "").trim().length > 0
                                        text: messageDelegate.stateTitleCard.subtitle || ""
                                        wrapMode: Text.Wrap
                                        color: HusTheme.Primary.colorTextSecondary
                                        font.pixelSize: 12
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        visible: root.sceneItems(messageDelegate.stateTitleCard.scene || {}).length > 0
                                        columns: width >= 520 ? 2 : 1
                                        columnSpacing: 6
                                        rowSpacing: 6

                                        Repeater {
                                            model: root.sceneItems(messageDelegate.stateTitleCard.scene || {})

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: sceneItemRow.implicitHeight + 10
                                                radius: 6
                                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.48)
                                                border.width: 1
                                                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.14)

                                                RowLayout {
                                                    id: sceneItemRow
                                                    anchors.fill: parent
                                                    anchors.margins: 5
                                                    spacing: 7

                                                    HusText {
                                                        Layout.preferredWidth: 54
                                                        text: modelData.label
                                                        color: Global.accentBlue
                                                        font.pixelSize: 11
                                                        font.weight: Font.DemiBold
                                                    }

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        text: modelData.value
                                                        wrapMode: Text.Wrap
                                                        color: HusTheme.Primary.colorTextSecondary
                                                        font.pixelSize: 12
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: String((messageDelegate.stateTitleCard.scene || {}).eventSummary || "").trim().length > 0
                                        text: (messageDelegate.stateTitleCard.scene || {}).eventSummary || ""
                                        wrapMode: Text.Wrap
                                        color: HusTheme.Primary.colorTextSecondary
                                        font.pixelSize: 12
                                        lineHeight: 1.18
                                    }
                                }
                            }

                            Repeater {
                                model: root.partsForMessage(modelData)

                                delegate: Item {
                                    width: messageStack.width
                                    implicitHeight: hiddenPart ? 0 : bubble.implicitHeight
                                    opacity: hiddenPart ? 0 : 1
                                    clip: true

                                    property bool loadingPart: messageDelegate.revealingMessage
                                        && !userMessage
                                        && index === root.revealingPartCount
                                        && index < root.revealingTotalParts
                                    property bool hiddenPart: messageDelegate.revealingMessage
                                        && !userMessage
                                        && index > root.revealingPartCount
                                    property string partText: String(modelData)
                                    property real partWidth: Math.min(messageDelegate.bubbleMaxWidth, Math.max(messageDelegate.bubbleMinWidth, partMeasure.implicitWidth + 30))

                                    Behavior on implicitHeight {
                                        NumberAnimation {
                                            duration: 180
                                            easing.type: Easing.OutCubic
                                        }
                                    }

                                    Behavior on opacity {
                                        NumberAnimation {
                                            duration: 150
                                            easing.type: Easing.OutCubic
                                        }
                                    }

                                    Text {
                                        id: partMeasure
                                        visible: false
                                        text: partText
                                        textFormat: Text.PlainText
                                        font.pixelSize: 15
                                    }

                                    Rectangle {
                                        id: bubble
                                        width: partWidth
                                        x: userMessage ? parent.width - width : 0
                                        implicitHeight: bubbleText.implicitHeight + 22
                                        radius: 16
                                        color: userMessage ? HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.42 : 0.28) : HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.30 : 0.64)
                                        border.width: 1
                                        border.color: HusThemeFunctions.alpha(userMessage ? Global.accentBlue : HusTheme.Primary.colorBorder, 0.24)

                                        HusText {
                                            id: bubbleText
                                            anchors.fill: parent
                                            anchors.leftMargin: 14
                                            anchors.rightMargin: 14
                                            anchors.topMargin: 10
                                            anchors.bottomMargin: 10
                                            text: partText
                                            wrapMode: Text.Wrap
                                            color: HusTheme.Primary.colorTextPrimary
                                            opacity: loadingPart ? 0.0 : 1.0
                                            textFormat: Text.PlainText
                                            font.pixelSize: 15
                                            lineHeight: 1.22

                                            Behavior on opacity {
                                                NumberAnimation {
                                                    duration: 220
                                                    easing.type: Easing.OutCubic
                                                }
                                            }
                                        }

                                        HusText {
                                            id: loadingText
                                            anchors.fill: parent
                                            anchors.leftMargin: 14
                                            anchors.rightMargin: 14
                                            anchors.topMargin: 10
                                            anchors.bottomMargin: 10
                                            text: root.loadingBubbleText
                                            wrapMode: Text.NoWrap
                                            color: HusTheme.Primary.colorTextTertiary
                                            opacity: loadingPart ? 0.70 : 0.0
                                            textFormat: Text.PlainText
                                            font.pixelSize: 15
                                            lineHeight: 1.22

                                            Behavior on opacity {
                                                NumberAnimation {
                                                    duration: 180
                                                    easing.type: Easing.OutCubic
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                visible: messageDelegate.showStateRecord
                                implicitHeight: stateRecordLayout.implicitHeight + 18
                                radius: 10
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.22 : 0.58)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(Global.accentViolet, 0.22)

                                ColumnLayout {
                                    id: stateRecordLayout
                                    anchors.fill: parent
                                    anchors.margins: 9
                                    spacing: 7

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        HusText {
                                            Layout.fillWidth: true
                                            text: "状态记录"
                                            color: HusTheme.Primary.colorTextPrimary
                                            font.pixelSize: 14
                                            font.weight: Font.DemiBold
                                        }

                                        HusButton {
                                            text: "重试"
                                            type: HusButton.Type_Outlined
                                            visible: Boolean(messageDelegate.stateRecord.canRetry)
                                            onClicked: root.retryStateRecord(modelData.message_id)
                                        }
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: String(messageDelegate.stateRecordCard.summary || "").trim().length > 0
                                        text: messageDelegate.stateRecordCard.summary
                                        wrapMode: Text.Wrap
                                        color: HusTheme.Primary.colorTextSecondary
                                        font.pixelSize: 13
                                        lineHeight: 1.18
                                    }

                                    HusText {
                                        Layout.fillWidth: true
                                        visible: !root.stateRecordHasDetails(messageDelegate.stateRecordCard)
                                        text: ((messageDelegate.stateRecord.error || {}).message)
                                            || (messageDelegate.stateRecord.status === "pending" ? "DatabaseWorker 正在生成状态记录。" : "暂无状态记录内容。")
                                        wrapMode: Text.Wrap
                                        color: messageDelegate.stateRecord.status === "error"
                                            ? HusTheme.Primary.colorError
                                            : HusTheme.Primary.colorTextTertiary
                                        font.pixelSize: 12
                                    }

                                    Repeater {
                                        model: messageDelegate.stateRecordCard.characters || []

                                        delegate: Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: characterColumn.implicitHeight + 12
                                            radius: 8
                                            color: HusThemeFunctions.alpha(Global.accentViolet, HusTheme.isDark ? 0.11 : 0.08)
                                            border.width: 1
                                            border.color: HusThemeFunctions.alpha(Global.accentViolet, 0.16)

                                            ColumnLayout {
                                                id: characterColumn
                                                anchors.fill: parent
                                                anchors.margins: 6
                                                spacing: 4

                                                HusText {
                                                    Layout.fillWidth: true
                                                    text: modelData.name || "角色"
                                                    color: HusTheme.Primary.colorTextPrimary
                                                    font.pixelSize: 13
                                                    font.weight: Font.DemiBold
                                                    elide: Text.ElideRight
                                                }

                                                Repeater {
                                                    model: modelData.fields || []

                                                    delegate: Rectangle {
                                                        Layout.fillWidth: true
                                                        implicitHeight: characterFieldRow.implicitHeight + 10
                                                        radius: 6
                                                        color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.44)
                                                        border.width: 1
                                                        border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.16)

                                                        RowLayout {
                                                            id: characterFieldRow
                                                            anchors.fill: parent
                                                            anchors.margins: 5
                                                            spacing: 8

                                                            HusText {
                                                                Layout.preferredWidth: 78
                                                                text: modelData.label || modelData.key || "字段"
                                                                wrapMode: Text.Wrap
                                                                color: Global.accentBlue
                                                                font.pixelSize: 11
                                                                font.weight: Font.DemiBold
                                                            }

                                                            HusText {
                                                                Layout.fillWidth: true
                                                                text: root.displayValue(modelData.value)
                                                                wrapMode: Text.Wrap
                                                                color: HusTheme.Primary.colorTextSecondary
                                                                font.pixelSize: 12
                                                                lineHeight: 1.18
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        visible: root.characterMetricGroups(messageDelegate.stateRecordCard.characters || []).length > 0
                                            || (messageDelegate.stateRecordCard.metrics || []).length > 0
                                        spacing: 6

                                        HusText {
                                            Layout.fillWidth: true
                                            text: "本轮数值变化"
                                            color: HusTheme.Primary.colorTextPrimary
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                        }

                                        Repeater {
                                            model: root.characterMetricGroups(messageDelegate.stateRecordCard.characters || [])

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: characterMetricColumn.implicitHeight + 12
                                                radius: 8
                                                color: HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.08 : 0.06)
                                                border.width: 1
                                                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.14)

                                                ColumnLayout {
                                                    id: characterMetricColumn
                                                    anchors.fill: parent
                                                    anchors.margins: 6
                                                    spacing: 4

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        text: modelData.name || "角色"
                                                        color: HusTheme.Primary.colorTextPrimary
                                                        font.pixelSize: 12
                                                        font.weight: Font.DemiBold
                                                    }

                                                    Repeater {
                                                        model: modelData.metrics || []

                                                        delegate: ColumnLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 1

                                                            RowLayout {
                                                                Layout.fillWidth: true
                                                                spacing: 8

                                                                HusText {
                                                                    Layout.fillWidth: true
                                                                    text: modelData.label || modelData.key || "数值"
                                                                    color: HusTheme.Primary.colorTextSecondary
                                                                    font.pixelSize: 12
                                                                }

                                                                HusText {
                                                                    text: root.metricText(modelData)
                                                                    color: root.metricDeltaText(modelData).charAt(0) === "-"
                                                                        ? HusTheme.Primary.colorError
                                                                        : Global.accentBlue
                                                                    font.pixelSize: 12
                                                                    font.weight: Font.DemiBold
                                                                }
                                                            }

                                                            HusText {
                                                                Layout.fillWidth: true
                                                                visible: String(modelData.reason || "").trim().length > 0
                                                                text: modelData.reason || ""
                                                                wrapMode: Text.Wrap
                                                                color: HusTheme.Primary.colorTextTertiary
                                                                font.pixelSize: 11
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        Repeater {
                                            model: messageDelegate.stateRecordCard.metrics || []

                                            delegate: ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 1

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 8

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        text: modelData.label || modelData.key || "数值"
                                                        color: HusTheme.Primary.colorTextSecondary
                                                        font.pixelSize: 12
                                                    }

                                                    HusText {
                                                        text: root.metricText(modelData)
                                                        color: root.metricDeltaText(modelData).charAt(0) === "-"
                                                            ? HusTheme.Primary.colorError
                                                            : Global.accentBlue
                                                        font.pixelSize: 12
                                                        font.weight: Font.DemiBold
                                                    }
                                                }

                                                HusText {
                                                    Layout.fillWidth: true
                                                    visible: String(modelData.reason || "").trim().length > 0
                                                    text: modelData.reason || ""
                                                    wrapMode: Text.Wrap
                                                    color: HusTheme.Primary.colorTextTertiary
                                                    font.pixelSize: 11
                                                }
                                            }
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        visible: (messageDelegate.stateRecordCard.relationships || []).length > 0
                                        spacing: 6

                                        HusText {
                                            Layout.fillWidth: true
                                            text: "关系与阶段变化"
                                            color: HusTheme.Primary.colorTextPrimary
                                            font.pixelSize: 13
                                            font.weight: Font.DemiBold
                                        }

                                        Repeater {
                                            model: messageDelegate.stateRecordCard.relationships || []

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: relationshipColumn.implicitHeight + 12
                                                radius: 8
                                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.14 : 0.44)
                                                border.width: 1
                                                border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.16)

                                                ColumnLayout {
                                                    id: relationshipColumn
                                                    anchors.fill: parent
                                                    anchors.margins: 6
                                                    spacing: 3

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 8

                                                        HusText {
                                                            Layout.fillWidth: true
                                                            text: modelData.pair || "关系"
                                                            color: HusTheme.Primary.colorTextPrimary
                                                            font.pixelSize: 12
                                                            font.weight: Font.DemiBold
                                                            wrapMode: Text.Wrap
                                                        }

                                                        HusTag {
                                                            visible: String(modelData.stage || "").trim().length > 0
                                                            text: modelData.stage || ""
                                                            tagState: HusTag.State_Processing
                                                        }
                                                    }

                                                    HusText {
                                                        Layout.fillWidth: true
                                                        visible: String(modelData.change || "").trim().length > 0
                                                        text: modelData.change || ""
                                                        wrapMode: Text.Wrap
                                                        color: HusTheme.Primary.colorTextSecondary
                                                        font.pixelSize: 12
                                                        lineHeight: 1.18
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ScrollBar.vertical: HusScrollBar {}

                    footer: Item {
                        id: streamingFooter
                        width: messageList.width
                        height: root.generating && !root.memoryOrganizing ? Math.max(streamingAvatar.size, streamingStack.implicitHeight) + 20 : 0
                        visible: root.generating && !root.memoryOrganizing

                        property string streamingContent: FantarealBridge.chatStreamingPreview.trim().length > 0 ? FantarealBridge.chatStreamingPreview : root.loadingBubbleText
                        property real streamingMaxWidth: Math.min(width * 0.58, 780)
                        property real streamingWidth: Math.min(streamingMaxWidth, Math.max(96, streamingMeasure.implicitWidth + 30))

                        Text {
                            id: streamingMeasure
                            visible: false
                            text: streamingFooter.streamingContent
                            textFormat: Text.PlainText
                            font.pixelSize: 15
                        }

                        HusAvatar {
                            id: streamingAvatar
                            size: 34
                            textSource: root.activeRoleName().trim().length > 0 ? root.activeRoleName().charAt(0) : "F"
                            textSize: HusAvatar.Size_Auto
                            colorBg: HusThemeFunctions.alpha(Global.accentViolet, 0.86)
                            colorText: "#ffffff"
                            x: 0
                            y: 2
                        }

                        Column {
                            id: streamingStack
                            spacing: 4
                            width: streamingBubble.width
                            x: streamingAvatar.width + 10
                            y: 0

                            HusText {
                                width: parent.width
                                text: root.activeRoleName()
                                color: HusTheme.Primary.colorTextTertiary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                id: streamingBubble
                                width: streamingFooter.streamingWidth
                                implicitHeight: streamingBubbleText.implicitHeight + 22
                                radius: 16
                                color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.30 : 0.64)
                                border.width: 1
                                border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.24)

                                HusText {
                                    id: streamingBubbleText
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 14
                                    anchors.topMargin: 10
                                    anchors.bottomMargin: 10
                                    text: streamingFooter.streamingContent
                                    wrapMode: Text.Wrap
                                    color: HusTheme.Primary.colorTextPrimary
                                    textFormat: Text.PlainText
                                    font.pixelSize: 15
                                    lineHeight: 1.22
                                }
                            }
                        }
                    }

                    onCountChanged: Qt.callLater(positionViewAtEnd)
                    Component.onCompleted: Qt.callLater(positionViewAtEnd)
                }

                SmoothWheelArea {
                    anchors.fill: messageList
                    target: messageList
                }

                Rectangle {
                    id: composerSurface
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 12
                    height: root.height > 760 ? 122 : 112
                    radius: 18
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, root.composerGlassAlpha)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.16 : 0.12)

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 6

                        HusTextArea {
                            id: input
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.minimumHeight: 50
                            placeholderText: "输入消息。"
                            minRows: 2
                            maxRows: 4
                            maxLength: 12000
                            autoSize: false
                            text: root.draftMessage
                            colorBg: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, root.inputGlassAlpha)
                            colorBorder: HusThemeFunctions.alpha(Global.accentBlue, active ? 0.26 : 0.10)
                            colorPlaceholderText: HusThemeFunctions.alpha(HusTheme.Primary.colorTextBase, HusTheme.isDark ? 0.34 : 0.36)
                            textArea.Keys.priority: Keys.BeforeItem
                            textArea.Keys.onReturnPressed: event => root.handleInputReturn(event)
                            textArea.Keys.onEnterPressed: event => root.handleInputReturn(event)
                            onTextChanged: root.draftMessage = text
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Item {
                                Layout.fillWidth: true
                            }

                            HusButton {
                                Layout.preferredWidth: 92
                                Layout.preferredHeight: 32
                                text: "重新回复"
                                type: HusButton.Type_Outlined
                                enabled: root.hasMessages && !root.generating
                                onClicked: root.retryLastReply()
                            }

                            HusButton {
                                Layout.preferredWidth: 104
                                Layout.preferredHeight: 32
                                text: "结束对话"
                                type: HusButton.Type_Primary
                                enabled: root.hasMessages && !root.generating
                                onClicked: root.endConversation()
                            }
                        }
                    }
                }
            }
        }
    }
}
