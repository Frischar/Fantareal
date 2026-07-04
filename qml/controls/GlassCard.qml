import QtQuick
import HuskarUI.Basic

Item {
    id: root
    implicitWidth: 320
    implicitHeight: 220

    property color accentColor: HusTheme.Primary.colorPrimary
    property int cornerRadius: 8
    property real shadowAlphaDark: 0.32
    property real shadowAlphaLight: 0.22
    property real backgroundAlphaDark: 0.18
    property real backgroundAlphaLight: 0.48
    property real borderAlphaDark: 0.28
    property real borderAlphaLight: 0.46

    HusCard {
        id: card
        anchors.fill: parent
        showShadow: true
        colorShadow: HusThemeFunctions.alpha(root.accentColor, HusTheme.isDark ? root.shadowAlphaDark : root.shadowAlphaLight)
        colorBg: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? root.backgroundAlphaDark : root.backgroundAlphaLight)
        colorBorder: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, HusTheme.isDark ? root.borderAlphaDark : root.borderAlphaLight)
        radiusBg.all: root.cornerRadius
        titleDelegate: null
        coverDelegate: null
        actionDelegate: null
        bodyDelegate: Item {}
        bgDelegate: Rectangle {
            radius: root.cornerRadius
            border.width: 1
            border.color: card.colorBorder
            color: card.colorBg
        }
    }
}
