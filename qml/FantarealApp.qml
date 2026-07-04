pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import HuskarUI.Basic
import Fantareal

HusWindow {
    id: root

    width: 1400
    height: 900
    minimumWidth: 1000
    minimumHeight: 680
    title: qsTr("Fantareal PC")
    followThemeSwitch: true
    captionBar.visible: Qt.platform.os === "windows" || Qt.platform.os === "linux" || Qt.platform.os === "osx"
    captionBar.height: captionBar.visible ? 38 : 0
    captionBar.showThemeButton: true
    captionBar.showTopButton: true
    captionBar.showWinIcon: Qt.platform.os !== "osx"
    captionBar.themeCallback: () => {
        HusTheme.darkMode = HusTheme.isDark ? HusTheme.Light : HusTheme.Dark;
        root.setWindowMode(HusTheme.isDark);
    }
    captionBar.topCallback: checked => {
        HusApi.setWindowStaysOnTopHint(root, checked);
    }
    captionBar.winIconDelegate: Rectangle {
        width: 18
        height: 18
        radius: 4
        color: HusThemeFunctions.alpha(Global.accentBlue, 0.88)

        HusText {
            anchors.centerIn: parent
            text: "F"
            color: "white"
            font.pixelSize: 12
            font.bold: true
        }
    }
    captionBar.winTitleDelegate: RowLayout {
        spacing: 0
        layoutDirection: captionBar.mirrored ? Qt.RightToLeft : Qt.LeftToRight

        Connections {
            target: captionBar
            function onWindowAgentChanged() {
                captionBar.addInteractionItem(backButton);
                captionBar.addInteractionItem(forwardButton);
                captionBar.addInteractionItem(refreshButton);
            }
        }

        HusText {
            text: captionBar.winTitle
            color: captionBar.winTitleColor
            font: captionBar.winTitleFont
        }

        HusCaptionButton {
            id: backButton
            Layout.leftMargin: 14
            Layout.fillHeight: true
            enabled: false
            noDisabledState: true
            iconSource: HusIcon.ArrowLeftOutlined
            iconSize: 14
            colorBg: hovered ? HusThemeFunctions.alpha(Global.accentBlue, 0.12) : "transparent"
            contentDescription: qsTr("后退")
        }

        HusCaptionButton {
            id: forwardButton
            Layout.fillHeight: true
            enabled: false
            noDisabledState: true
            iconSource: HusIcon.ArrowRightOutlined
            iconSize: 14
            colorBg: hovered ? HusThemeFunctions.alpha(Global.accentBlue, 0.12) : "transparent"
            contentDescription: qsTr("前进")
        }

        HusCaptionButton {
            id: refreshButton
            Layout.fillHeight: true
            noDisabledState: true
            iconSource: HusIcon.ReloadOutlined
            iconSize: 14
            colorBg: hovered ? HusThemeFunctions.alpha(Global.accentBlue, 0.12) : "transparent"
            contentDescription: qsTr("刷新旧数据扫描")
            onClicked: FantarealBridge.refreshLegacyScan()
        }
    }
    captionBar.winPresetButtonsDelegate: RowLayout {
        spacing: 0
        layoutDirection: captionBar.mirrored ? Qt.RightToLeft : Qt.LeftToRight

        Connections {
            target: captionBar
            function onWindowAgentChanged() {
                captionBar.addInteractionItem(scanButton);
                captionBar.addInteractionItem(themeButton);
                captionBar.addInteractionItem(topButton);
            }
        }

        HusCaptionButton {
            id: scanButton
            Layout.fillHeight: true
            noDisabledState: true
            text: qsTr("刷新")
            iconSource: HusIcon.DatabaseOutlined
            iconSize: 14
            colorBg: HusThemeFunctions.alpha(Global.accentBlue, hovered ? 0.24 : 0.14)
            colorText: HusTheme.Primary.colorTextBase
            onClicked: FantarealBridge.refreshLegacyScan()
        }

        HusCaptionButton {
            id: themeButton
            Layout.fillHeight: true
            noDisabledState: true
            iconSource: HusTheme.isDark ? HusIcon.MoonOutlined : HusIcon.SunOutlined
            iconSize: 14
            contentDescription: qsTr("明暗主题")
            onClicked: captionBar.themeCallback()
        }

        HusCaptionButton {
            id: topButton
            Layout.fillHeight: true
            noDisabledState: true
            iconSource: HusIcon.PushpinOutlined
            iconSize: 14
            checkable: true
            checked: captionBar.topButtonChecked
            contentDescription: qsTr("置顶")
            onClicked: captionBar.topCallback(checked)
        }
    }

    property string currentPage: "chat"
    property bool sidebarHovered: false
    property bool sidebarExpanded: sidebarHovered && currentPage !== "chat"
    property int sidebarCollapsedWidth: 68
    property int sidebarExpandedWidth: 292
    property real sidebarWidth: sidebarExpanded ? sidebarExpandedWidth : sidebarCollapsedWidth
    property real sidebarLabelOpacity: sidebarExpanded ? 1.0 : 0.0
    property string backgroundImageUrl: FantarealBridge.settingsDraft.background_image_url || ""
    property real backgroundImageOpacity: Number(FantarealBridge.backgroundImagePreviewOpacity)
    property real backgroundVisualOpacity: Math.max(0.0, Math.min(1.0, backgroundImageOpacity))

    Behavior on sidebarWidth {
        NumberAnimation {
            duration: 220
            easing.type: Easing.OutCubic
        }
    }

    Behavior on sidebarLabelOpacity {
        NumberAnimation {
            duration: 150
            easing.type: Easing.OutCubic
        }
    }

    function badgeStateFrom(value) {
        if (value === "online") {
            return HusBadge.State_Success;
        }
        if (value === "warning") {
            return HusBadge.State_Warning;
        }
        if (value === "pending") {
            return HusBadge.State_Processing;
        }
        return HusBadge.State_Default;
    }

    function openPage(key) {
        root.currentPage = key;
        navMenu.gotoMenu(key);
    }

    Component.onCompleted: {
        if (Qt.platform.os === "windows") {
            setSpecialEffect(HusWindow.None);
        } else if (Qt.platform.os === "osx") {
            setSpecialEffect(HusWindow.Mac_BlurEffect);
        }
        let startPageKey = "";
        for (const argument of Qt.application.arguments) {
            if (argument.indexOf("--page=") === 0) {
                startPageKey = argument.substring(7);
                break;
            }
        }
        if (startPageKey.length > 0) {
            openPage(startPageKey);
        }
    }

    Rectangle {
        id: appSurface
        anchors.top: root.captionBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: HusTheme.isDark ? "#07051d" : "#dedfec"
        clip: true

        Image {
            anchors.fill: parent
            source: root.backgroundImageUrl
            visible: root.backgroundImageUrl.length > 0
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: true
            opacity: root.backgroundVisualOpacity
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 8

            Item {
                id: sidebar
                Layout.preferredWidth: root.sidebarWidth
                Layout.minimumWidth: root.sidebarCollapsedWidth
                Layout.maximumWidth: root.sidebarExpandedWidth
                Layout.fillHeight: true
                clip: true

                HoverHandler {
                    id: sidebarHoverHandler
                    onHoveredChanged: root.sidebarHovered = hovered
                }

                Rectangle {
                    anchors.fill: parent
                    radius: 24
                    color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.18 : 0.36)
                    border.width: 1
                    border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorSplit, 0.40)
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.sidebarExpanded ? 12 : 7
                    anchors.rightMargin: root.sidebarExpanded ? 12 : 7
                    anchors.topMargin: root.sidebarExpanded ? 12 : 8
                    anchors.bottomMargin: root.sidebarExpanded ? 12 : 8
                    spacing: root.sidebarExpanded ? 10 : 8

                    HusMenu {
                        id: navMenu
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        showEdge: true
                        showToolTip: true
                        compactMode: root.sidebarExpanded ? HusMenu.Mode_Relaxed : HusMenu.Mode_Compact
                        compactWidth: root.sidebarCollapsedWidth - 22
                        popupWidth: 220
                        defaultMenuWidth: Math.max(46, root.sidebarWidth - 24)
                        defaultMenuIconSpacing: root.sidebarExpanded ? 8 : 0
                        defaultMenuSpacing: root.sidebarExpanded ? 5 : 6
                        defaultMenuTopPadding: root.sidebarExpanded ? 7 : 8
                        defaultMenuBottomPadding: root.sidebarExpanded ? 7 : 8
                        defaultSelectedKeys: [root.currentPage]
                        initModel: Global.navMenuModel
                        radiusMenuBg.all: 13
                        onClickMenu: (deep, key, keyPath, data) => {
                            if (data && data.type !== "group" && data.type !== "divider" && key !== "") {
                                root.currentPage = key;
                            }
                        }
                        menuLabelDelegate: HusText {
                            visible: root.sidebarExpanded
                            opacity: root.sidebarLabelOpacity
                            text: root.sidebarExpanded ? menuButton.text : ""
                            font: menuButton.font
                            color: menuButton.colorText
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter

                            property var model: parent.model
                            property var menuButton: parent.menuButton
                        }
                        menuBgDelegate: Rectangle {
                            radius: 13
                            color: menuButton.isCurrent ? HusThemeFunctions.alpha(Global.accentBlue, HusTheme.isDark ? 0.28 : 0.18) : (menuButton.hovered ? HusThemeFunctions.alpha(Global.accentBlue, 0.08) : "transparent")
                            border.width: menuButton.isCurrent ? 1 : 0
                            border.color: HusThemeFunctions.alpha(Global.accentBlue, 0.28)

                            property var model: parent.model
                            property var menuButton: parent.menuButton

                            HusBadge {
                                anchors.right: parent.right
                                anchors.rightMargin: root.sidebarExpanded ? 8 : 4
                                anchors.verticalCenter: parent.verticalCenter
                                dot: true
                                badgeState: root.badgeStateFrom(parent.model.state === undefined ? "" : parent.model.state)
                                visible: parent.model.state !== undefined
                            }
                        }
                    }
                }
            }

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: {
                    switch (root.currentPage) {
                    case "chat":
                        return chatPage;
                    case "settings":
                        return settingsPage;
                    case "routes":
                        return routesPage;
                    case "cards":
                        return cardsPage;
                    case "preset":
                        return presetPage;
                    case "memory":
                        return memoryPage;
                    case "worldbook":
                        return worldbookPage;
                    case "workshop":
                        return workshopPage;
                    case "plugins":
                        return pluginsPage;
                    default:
                        return homePage;
                    }
                }
            }
        }
    }

    Component {
        id: homePage
        HomePage {
            onOpenPage: page => root.openPage(page)
        }
    }
    Component {
        id: chatPage
        ChatPage {
            onOpenPage: page => root.openPage(page)
        }
    }
    Component {
        id: settingsPage
        SettingsPage {}
    }
    Component {
        id: routesPage
        RoutesPage {}
    }
    Component {
        id: cardsPage
        CardsPage {}
    }
    Component {
        id: presetPage
        PresetPage {}
    }
    Component {
        id: memoryPage
        MemoryPage {}
    }
    Component {
        id: worldbookPage
        WorldbookPage {}
    }
    Component {
        id: workshopPage
        WorkshopPage {}
    }
    Component {
        id: pluginsPage
        PluginsPage {}
    }

    FirstLaunchDisclaimerModal {
        id: firstLaunchDisclaimerModal
        windowWidth: root.width
        windowHeight: root.height - root.captionBar.height
    }
}
