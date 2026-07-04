import QtQuick
import QtQuick.Layouts
import HuskarUI.Basic

ColumnLayout {
    id: root

    property string title: ""
    property string description: ""
    default property alias content: contentHost.data

    Layout.fillWidth: true
    spacing: 7

    HusText {
        Layout.fillWidth: true
        text: root.title
        color: HusTheme.Primary.colorTextPrimary
        font.pixelSize: 14
        font.weight: Font.DemiBold
        elide: Text.ElideRight
    }

    HusText {
        Layout.fillWidth: true
        visible: root.description.length > 0
        text: root.description
        color: HusTheme.Primary.colorTextSecondary
        font.pixelSize: 12
        wrapMode: Text.Wrap
    }

    Item {
        id: contentHost
        Layout.fillWidth: true
        implicitHeight: childrenRect.height
    }
}
