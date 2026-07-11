#pragma once

#include "database/databasemodels.h"
#include "database/databasepaths.h"

#include <QList>
#include <QStringList>

#include <optional>

class DatabaseRepository final {
public:
    explicit DatabaseRepository(DatabasePaths paths);

    DatabaseStatus initializeSchema() const;
    DatabaseOverview describe() const;
    DatabaseOperationResult createPendingTurn(const DatabaseTurnRecord& record) const;
    DatabaseOperationResult saveTurnResult(const DatabaseTurnResult& result) const;
    DatabaseOperationResult initializeRuntime(const QString& cardUid, const QJsonObject& databaseConfig) const;
    DatabaseOperationResult configureStoryTime(const QString& cardUid, const QJsonObject& draft) const;
    DatabaseOperationResult markTurnError(const QString& turnId, const QString& code, const QString& message,
        int expectedAttemptCount = -1) const;
    DatabaseOperationResult markMessageSuperseded(const QString& cardUid, const QString& messageId) const;
    DatabaseOperationResult markMessagesSuperseded(const QString& cardUid, const QStringList& messageIds) const;
    DatabaseOperationResult retryTurn(const QString& turnId) const;
    std::optional<DatabaseTurnView> turnByMessageId(const QString& cardUid, const QString& messageId) const;
    std::optional<DatabaseTurnView> turnById(const QString& turnId) const;
    QList<DatabaseTurnView> recentTurns(const QString& cardUid, int limit) const;
    DatabaseRuntimeView runtimeView(const QString& cardUid, int ledgerLimit = 50) const;
    DatabaseDebugTableView debugTable(
        const QString& tableName, const QString& cardUid, int offset = 0, int limit = 50) const;

private:
    DatabasePaths paths_;
};
