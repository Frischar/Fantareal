import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

HusModal {
    id: root

    property real windowWidth: 1000
    property real windowHeight: 700
    property string ageGroup: ""
    property string errorMessage: ""
    property bool localConfirmed: false
    property bool apiConfirmed: false
    property bool legalConfirmed: false
    property string typedConfirmation: ""
    readonly property bool allConfirmed: localConfirmed && apiConfirmed && legalConfirmed
    readonly property bool typedConfirmationMatches: normalizedConfirmation(typedConfirmation) === normalizedConfirmation(FantarealBridge.firstLaunchConfirmationText)
    readonly property bool canContinue: ageGroup.length > 0 && allConfirmed && typedConfirmationMatches

    width: Math.min(Math.max(720, windowWidth - 120), 900)
    height: Math.min(Math.max(620, windowHeight - 90), 760)
    modal: true
    closable: false
    maskClosable: false
    position: HusModal.Position_Center
    colorOverlay: HusThemeFunctions.alpha("#000000", HusTheme.isDark ? 0.72 : 0.48)
    footerDelegate: null

    Component.onCompleted: {
        if (FantarealBridge.firstLaunchDisclaimerRequired) {
            open();
        }
    }

    Connections {
        target: FantarealBridge
        function onScanChanged() {
            if (FantarealBridge.firstLaunchDisclaimerRequired && !root.visible) {
                root.open();
            }
        }
    }

    function acceptDisclaimer() {
        const result = FantarealBridge.acceptFirstLaunchDisclaimer(root.ageGroup, root.typedConfirmation);
        if (result.ok) {
            root.close();
        } else {
            root.errorMessage = result.message;
        }
    }

    function normalizedConfirmation(value) {
        return String(value).replace(/[\s,，、.。．]+/g, "");
    }

    contentDelegate: Item {
        height: root.height

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 26
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                HusText {
                    Layout.fillWidth: true
                    text: "首次使用说明与本地服务边界确认"
                    font.pixelSize: 24
                    font.weight: Font.DemiBold
                    color: HusTheme.Primary.colorTextPrimary
                    wrapMode: Text.Wrap
                }

                HusTag {
                    text: FantarealBridge.firstLaunchDisclaimerVersion
                    tagState: HusTag.State_Processing
                }
            }

            Flickable {
                id: bodyScroller
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                contentWidth: width
                contentHeight: bodyColumn.implicitHeight

                ColumnLayout {
                    id: bodyColumn
                    width: bodyScroller.width
                    spacing: 16

                    HusText {
                        Layout.fillWidth: true
                        text: "欢迎使用 Fantareal。\n\nFantareal 是一个本地部署的开源 AI 角色创作框架与工具库，主要用于管理角色卡、世界书、记忆、Prompt、预设和本地运行环境。\n\nFantareal 制作组不提供官方在线聊天服务、模型服务、API 中转服务、账号服务、云端角色陪伴服务，也不托管用户聊天记录、角色卡、世界书、记忆或 API Key。\n\n如你在 Fantareal 中配置第三方 LLM API、Embedding API、Rerank API 或其他云端接口，相关请求可能会从你的本地环境发送至对应上游服务商。该等服务的内容生成、数据处理、可用性、计费规则、隐私政策和合规要求，由你与对应上游服务商自行确认，Fantareal 制作组不参与、不控制、不管理。\n\n请勿将 Fantareal 用于违法违规、侵权、诱导沉迷、诱导情感依赖、套取隐私信息、冒充真实自然人，或替代现实人际关系、医疗、心理、法律、金融等专业服务的用途。\n\n如果你基于 Fantareal 进行二次开发、公开部署、商业运营、API 中转、云端同步、角色市场、账号系统或面向公众的拟人化互动服务，应由实际部署者、运营者或服务提供者自行承担相应的内容安全、数据保护、未成年人保护、安全评估、算法备案等合规责任。"
                        color: HusTheme.Primary.colorTextBase
                        font.pixelSize: 14
                        lineHeight: 1.35
                        wrapMode: Text.Wrap
                    }

                    HusDivider {}

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        HusText {
                            text: "请选择你的年龄段"
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusRadioBlock {
                            id: ageRadio
                            Layout.fillWidth: true
                            type: HusRadioBlock.Type_Outlined
                            model: [
                                { label: "未满 14 周岁", value: "under_14" },
                                { label: "14-17 周岁", value: "14_to_17" },
                                { label: "18 周岁及以上", value: "18_plus" }
                            ]
                            onClicked: (index, radioData) => {
                                root.ageGroup = radioData.value;
                                root.errorMessage = "";
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            visible: root.ageGroup === "under_14" || root.ageGroup === "14_to_17"
                            text: "已为当前用户开启更保守的使用模式。Fantareal 是本地创作工具，请在合理时间内使用，并避免将 AI 角色作为现实关系或专业服务的替代。"
                            color: HusTheme.Primary.colorWarning
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                    }

                    HusDivider {}

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            text: "确认项"
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                        }

                        HusCheckBox {
                            id: localCheck
                            Layout.fillWidth: true
                            text: "我理解 Fantareal 是本地开源框架与工具库，不是官方在线聊天服务。"
                            onToggled: {
                                root.localConfirmed = checked;
                                root.errorMessage = "";
                            }
                        }

                        HusCheckBox {
                            id: apiCheck
                            Layout.fillWidth: true
                            text: "我理解第三方 API 由我自行配置和调用，Fantareal 制作组不管理对应上游服务。"
                            onToggled: {
                                root.apiConfirmed = checked;
                                root.errorMessage = "";
                            }
                        }

                        HusCheckBox {
                            id: legalCheck
                            Layout.fillWidth: true
                            text: "我同意自行遵守所在地法律法规、平台规则和第三方 API 服务商条款。"
                            onToggled: {
                                root.legalConfirmed = checked;
                                root.errorMessage = "";
                            }
                        }
                    }

                    HusDivider {}

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        HusText {
                            Layout.fillWidth: true
                            text: "请手动输入以下确认语（空格和常见标点差异会自动忽略）"
                            font.pixelSize: 16
                            font.weight: Font.DemiBold
                            color: HusTheme.Primary.colorTextPrimary
                            wrapMode: Text.Wrap
                        }

                        HusText {
                            Layout.fillWidth: true
                            text: FantarealBridge.firstLaunchConfirmationText
                            color: HusTheme.Primary.colorTextSecondary
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }

                        HusInput {
                            id: confirmationInput
                            Layout.fillWidth: true
                            placeholderText: "请完整输入确认语"
                            clearEnabled: "active"
                            onTextEdited: {
                                root.typedConfirmation = text;
                                root.errorMessage = "";
                            }
                        }

                        HusText {
                            Layout.fillWidth: true
                            visible: root.errorMessage.length > 0
                            text: root.errorMessage
                            color: HusTheme.Primary.colorError
                            font.pixelSize: 13
                            wrapMode: Text.Wrap
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                HusText {
                    Layout.fillWidth: true
                    text: "确认记录仅保存在本地，不上传年龄段、确认记录或输入内容。"
                    color: HusTheme.Primary.colorTextSecondary
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }

                HusButton {
                    text: "退出程序"
                    onClicked: Qt.quit()
                }

                HusButton {
                    text: "我已阅读，继续使用"
                    type: HusButton.Type_Primary
                    enabled: root.canContinue
                    onClicked: root.acceptDisclaimer()
                }
            }
        }
    }
}
