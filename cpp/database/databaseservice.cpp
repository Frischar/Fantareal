#include "database/databaseservice.h"

#include "database/databaserepository.h"
#include "database/databaseworkerconfigstore.h"

#include <utility>

DatabaseService::DatabaseService(QString rootPath)
    : paths_(std::move(rootPath)) {
}

DatabasePaths DatabaseService::paths() const {
    return paths_;
}

DatabaseStatus DatabaseService::ensureInitialized() const {
    DatabaseRepository repository(paths_);
    return repository.initializeSchema();
}

DatabaseOverview DatabaseService::overview() const {
    DatabaseRepository repository(paths_);
    return repository.describe();
}

DatabaseWorkerConfig DatabaseService::loadWorkerConfig(QString* errorMessage) const {
    return DatabaseWorkerConfigStore(paths_).load(errorMessage);
}

QVariantMap DatabaseService::workerConfigDraft(QString* errorMessage) const {
    return DatabaseWorkerConfigStore(paths_).draft(errorMessage);
}

DatabaseOperationResult DatabaseService::saveWorkerConfig(const QVariantMap& draft, bool clearApiKey) const {
    return DatabaseWorkerConfigStore(paths_).save(draft, clearApiKey);
}

DatabaseOperationResult DatabaseService::copyMainModelConfig(const QJsonObject& mainSettings) const {
    return DatabaseWorkerConfigStore(paths_).copyMainSettings(mainSettings);
}

DatabaseOperationResult DatabaseService::createPendingTurn(const DatabaseTurnRecord& record) const {
    return DatabaseRepository(paths_).createPendingTurn(record);
}

DatabaseOperationResult DatabaseService::saveTurnResult(const DatabaseTurnResult& result) const {
    return DatabaseRepository(paths_).saveTurnResult(result);
}

DatabaseOperationResult DatabaseService::initializeRuntime(const QString& cardUid, const QJsonObject& databaseConfig) const {
    return DatabaseRepository(paths_).initializeRuntime(cardUid, databaseConfig);
}

DatabaseOperationResult DatabaseService::configureStoryTime(const QString& cardUid, const QJsonObject& draft) const {
    return DatabaseRepository(paths_).configureStoryTime(cardUid, draft);
}

DatabaseOperationResult DatabaseService::markTurnError(
    const QString& turnId, const QString& code, const QString& message, int expectedAttemptCount) const {
    return DatabaseRepository(paths_).markTurnError(turnId, code, message, expectedAttemptCount);
}

DatabaseOperationResult DatabaseService::markMessageSuperseded(const QString& cardUid, const QString& messageId) const {
    return DatabaseRepository(paths_).markMessageSuperseded(cardUid, messageId);
}

DatabaseOperationResult DatabaseService::markMessagesSuperseded(
    const QString& cardUid, const QStringList& messageIds) const {
    return DatabaseRepository(paths_).markMessagesSuperseded(cardUid, messageIds);
}

DatabaseOperationResult DatabaseService::retryTurn(const QString& turnId) const {
    return DatabaseRepository(paths_).retryTurn(turnId);
}

std::optional<DatabaseTurnView> DatabaseService::turnByMessageId(const QString& cardUid, const QString& messageId) const {
    return DatabaseRepository(paths_).turnByMessageId(cardUid, messageId);
}

std::optional<DatabaseTurnView> DatabaseService::turnById(const QString& turnId) const {
    return DatabaseRepository(paths_).turnById(turnId);
}

QList<DatabaseTurnView> DatabaseService::recentTurns(const QString& cardUid, int limit) const {
    return DatabaseRepository(paths_).recentTurns(cardUid, limit);
}

DatabaseRuntimeView DatabaseService::runtimeView(const QString& cardUid, int ledgerLimit) const {
    return DatabaseRepository(paths_).runtimeView(cardUid, ledgerLimit);
}

DatabaseDebugTableView DatabaseService::debugTable(
    const QString& tableName, const QString& cardUid, int offset, int limit) const {
    return DatabaseRepository(paths_).debugTable(tableName, cardUid, offset, limit);
}
