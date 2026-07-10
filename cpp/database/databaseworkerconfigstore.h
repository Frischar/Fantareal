#pragma once

#include "database/databasemodels.h"
#include "database/databasepaths.h"

#include <QJsonObject>
#include <QVariantMap>

class DatabaseWorkerConfigStore final {
public:
    explicit DatabaseWorkerConfigStore(DatabasePaths paths);

    DatabaseWorkerConfig load(QString* errorMessage = nullptr) const;
    QVariantMap draft(QString* errorMessage = nullptr) const;
    DatabaseOperationResult save(const QVariantMap& draft, bool clearApiKey = false) const;
    DatabaseOperationResult copyMainSettings(const QJsonObject& mainSettings) const;

private:
    QJsonObject readRaw(QString* errorMessage) const;
    DatabaseOperationResult writeRaw(const QJsonObject& object) const;

    DatabasePaths paths_;
};
