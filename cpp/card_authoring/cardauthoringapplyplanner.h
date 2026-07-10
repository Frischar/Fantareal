#pragma once

#include "card_authoring/cardauthoringpaths.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QStringList>

class CardAuthoringApplyPlanner final {
public:
    explicit CardAuthoringApplyPlanner(QString rootPath);

    QJsonObject buildPreview(const QJsonObject& project, const QStringList& modules = {}) const;
    QJsonObject applySelected(const QJsonObject& project, const QStringList& selectedGroupIds = {}) const;

private:
    QJsonObject readCurrentCard(QString* errorMessage = nullptr) const;
    bool readJsonObjectFile(const QString& relativePath, QJsonObject* object, QString* errorMessage = nullptr) const;
    bool readJsonArrayFile(const QString& relativePath, QJsonArray* array, QString* errorMessage = nullptr) const;
    bool writeJsonDocumentFile(const QString& relativePath, const QJsonDocument& document, QString* errorMessage = nullptr) const;
    QString backupRuntimeFile(const QString& relativePath, QString* errorMessage = nullptr) const;
    QString memoryCardUid(const QJsonObject& currentCard) const;
    QString currentMemoryRelativePath(const QJsonObject& currentCard) const;
    QJsonArray buildChanges(const QJsonObject& beforeRaw, const QJsonObject& afterRaw, const QStringList& fields) const;
    QJsonArray buildDocumentChanges(const QString& field, const QString& label, const QString& path, const QJsonValue& before, const QJsonValue& after) const;
    QJsonObject buildGroup(const QString& id, const QString& title, const QString& description, const QJsonArray& changes) const;
    QStringList normalizedModules(const QStringList& modules) const;
    QJsonObject mergedCard(const QJsonObject& currentCard, const QJsonObject& compiledCard, const QStringList& groupIds) const;
    QJsonObject mergedWorldbookStore(const QJsonObject& currentStore, const QJsonObject& project) const;
    QJsonObject mergedPresetStore(const QJsonObject& currentStore, const QJsonObject& project) const;
    QJsonArray mergedMemoryEntries(const QJsonArray& currentEntries, const QJsonObject& project) const;

    CardAuthoringPaths paths_;
};
