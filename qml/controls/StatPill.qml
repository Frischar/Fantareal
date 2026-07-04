import QtQuick
import HuskarUI.Basic

HusTag {
    id: root

    property color accentColor: HusTheme.Primary.colorPrimary

    height: 28
    radiusBg.all: 14
    colorBg: HusThemeFunctions.alpha(root.accentColor, HusTheme.isDark ? 0.22 : 0.16)
    colorBorder: HusThemeFunctions.alpha(root.accentColor, HusTheme.isDark ? 0.22 : 0.20)
    colorText: root.accentColor
    font.pixelSize: 13
    font.bold: true
}
