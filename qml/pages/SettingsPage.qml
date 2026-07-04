import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import HuskarUI.Basic
import Fantareal

Item {
    id: root

    property bool initialized: false
    property bool dirty: false
    property string llmBaseUrl: ""
    property string llmApiKey: ""
    property string llmModel: ""
    property string themeName: ""
    property real temperature: 0.85
    property int historyLimit: 20
    property int requestTimeout: 120
    property bool demoMode: false
    property bool outputSplittingEnabled: true
    property string backgroundImagePath: ""
    property real backgroundImageOpacity: 0.42
    property string embeddingBaseUrl: ""
    property string embeddingApiKey: ""
    property string embeddingModel: ""
    property int retrievalTopK: 4
    property bool rerankEnabled: false
    property string rerankBaseUrl: ""
    property string rerankApiKey: ""
    property string rerankModel: ""
    property int rerankTopN: 3
    property string memorySummaryLength: ""
    property int memorySummaryMaxChars: 520

    function markDirty() {
        if (initialized) {
            dirty = true;
        }
    }

    function applyDraft(draft) {
        initialized = false;
        llmBaseUrl = draft.llm_base_url || "";
        llmApiKey = "";
        llmModel = draft.llm_model || "";
        themeName = draft.theme || "";
        temperature = Number(draft.temperature || 0.85);
        historyLimit = Number(draft.history_limit || 20);
        requestTimeout = Number(draft.request_timeout || 120);
        demoMode = Boolean(draft.demo_mode);
        outputSplittingEnabled = draft.output_splitting_enabled === undefined ? true : Boolean(draft.output_splitting_enabled);
        backgroundImagePath = draft.background_image_path || "";
        backgroundImageOpacity = draft.background_image_opacity === undefined ? 0.42 : Number(draft.background_image_opacity);
        embeddingBaseUrl = draft.embedding_base_url || "";
        embeddingApiKey = "";
        embeddingModel = draft.embedding_model || "";
        retrievalTopK = Number(draft.retrieval_top_k || 4);
        rerankEnabled = Boolean(draft.rerank_enabled);
        rerankBaseUrl = draft.rerank_base_url || "";
        rerankApiKey = "";
        rerankModel = draft.rerank_model || "";
        rerankTopN = Number(draft.rerank_top_n || 3);
        memorySummaryLength = draft.memory_summary_length || "";
        memorySummaryMaxChars = Number(draft.memory_summary_max_chars || 520);
        dirty = false;
        initialized = true;
    }

    function saveDraft() {
        const result = FantarealBridge.saveSettingsDraft({
            "llm_base_url": llmBaseUrl,
            "llm_api_key": llmApiKey,
            "llm_model": llmModel,
            "theme": themeName,
            "temperature": temperature,
            "history_limit": historyLimit,
            "request_timeout": requestTimeout,
            "demo_mode": demoMode,
            "output_splitting_enabled": outputSplittingEnabled,
            "background_image_path": backgroundImagePath,
            "background_image_opacity": backgroundImageOpacity,
            "embedding_base_url": embeddingBaseUrl,
            "embedding_api_key": embeddingApiKey,
            "embedding_model": embeddingModel,
            "retrieval_top_k": retrievalTopK,
            "rerank_enabled": rerankEnabled,
            "rerank_base_url": rerankBaseUrl,
            "rerank_api_key": rerankApiKey,
            "rerank_model": rerankModel,
            "rerank_top_n": rerankTopN,
            "memory_summary_length": memorySummaryLength,
            "memory_summary_max_chars": memorySummaryMaxChars
        });
        if (result.ok) {
            message.success(result.message);
            applyDraft(FantarealBridge.settingsDraft);
        } else {
            message.error(result.message, 5000);
        }
    }

    function previewBackgroundOpacity(value) {
        const normalized = Math.max(0, Math.min(1, Number(value)));
        root.backgroundImageOpacity = normalized;
        root.markDirty();
        FantarealBridge.previewBackgroundImageOpacity(normalized);
    }

    function restoreDraft() {
        root.applyDraft(FantarealBridge.settingsDraft);
        FantarealBridge.previewBackgroundImageOpacity(root.backgroundImageOpacity);
    }

    function setBackgroundAndSave(path) {
        root.backgroundImagePath = path;
        root.markDirty();
        root.saveDraft();
    }

    Component.onCompleted: applyDraft(FantarealBridge.settingsDraft)

    FileDialog {
        id: backgroundFileDialog
        title: "选择背景图片"
        nameFilters: ["图片文件 (*.png *.jpg *.jpeg *.webp *.bmp)", "所有文件 (*)"]
        onAccepted: root.setBackgroundAndSave(selectedFile.toString())
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (!root.dirty) {
                root.applyDraft(FantarealBridge.settingsDraft);
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
                    text: "设置"
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
                    type: HusButton.Type_Default
                    onClicked: FantarealBridge.refreshLegacyScan()
                }

                HusButton {
                    text: "还原"
                    enabled: root.dirty
                    onClicked: root.restoreDraft()
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
                accentColor: Global.accentBlue

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
                            text: "模型连接"
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusTag {
                            text: FantarealBridge.settingsDraft.llm_api_key_configured ? "LLM Key 已配置" : "LLM Key 未配置"
                            tagState: FantarealBridge.settingsDraft.llm_api_key_configured ? HusTag.State_Success : HusTag.State_Warning
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: apiNotice.implicitHeight + 22
                        radius: 14
                        color: HusThemeFunctions.alpha(Global.accentGold, HusTheme.isDark ? 0.14 : 0.18)
                        border.width: 1
                        border.color: HusThemeFunctions.alpha(Global.accentGold, 0.36)

                        HusText {
                            id: apiNotice
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            text: "第三方 API 提示：发送消息时，聊天内容、角色卡、世界书、记忆片段或 Prompt 可能会发送至对应上游服务商。Fantareal 不托管、不中转、不管理该服务，请自行确认其服务条款、隐私政策、计费规则和可用性。"
                            color: HusTheme.Primary.colorTextBase
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "LLM Base URL"
                            description: "OpenAI 兼容接口地址；可填根域名，聊天会自动调用 /v1/chat/completions。"

                            HusInput {
                                width: parent.width
                                text: root.llmBaseUrl
                                placeholderText: "https://api.example.com 或 https://api.example.com/v1"
                                clearEnabled: "active"
                                iconSource: HusIcon.ApiOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.llmBaseUrl = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "LLM Model"
                            description: "用于聊天生成的模型 ID，例如 grok-4.3。"

                            HusInput {
                                width: parent.width
                                text: root.llmModel
                                placeholderText: "grok-4.3"
                                clearEnabled: "active"
                                iconSource: HusIcon.RobotOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.llmModel = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "LLM API Key"
                            description: "留空则保留当前密钥，不会从本地文件回显明文。"

                            HusInput {
                                width: parent.width
                                text: root.llmApiKey
                                placeholderText: FantarealBridge.settingsDraft.llm_api_key_configured ? "已配置，输入新值以覆盖" : "未配置"
                                echoMode: HusInput.Password
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.llmApiKey = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Theme"
                            description: "保存时归一为 dark 或 light。"

                            HusInput {
                                width: parent.width
                                text: root.themeName
                                placeholderText: "dark / light"
                                clearEnabled: "active"
                                iconSource: HusIcon.SkinOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.themeName = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "背景图片"
                            description: "选择本地图片作为背景。"

                            RowLayout {
                                width: parent.width
                                spacing: 8

                                HusInput {
                                    Layout.fillWidth: true
                                    text: root.backgroundImagePath
                                    placeholderText: "E:/Pictures/fantareal-bg.png"
                                    clearEnabled: "active"
                                    iconSource: HusIcon.FolderOpenOutlined
                                    iconPosition: HusInput.Position_Left
                                    onTextEdited: {
                                        root.backgroundImagePath = text;
                                        root.markDirty();
                                    }
                                }

                                HusButton {
                                    text: "选择"
                                    type: HusButton.Type_Primary
                                    onClicked: backgroundFileDialog.open()
                                }

                                HusButton {
                                    text: "清除"
                                    type: HusButton.Type_Outlined
                                    onClicked: root.setBackgroundAndSave("")
                                }
                            }
                        }

                        SettingField {
                            title: "背景显示强度"
                            description: "0% 保留雾面遮罩，100% 让图片最清晰；拖动会立即预览。"

                            ColumnLayout {
                                width: parent.width
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 12

                                    HusSlider {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 32
                                        min: 0
                                        max: 100
                                        stepSize: 5
                                        snapMode: HusSlider.SnapAlways
                                        value: root.backgroundImageOpacity * 100
                                        contentDescription: "背景显示强度"
                                        onFirstMoved: root.previewBackgroundOpacity(currentValue / 100)
                                        onFirstReleased: root.saveDraft()
                                    }

                                    HusText {
                                        Layout.preferredWidth: 54
                                        text: Math.round(root.backgroundImageOpacity * 100) + "%"
                                        horizontalAlignment: Text.AlignRight
                                        font.pixelSize: 15
                                        color: HusTheme.Primary.colorTextSecondary
                                    }
                                }

                                HusInputNumber {
                                    Layout.fillWidth: true
                                    value: root.backgroundImageOpacity
                                    min: 0
                                    max: 1
                                    step: 0.05
                                    precision: 2
                                    formatter: value => Math.round(value * 100) + "%"
                                    parser: text => text.replace("%", "") / 100
                                    onValueModified: {
                                        root.previewBackgroundOpacity(value);
                                    }
                                }
                            }
                        }

                        SettingField {
                            title: "Temperature"
                            description: "保存时夹取到 0-2。"

                            HusInputNumber {
                                width: parent.width
                                value: root.temperature
                                min: 0
                                max: 2
                                step: 0.05
                                precision: 2
                                onValueModified: {
                                    root.temperature = value;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "历史轮数"
                            description: "保存时夹取到 1-100。"

                            HusInputNumber {
                                width: parent.width
                                value: root.historyLimit
                                min: 1
                                max: 100
                                step: 1
                                precision: 0
                                onValueModified: {
                                    root.historyLimit = Math.round(value);
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "请求超时"
                            description: "单位秒，保存时夹取到 10-600。"

                            HusInputNumber {
                                width: parent.width
                                value: root.requestTimeout
                                min: 10
                                max: 600
                                step: 5
                                precision: 0
                                suffix: "s"
                                onValueModified: {
                                    root.requestTimeout = Math.round(value);
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "本地演示回复"
                            description: "未配置模型时允许聊天页生成本地演示回复，便于离线验收。"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusSwitch {
                                    checked: root.demoMode
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.demoMode = checked;
                                        root.markDirty();
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.demoMode ? "发送并生成可回落到本地演示" : "严格要求真实模型配置"
                                    color: HusTheme.Primary.colorTextSecondary
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        SettingField {
                            title: "输出气泡切分"
                            description: "开启后，模型回复会先交给后处理子代理拆成多个聊天气泡；关闭则按原文单气泡显示。"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusSwitch {
                                    checked: root.outputSplittingEnabled
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.outputSplittingEnabled = checked;
                                        root.markDirty();
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.outputSplittingEnabled ? "多段回复会分泡展示" : "关闭子代理，仅显示原文"
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

                    HusText {
                        Layout.fillWidth: true
                        text: "检索与记忆"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        color: HusTheme.Primary.colorTextPrimary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 18
                        rowSpacing: 18

                        SettingField {
                            title: "Embedding Base URL"
                            description: "向量检索接口地址。"

                            HusInput {
                                width: parent.width
                                text: root.embeddingBaseUrl
                                clearEnabled: "active"
                                iconSource: HusIcon.ClusterOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.embeddingBaseUrl = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Embedding Model"
                            description: "向量模型名。"

                            HusInput {
                                width: parent.width
                                text: root.embeddingModel
                                clearEnabled: "active"
                                iconSource: HusIcon.DatabaseOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.embeddingModel = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Embedding API Key"
                            description: "留空保留当前密钥。"

                            HusInput {
                                width: parent.width
                                text: root.embeddingApiKey
                                placeholderText: FantarealBridge.settingsDraft.embedding_api_key_configured ? "已配置，输入新值以覆盖" : "未配置"
                                echoMode: HusInput.Password
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.embeddingApiKey = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Retrieval Top K"
                            description: "保存时夹取到 1-12。"

                            HusInputNumber {
                                width: parent.width
                                value: root.retrievalTopK
                                min: 1
                                max: 12
                                step: 1
                                precision: 0
                                onValueModified: {
                                    root.retrievalTopK = Math.round(value);
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Rerank"
                            description: "控制重排链路是否启用。"

                            RowLayout {
                                width: parent.width
                                spacing: 10

                                HusSwitch {
                                    checked: root.rerankEnabled
                                    checkedText: "开启"
                                    uncheckedText: "关闭"
                                    onToggled: {
                                        root.rerankEnabled = checked;
                                        root.markDirty();
                                    }
                                }

                                HusText {
                                    Layout.fillWidth: true
                                    text: root.rerankEnabled ? "已启用重排" : "未启用重排"
                                    color: HusTheme.Primary.colorTextSecondary
                                }
                            }
                        }

                        SettingField {
                            title: "Rerank Base URL"
                            description: "重排接口地址。"

                            HusInput {
                                width: parent.width
                                text: root.rerankBaseUrl
                                clearEnabled: "active"
                                iconSource: HusIcon.NodeIndexOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.rerankBaseUrl = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Rerank Model"
                            description: "重排模型名。"

                            HusInput {
                                width: parent.width
                                text: root.rerankModel
                                clearEnabled: "active"
                                iconSource: HusIcon.PartitionOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.rerankModel = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Rerank API Key"
                            description: "留空保留当前密钥。"

                            HusInput {
                                width: parent.width
                                text: root.rerankApiKey
                                placeholderText: FantarealBridge.settingsDraft.rerank_api_key_configured ? "已配置，输入新值以覆盖" : "未配置"
                                echoMode: HusInput.Password
                                clearEnabled: "active"
                                iconSource: HusIcon.KeyOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.rerankApiKey = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "Rerank Top N"
                            description: "保存时夹取到 1-12。"

                            HusInputNumber {
                                width: parent.width
                                value: root.rerankTopN
                                min: 1
                                max: 12
                                step: 1
                                precision: 0
                                onValueModified: {
                                    root.rerankTopN = Math.round(value);
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "记忆摘要长度"
                            description: "保存时归一为 short / medium / long / custom。"

                            HusInput {
                                width: parent.width
                                text: root.memorySummaryLength
                                clearEnabled: "active"
                                iconSource: HusIcon.FileTextOutlined
                                iconPosition: HusInput.Position_Left
                                onTextEdited: {
                                    root.memorySummaryLength = text;
                                    root.markDirty();
                                }
                            }
                        }

                        SettingField {
                            title: "记忆摘要字符数"
                            description: "保存时夹取到 80-2000。"

                            HusInputNumber {
                                width: parent.width
                                value: root.memorySummaryMaxChars
                                min: 80
                                max: 2000
                                step: 20
                                precision: 0
                                onValueModified: {
                                    root.memorySummaryMaxChars = Math.round(value);
                                    root.markDirty();
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
