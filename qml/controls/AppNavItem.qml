import QtQuick
import QtQuick.Layouts
import HuskarUI.Basic

HusButton {
    id: root
    height: 44
    radiusBg.all: 7
    effectEnabled: false
    colorBg: selected ? HusThemeFunctions.alpha(HusTheme.Primary.colorPrimary, 0.18) : "transparent"
    colorBorder: "transparent"
    colorText: selected ? HusTheme.Primary.colorPrimary : HusTheme.Primary.colorTextPrimary
    hoverCursorShape: Qt.PointingHandCursor

    property bool selected: false
    property int iconSource: 0
    property string label: ""

    contentItem: RowLayout {
        spacing: 12
        HusIconText {
            iconSource: root.iconSource
            iconSize: 16
            colorIcon: root.colorText
        }
        HusText {
            text: root.label
            color: root.colorText
            font.pixelSize: 15
            Layout.fillWidth: true
        }
        Rectangle {
            Layout.preferredWidth: 7
            Layout.preferredHeight: 7
            radius: 4
            color: root.selected ? "#42d15a" : "#ff3347"
            opacity: root.selected ? 1.0 : 0.85
        }
    }
}
