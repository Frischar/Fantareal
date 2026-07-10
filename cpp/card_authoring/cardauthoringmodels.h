#pragma once

#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QString>
#include <QStringList>

namespace CardAuthoring {

QString projectType();
QString legacyProjectType();
int projectVersion();

QJsonObject createEmptyProject();
QJsonObject normalizeProject(const QJsonObject& payload);
QJsonObject normalizePersonaCard(const QJsonObject& payload);
QJsonObject normalizeWorldbook(const QJsonObject& payload);
QJsonObject normalizeWorldbookEntry(const QJsonObject& payload, int index);
QJsonObject normalizeMemory(const QJsonObject& payload);
QJsonObject normalizeMemoryItem(const QJsonObject& payload, int index);
QJsonObject normalizePreset(const QJsonObject& payload);
QJsonObject normalizePresetItem(const QJsonObject& payload, int index);
QJsonObject normalizeDatabase(const QJsonObject& payload);
QJsonObject normalizeDatabaseVariable(const QJsonObject& payload, int index);
QJsonObject normalizeDatabaseStage(const QJsonObject& payload, int index);
QJsonObject normalizeDatabaseTag(const QJsonObject& payload, int index);

QString normalizedText(const QJsonValue& value);
QStringList splitTags(const QJsonValue& value);
QJsonArray tagsArray(const QStringList& tags);
QString stableJson(const QJsonValue& value);

}
