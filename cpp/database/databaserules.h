#pragma once

#include <QHash>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QString>

namespace DatabaseRules {

QJsonObject defaultStoryTimeState(const QString& cardUid);
QJsonObject normalizeStoryTimeState(const QJsonObject& state, const QString& cardUid);
QJsonObject configureStoryTime(const QJsonObject& current, const QJsonObject& draft, const QString& cardUid);
QJsonObject advanceStoryTime(const QJsonObject& current, const QJsonObject& rawDelta,
    const QString& turnId, const QString& messageId, qint64 turnOrdinal);
QJsonObject storyTimeContext(const QJsonObject& state);

QList<QJsonObject> evaluateStages(const QJsonObject& databaseConfig,
    const QHash<QString, QJsonValue>& runtimeValues,
    const QJsonObject& storyContext,
    const QHash<QString, QJsonObject>& currentStages,
    qint64 turnOrdinal);

}
