import QtQuick
import QtQuick.Layouts
import HuskarUI.Basic

ColumnLayout {
    id: root

    property var rows: []
    property int labelWidth: 160

    spacing: 8

    Repeater {
        model: root.rows

        delegate: Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(42, rowLayout.implicitHeight + 18)
            radius: 8
            color: HusThemeFunctions.alpha(HusTheme.Primary.colorBgBase, HusTheme.isDark ? 0.16 : 0.44)
            border.width: 1
            border.color: HusThemeFunctions.alpha(HusTheme.Primary.colorBorder, 0.28)

            property string rowText: modelData
            property int separatorIndex: rowText.indexOf("：")
            property string labelText: separatorIndex >= 0 ? rowText.substring(0, separatorIndex) : rowText
            property string valueText: separatorIndex >= 0 ? rowText.substring(separatorIndex + 1) : ""

            RowLayout {
                id: rowLayout
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                spacing: 12

                HusText {
                    Layout.preferredWidth: root.labelWidth
                    text: labelText
                    color: HusTheme.Primary.colorTextSecondary
                    elide: Text.ElideRight
                }

                HusText {
                    Layout.fillWidth: true
                    text: valueText
                    color: HusTheme.Primary.colorTextPrimary
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
