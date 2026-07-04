import QtQuick

Item {
    id: root

    property Flickable target
    property var childTargets: []
    property real wheelMultiplier: 1.5
    property int wheelStep: 96
    property int animationDuration: 180
    property real __targetContentY: target ? target.contentY : 0
    property var __childTarget: null
    property real __childTargetContentY: 0

    enabled: target !== null
    z: 40

    function __numberFor(object, propertyName, fallback) {
        if (!object) {
            return fallback;
        }
        const rawValue = object[propertyName];
        if (rawValue === undefined || rawValue === null) {
            return fallback;
        }
        const numericValue = Number(rawValue);
        return isFinite(numericValue) ? numericValue : fallback;
    }

    function __scrollableFor(candidate) {
        if (!candidate) {
            return null;
        }
        if (__numberFor(candidate, "contentHeight", 0) > 0 && __numberFor(candidate, "height", 0) > 0) {
            return candidate;
        }
        const contentItem = candidate.contentItem;
        const children = contentItem ? contentItem.children : null;
        if (!children) {
            return candidate;
        }
        for (let index = 0; index < children.length; ++index) {
            const child = children[index];
            if (child && child.contentItem && __numberFor(child.contentItem, "contentHeight", 0) > 0) {
                return child.contentItem;
            }
            if (child && __numberFor(child, "contentHeight", 0) > 0) {
                return child;
            }
        }
        return candidate;
    }

    function __minYFor(flickable) {
        return __numberFor(flickable, "originY", 0);
    }

    function __maxYFor(flickable) {
        if (!flickable) {
            return 0;
        }
        return __minYFor(flickable)
            + Math.max(0, __numberFor(flickable, "contentHeight", 0) - __numberFor(flickable, "height", 0));
    }

    function __clampFor(flickable, value) {
        return Math.max(__minYFor(flickable), Math.min(__maxYFor(flickable), value));
    }

    function __clamp(value) {
        return __clampFor(target, value);
    }

    function __containsFlickable(flickable, localX, localY) {
        if (!flickable || !flickable.visible || __numberFor(flickable, "width", 0) <= 0 || __numberFor(flickable, "height", 0) <= 0) {
            return false;
        }
        const point = root.mapToItem(flickable, localX, localY);
        return point.x >= 0 && point.x <= __numberFor(flickable, "width", 0)
            && point.y >= 0 && point.y <= __numberFor(flickable, "height", 0);
    }

    function __canScrollFlickable(flickable, deltaY) {
        if (!flickable || __numberFor(flickable, "contentHeight", 0) <= __numberFor(flickable, "height", 0) || deltaY === 0) {
            return false;
        }
        const minY = __minYFor(flickable);
        const maxY = __maxYFor(flickable);
        const currentY = root.__childTarget === flickable && childScrollAnimation.running
            ? root.__childTargetContentY
            : __numberFor(flickable, "contentY", 0);
        if (deltaY < 0) {
            return currentY > minY;
        }
        return currentY < maxY;
    }

    function scrollBy(deltaY) {
        if (!target || __numberFor(target, "contentHeight", 0) <= __numberFor(target, "height", 0)) {
            return;
        }
        __targetContentY = __clamp(__targetContentY + deltaY);
        scrollAnimation.stop();
        scrollAnimation.from = __numberFor(target, "contentY", 0);
        scrollAnimation.to = __targetContentY;
        scrollAnimation.start();
    }

    function scrollChildBy(flickable, deltaY) {
        const baseY = root.__childTarget === flickable && childScrollAnimation.running
            ? root.__childTargetContentY
            : __numberFor(flickable, "contentY", 0);
        root.__childTarget = flickable;
        root.__childTargetContentY = __clampFor(flickable, baseY + deltaY);
        childScrollAnimation.stop();
        childScrollAnimation.target = flickable;
        childScrollAnimation.from = __numberFor(flickable, "contentY", 0);
        childScrollAnimation.to = root.__childTargetContentY;
        childScrollAnimation.start();
    }

    Connections {
        target: root.target

        function onContentYChanged() {
            if (!scrollAnimation.running && root.target) {
                root.__targetContentY = root.__clamp(root.target.contentY);
            }
        }

        function onContentHeightChanged() {
            root.__targetContentY = root.__clamp(root.__targetContentY);
        }

        function onHeightChanged() {
            root.__targetContentY = root.__clamp(root.__targetContentY);
        }
    }

    NumberAnimation {
        id: scrollAnimation
        target: root.target
        property: "contentY"
        duration: root.animationDuration
        easing.type: Easing.OutCubic
    }

    NumberAnimation {
        id: childScrollAnimation
        property: "contentY"
        duration: root.animationDuration
        easing.type: Easing.OutCubic
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton

        onWheel: function(wheel) {
            const rawDelta = wheel.pixelDelta.y !== 0
                ? wheel.pixelDelta.y
                : (wheel.angleDelta.y / 120) * root.wheelStep;
            if (rawDelta === 0) {
                return;
            }
            const deltaY = -rawDelta * root.wheelMultiplier;
            for (const childTarget of root.childTargets) {
                const scrollTarget = root.__scrollableFor(childTarget);
                if (root.__containsFlickable(childTarget, wheel.x, wheel.y) && root.__canScrollFlickable(scrollTarget, deltaY)) {
                    root.scrollChildBy(scrollTarget, deltaY);
                    wheel.accepted = true;
                    return;
                }
            }
            root.scrollBy(deltaY);
            wheel.accepted = true;
        }
    }
}
