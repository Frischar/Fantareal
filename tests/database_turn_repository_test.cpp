#include "database/databaseservice.h"
#include "database/databaserules.h"

#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QTemporaryDir>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

int rowCount(const QString& databasePath, const QString& sql) {
    const QString connectionName = QStringLiteral("FantarealTurnRepositoryCount_%1").arg(qHash(sql));
    int count = -1;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(databasePath);
        if (database.open()) {
            QSqlQuery query(database);
            if (query.exec(sql) && query.next()) {
                count = query.value(0).toInt();
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return count;
}

QString scalarText(const QString& databasePath, const QString& sql) {
    const QString connectionName = QStringLiteral("FantarealTurnRepositoryScalar_%1").arg(qHash(sql));
    QString value;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(databasePath);
        if (database.open()) {
            QSqlQuery query(database);
            if (query.exec(sql) && query.next()) value = query.value(0).toString();
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return value;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    DatabaseService service(tempDir.path());
    if (!service.ensureInitialized().ok) {
        return fail(QStringLiteral("failed to initialize database schema")) ? 0 : 1;
    }

    const QJsonObject initialStage{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("stage_key"), QStringLiteral("start") },
        { QStringLiteral("stage_name"), QStringLiteral("初识") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("priority"), 10 },
        { QStringLiteral("conditions"), QJsonArray{} },
        { QStringLiteral("activation_tag"), QStringLiteral("database.stage.main.start") },
        { QStringLiteral("emits_tags"), QJsonArray{ QStringLiteral("database.stage.main.start") } },
    };
    const QJsonObject trustedStage{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("stage_key"), QStringLiteral("trusted") },
        { QStringLiteral("stage_name"), QStringLiteral("信赖") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("priority"), 20 },
        { QStringLiteral("condition_mode"), QStringLiteral("all") },
        { QStringLiteral("conditions"), QJsonArray{ QJsonObject{
              { QStringLiteral("source"), QStringLiteral("variable") },
              { QStringLiteral("var"), QStringLiteral("affection") },
              { QStringLiteral("op"), QStringLiteral(">=") },
              { QStringLiteral("value"), 40 },
          } } },
        { QStringLiteral("confirm_turns"), 1 },
        { QStringLiteral("cooldown_turns"), 2 },
        { QStringLiteral("activation_tag"), QStringLiteral("database.stage.main.trusted") },
        { QStringLiteral("emits_tags"), QJsonArray{
              QStringLiteral("database.stage.main.trusted"),
              QStringLiteral("database.tag.trusted-lore"),
          } },
    };
    const QJsonObject databaseConfig{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("roles"), QJsonArray{ QJsonObject{
              { QStringLiteral("role_id"), QStringLiteral("main") },
              { QStringLiteral("role_name"), QStringLiteral("主角色") },
              { QStringLiteral("enabled"), true },
              { QStringLiteral("mode"), QStringLiteral("full") },
              { QStringLiteral("initial_stage"), QStringLiteral("start") },
              { QStringLiteral("stages"), QJsonArray{ initialStage, trustedStage } },
          } } },
        { QStringLiteral("stages"), QJsonArray{ initialStage, trustedStage } },
        { QStringLiteral("tags"), QJsonArray{ QJsonObject{
              { QStringLiteral("tag"), QStringLiteral("database.tag.runtime-signal") },
          } } },
    };
    const QJsonObject pureStoryTime = DatabaseRules::configureStoryTime(
        DatabaseRules::defaultStoryTimeState(QStringLiteral("card-1")),
        QJsonObject{
            { QStringLiteral("action"), QStringLiteral("initialize") },
            { QStringLiteral("baseTime"), QStringLiteral("2026-01-01 08:00:00") },
            { QStringLiteral("advanceMode"), QStringLiteral("explicit") },
        }, QStringLiteral("card-1"));
    if (pureStoryTime.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-01-01 08:00:00")) {
        return fail(QStringLiteral("pure story time initialization failed: %1")
                        .arg(QString::fromUtf8(QJsonDocument(pureStoryTime).toJson(QJsonDocument::Compact)))) ? 0 : 1;
    }
    const DatabaseOperationResult deterministicInitialization = service.initializeRuntime(
        QStringLiteral("card-1"), databaseConfig);
    const DatabaseOperationResult storyTimeInitialization = service.configureStoryTime(
        QStringLiteral("card-1"), QJsonObject{
                { QStringLiteral("action"), QStringLiteral("initialize") },
                { QStringLiteral("baseTime"), QStringLiteral("2026-01-01 08:00:00") },
                { QStringLiteral("advanceMode"), QStringLiteral("explicit") },
            });
    if (!deterministicInitialization.ok || !storyTimeInitialization.ok) {
        return fail(QStringLiteral("failed to initialize deterministic database runtime: %1 / %2")
                        .arg(deterministicInitialization.message, storyTimeInitialization.message)) ? 0 : 1;
    }
    const QJsonObject initializedStoryTime = service.runtimeView(QStringLiteral("card-1")).storyTime;
    if (!initializedStoryTime.value(QStringLiteral("enabled")).toBool()
        || initializedStoryTime.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-01-01 08:00:00")) {
        return fail(QStringLiteral("story time initialization did not persist: %1 / raw=%2 / %3")
                        .arg(storyTimeInitialization.message,
                            scalarText(service.paths().databasePath(), QStringLiteral(
                                "SELECT \"current_time\" FROM database_story_time_state WHERE card_uid = 'card-1'")),
                            QString::fromUtf8(QJsonDocument(initializedStoryTime).toJson(QJsonDocument::Compact)))) ? 0 : 1;
    }

    DatabaseTurnRecord pending;
    pending.turnId = QStringLiteral("turn-1");
    pending.cardUid = QStringLiteral("card-1");
    pending.conversationId = QStringLiteral("conversation-1");
    pending.messageId = QStringLiteral("message-1");
    pending.turnIndex = 1;
    pending.contentHash = QString(64, QLatin1Char('a'));
    pending.workerModel = QStringLiteral("fast-model");

    if (!service.createPendingTurn(pending).ok) {
        return fail(QStringLiteral("failed to create pending turn")) ? 0 : 1;
    }
    if (service.createPendingTurn(pending).ok) {
        return fail(QStringLiteral("duplicate card/message turn should be rejected")) ? 0 : 1;
    }

    const std::optional<DatabaseTurnView> pendingView = service.turnByMessageId(pending.cardUid, pending.messageId);
    if (!pendingView || pendingView->turn.status != DatabaseTurnStatus::Pending || pendingView->hasDisplay) {
        return fail(QStringLiteral("pending turn should be queryable without display")) ? 0 : 1;
    }

    DatabaseTurnResult turnResult;
    turnResult.display.turnId = pending.turnId;
    turnResult.display.workerModel = QStringLiteral("fast-model");
    turnResult.display.warningsJson = QStringLiteral("[\"ignored optional field\"]");
    turnResult.expectedAttemptCount = pending.attemptCount;
    turnResult.display.title.insert(QStringLiteral("title"), QStringLiteral("状态标题"));
    turnResult.display.record.insert(QStringLiteral("summary"), QStringLiteral("状态摘要"));
    turnResult.display.record.insert(QStringLiteral("characters"), QJsonArray{ QJsonObject{
        { QStringLiteral("roleId"), QStringLiteral("main") },
        { QStringLiteral("name"), QStringLiteral("主角色") },
        { QStringLiteral("fields"), QJsonArray{ QJsonObject{
              { QStringLiteral("key"), QStringLiteral("location") },
              { QStringLiteral("label"), QStringLiteral("当前位置") },
              { QStringLiteral("value"), QStringLiteral("咖啡馆") },
          } } },
    } });
    turnResult.databaseConfig = databaseConfig;
    turnResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("snapshot"), QJsonObject{
              { QStringLiteral("scope"), QStringLiteral("current") },
              { QStringLiteral("title"), QStringLiteral("本轮快照") },
              { QStringLiteral("payload"), QJsonObject{ { QStringLiteral("location"), QStringLiteral("咖啡馆") } } },
          } },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("key"), QStringLiteral("affection") },
              { QStringLiteral("label"), QStringLiteral("好感度") },
              { QStringLiteral("value"), 42 },
              { QStringLiteral("maximum"), 100 },
              { QStringLiteral("delta"), 2 },
              { QStringLiteral("reason"), QStringLiteral("共同完成委托") },
          } } },
        { QStringLiteral("relationships"), QJsonArray{ QJsonObject{
              { QStringLiteral("pairKey"), QStringLiteral("主角色→用户") },
              { QStringLiteral("roleA"), QStringLiteral("主角色") },
              { QStringLiteral("roleB"), QStringLiteral("用户") },
              { QStringLiteral("stage"), QStringLiteral("信任") },
              { QStringLiteral("attitude"), QStringLiteral("愿意继续合作") },
              { QStringLiteral("summary"), QStringLiteral("共同完成委托后建立了稳定信任") },
              { QStringLiteral("change"), QStringLiteral("本轮信任明显加深") },
          } } },
        { QStringLiteral("stages"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("stageKey"), QStringLiteral("trusted") },
              { QStringLiteral("state"), QJsonObject{ { QStringLiteral("active"), true } } },
          } } },
        { QStringLiteral("ledger"), QJsonArray{ QJsonObject{
              { QStringLiteral("entryType"), QStringLiteral("event") },
              { QStringLiteral("content"), QStringLiteral("完成咖啡馆委托") },
          } } },
        { QStringLiteral("storyTimeDelta"), QJsonObject{
              { QStringLiteral("changed"), true },
              { QStringLiteral("deltaSeconds"), 600 },
              { QStringLiteral("deltaText"), QStringLiteral("交谈经过十分钟") },
              { QStringLiteral("confidence"), QStringLiteral("high") },
              { QStringLiteral("reason"), QStringLiteral("对话明确持续十分钟") },
          } },
        { QStringLiteral("tags"), QJsonArray{ QJsonObject{
              { QStringLiteral("tag"), QStringLiteral("database.tag.runtime-signal") },
              { QStringLiteral("active"), true },
              { QStringLiteral("reason"), QStringLiteral("本轮事实信号") },
          } } },
    };
    const DatabaseOperationResult savedTurnResult = service.saveTurnResult(turnResult);
    if (!savedTurnResult.ok) {
        return fail(QStringLiteral("failed to save ready turn result: %1 / %2")
                        .arg(savedTurnResult.code, savedTurnResult.message)) ? 0 : 1;
    }

    const std::optional<DatabaseTurnView> readyView = service.turnById(pending.turnId);
    if (!readyView || readyView->turn.status != DatabaseTurnStatus::Ready || !readyView->hasDisplay
        || readyView->display.title.value(QStringLiteral("title")).toString() != QStringLiteral("状态标题")
        || readyView->display.title.value(QStringLiteral("scene")).toObject()
                .value(QStringLiteral("time")).toString() != QStringLiteral("2026年1月1日 08:10")) {
        return fail(QStringLiteral("ready turn should retain its structured display")) ? 0 : 1;
    }
    if (service.retryTurn(pending.turnId).ok) {
        return fail(QStringLiteral("ready turn must not be retryable")) ? 0 : 1;
    }
    const DatabaseOperationResult readyError = service.markTurnError(
        pending.turnId, QStringLiteral("provider_timeout"), QStringLiteral("late failure"), pending.attemptCount);
    if (readyError.ok || service.turnById(pending.turnId)->turn.status != DatabaseTurnStatus::Ready) {
        return fail(QStringLiteral("a late failure must not downgrade a ready turn")) ? 0 : 1;
    }
    const QList<int> firstTurnCounts{
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_state_snapshots")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_runtime_values")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_metric_history")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_state")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_history")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_stage_state")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_plot_ledger")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_story_time_history")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_stage_history")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_active_tags WHERE active = 1")),
        rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_turn_effects")),
    };
    if (firstTurnCounts != QList<int>{1, 1, 1, 1, 1, 1, 1, 2, 1, 3, 12}) {
        QStringList countTexts;
        for (int count : firstTurnCounts) countTexts.append(QString::number(count));
        return fail(QStringLiteral("ready turn should apply all runtime updates and record reversible effects: %1")
                        .arg(countTexts.join(QLatin1Char(',')))) ? 0 : 1;
    }
    const DatabaseRuntimeView runtime = service.runtimeView(pending.cardUid);
    if (runtime.snapshots.size() != 1 || runtime.characters.size() != 1
        || runtime.variables.size() != 1 || runtime.metricHistory.size() != 1
        || runtime.relationships.size() != 1 || runtime.relationshipHistory.size() != 1
        || runtime.stages.size() != 1 || runtime.ledger.size() != 1
        || runtime.variables.first().value(QStringLiteral("value")).toInt() != 42
        || runtime.metricHistory.first().value(QStringLiteral("delta")).toInt() != 2
        || runtime.metricHistory.first().value(QStringLiteral("reason")).toString() != QStringLiteral("共同完成委托")
        || runtime.relationships.first().value(QStringLiteral("stage")).toString() != QStringLiteral("信任")
        || runtime.relationshipHistory.first().value(QStringLiteral("change")).toString() != QStringLiteral("本轮信任明显加深")
        || runtime.stages.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("trusted")
        || runtime.storyTime.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-01-01 08:10:00")
        || runtime.stageHistory.size() != 1 || runtime.activeTags.size() != 3) {
        return fail(QStringLiteral("runtime view should expose the applied snapshot, values, stages and ledger")) ? 0 : 1;
    }

    DatabaseTurnRecord errorTurn;
    errorTurn.turnId = QStringLiteral("attempt-turn");
    errorTurn.cardUid = QStringLiteral("attempt-card");
    errorTurn.conversationId = QStringLiteral("attempt-conversation");
    errorTurn.messageId = QStringLiteral("attempt-message");
    errorTurn.turnIndex = 1;
    errorTurn.contentHash = QString(64, QLatin1Char('f'));
    errorTurn.workerModel = QStringLiteral("fast-model");
    if (!service.createPendingTurn(errorTurn).ok) {
        return fail(QStringLiteral("failed to create attempt test turn")) ? 0 : 1;
    }

    const QString secret = QStringLiteral("do-not-store-this-secret");
    if (!service.markTurnError(errorTurn.turnId, QStringLiteral("provider_network"),
            QStringLiteral("Bearer %1 timed out").arg(secret), errorTurn.attemptCount).ok) {
        return fail(QStringLiteral("failed to mark turn error")) ? 0 : 1;
    }
    const std::optional<DatabaseTurnView> errorView = service.turnById(errorTurn.turnId);
    if (!errorView || errorView->turn.status != DatabaseTurnStatus::Error
        || errorView->turn.errorMessage.contains(secret)) {
        return fail(QStringLiteral("error turn should redact bearer secrets")) ? 0 : 1;
    }
    if (!service.retryTurn(errorTurn.turnId).ok) {
        return fail(QStringLiteral("error turn should retry")) ? 0 : 1;
    }
    const std::optional<DatabaseTurnView> retriedView = service.turnById(errorTurn.turnId);
    if (!retriedView || retriedView->turn.status != DatabaseTurnStatus::Pending || retriedView->turn.attemptCount != 1) {
        return fail(QStringLiteral("retry should return the same turn to pending and increment attempt count")) ? 0 : 1;
    }
    DatabaseTurnResult staleAttemptResult;
    staleAttemptResult.display.turnId = errorTurn.turnId;
    staleAttemptResult.expectedAttemptCount = 0;
    staleAttemptResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{} },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("ledger"), QJsonArray{} },
    };
    const DatabaseOperationResult staleAttemptSave = service.saveTurnResult(staleAttemptResult);
    const DatabaseOperationResult staleAttemptError = service.markTurnError(
        errorTurn.turnId, QStringLiteral("provider_timeout"), QStringLiteral("old attempt failed"), 0);
    if (staleAttemptSave.ok || staleAttemptSave.code != QStringLiteral("stale_attempt")
        || staleAttemptError.ok || staleAttemptError.code != QStringLiteral("stale_attempt")
        || service.turnById(errorTurn.turnId)->turn.status != DatabaseTurnStatus::Pending) {
        return fail(QStringLiteral("attempt zero must not write success or failure after retry entered attempt one")) ? 0 : 1;
    }
    DatabaseTurnResult currentAttemptResult = staleAttemptResult;
    currentAttemptResult.expectedAttemptCount = 1;
    if (!service.saveTurnResult(currentAttemptResult).ok) {
        return fail(QStringLiteral("current retry attempt should save successfully")) ? 0 : 1;
    }
    const DatabaseOperationResult lateAttemptError = service.markTurnError(
        errorTurn.turnId, QStringLiteral("provider_timeout"), QStringLiteral("attempt zero arrived late"), 0);
    if (lateAttemptError.ok || lateAttemptError.code != QStringLiteral("stale_attempt")
        || service.turnById(errorTurn.turnId)->turn.status != DatabaseTurnStatus::Ready) {
        return fail(QStringLiteral("an old attempt failure must not downgrade the current ready turn")) ? 0 : 1;
    }

    if (!service.markMessageSuperseded(pending.cardUid, pending.messageId).ok) {
        return fail(QStringLiteral("failed to supersede turn")) ? 0 : 1;
    }
    const std::optional<DatabaseTurnView> supersededView = service.turnById(pending.turnId);
    if (!supersededView || supersededView->turn.status != DatabaseTurnStatus::Superseded
        || service.retryTurn(pending.turnId).ok || service.saveTurnResult(turnResult).ok) {
        return fail(QStringLiteral("superseded turn must not retry or accept a display")) ? 0 : 1;
    }
    if (!service.recentTurns(pending.cardUid).isEmpty()) {
        return fail(QStringLiteral("recent turns should hide superseded history")) ? 0 : 1;
    }
    if (rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_state_snapshots")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_runtime_values")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_metric_history")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_state")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_history")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_stage_state WHERE stage_key = 'start'")) != 1
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_plot_ledger")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_story_time_history")) != 1
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_stage_history")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_active_tags WHERE active = 1 AND tag = 'database.stage.main.start'")) != 1
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_active_tags WHERE active = 1 AND tag = 'database.tag.runtime-signal'")) != 0
        || rowCount(service.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_turn_effects WHERE reverted_at != ''")) != 12) {
        return fail(QStringLiteral("superseding a turn should revert all of its runtime updates")) ? 0 : 1;
    }
    const DatabaseRuntimeView revertedRuntime = service.runtimeView(pending.cardUid);
    if (!revertedRuntime.snapshots.isEmpty() || !revertedRuntime.characters.isEmpty()
        || !revertedRuntime.variables.isEmpty()
        || !revertedRuntime.metricHistory.isEmpty()
        || !revertedRuntime.relationships.isEmpty()
        || !revertedRuntime.relationshipHistory.isEmpty()
        || revertedRuntime.stages.size() != 1
        || revertedRuntime.stages.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("start")
        || !revertedRuntime.ledger.isEmpty()
        || revertedRuntime.storyTime.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-01-01 08:00:00")) {
        return fail(QStringLiteral("runtime view should not retain superseded turn data")) ? 0 : 1;
    }

    const QString orderedCard = QStringLiteral("ordered-card");
    DatabaseTurnRecord orderedFirst;
    orderedFirst.turnId = QStringLiteral("ordered-turn-1");
    orderedFirst.cardUid = orderedCard;
    orderedFirst.conversationId = QStringLiteral("ordered-conversation");
    orderedFirst.messageId = QStringLiteral("ordered-message-1");
    orderedFirst.turnIndex = 1;
    orderedFirst.contentHash = QString(64, QLatin1Char('b'));
    DatabaseTurnRecord orderedSecond = orderedFirst;
    orderedSecond.turnId = QStringLiteral("ordered-turn-2");
    orderedSecond.messageId = QStringLiteral("ordered-message-2");
    orderedSecond.turnIndex = 2;
    orderedSecond.contentHash = QString(64, QLatin1Char('c'));
    DatabaseTurnResult orderedFirstResult;
    orderedFirstResult.display.turnId = orderedFirst.turnId;
    orderedFirstResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("key"), QStringLiteral("score") },
              { QStringLiteral("value"), 10 },
          } } },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("ledger"), QJsonArray{} },
    };
    DatabaseTurnResult orderedSecondResult = orderedFirstResult;
    orderedSecondResult.display.turnId = orderedSecond.turnId;
    orderedSecondResult.updates.insert(QStringLiteral("variables"), QJsonArray{ QJsonObject{
        { QStringLiteral("roleId"), QStringLiteral("main") },
        { QStringLiteral("key"), QStringLiteral("score") },
        { QStringLiteral("value"), 20 },
    } });
    if (!service.createPendingTurn(orderedFirst).ok || !service.saveTurnResult(orderedFirstResult).ok
        || !service.createPendingTurn(orderedSecond).ok || !service.saveTurnResult(orderedSecondResult).ok) {
        return fail(QStringLiteral("failed to prepare ordered rollback turns")) ? 0 : 1;
    }
    const DatabaseOperationResult unsafeSingleRollback = service.markMessageSuperseded(
        orderedCard, orderedFirst.messageId);
    const DatabaseRuntimeView retainedOrderedRuntime = service.runtimeView(orderedCard);
    if (unsafeSingleRollback.ok || retainedOrderedRuntime.variables.size() != 1
        || retainedOrderedRuntime.variables.first().value(QStringLiteral("value")).toInt() != 20
        || service.turnById(orderedFirst.turnId)->turn.status != DatabaseTurnStatus::Ready
        || service.turnById(orderedSecond.turnId)->turn.status != DatabaseTurnStatus::Ready) {
        return fail(QStringLiteral("rolling back an older turn must not overwrite a newer runtime owner")) ? 0 : 1;
    }
    const DatabaseOperationResult orderedRollback = service.markMessagesSuperseded(
        orderedCard, QStringList{orderedFirst.messageId, orderedSecond.messageId});
    if (!orderedRollback.ok || orderedRollback.affectedRows != 2
        || !service.runtimeView(orderedCard).variables.isEmpty()
        || service.turnById(orderedFirst.turnId)->turn.status != DatabaseTurnStatus::Superseded
        || service.turnById(orderedSecond.turnId)->turn.status != DatabaseTurnStatus::Superseded) {
        return fail(QStringLiteral("batch supersede should roll back the newest turn first in one transaction: %1 / %2 / %3")
                        .arg(orderedRollback.code, orderedRollback.message)
                        .arg(orderedRollback.affectedRows)) ? 0 : 1;
    }
    const DatabaseOperationResult repeatedOrderedRollback = service.markMessagesSuperseded(
        orderedCard, QStringList{orderedFirst.messageId, orderedSecond.messageId});
    if (!repeatedOrderedRollback.ok || repeatedOrderedRollback.affectedRows != 0) {
        return fail(QStringLiteral("batch supersede should be idempotent")) ? 0 : 1;
    }

    const QString staleCard = QStringLiteral("stale-card");
    DatabaseTurnRecord staleFirst;
    staleFirst.turnId = QStringLiteral("stale-turn-1");
    staleFirst.cardUid = staleCard;
    staleFirst.conversationId = QStringLiteral("stale-conversation-old");
    staleFirst.messageId = QStringLiteral("stale-message-1");
    staleFirst.turnIndex = 8;
    staleFirst.contentHash = QString(64, QLatin1Char('d'));
    DatabaseTurnRecord staleSecond = staleFirst;
    staleSecond.turnId = QStringLiteral("stale-turn-2");
    staleSecond.conversationId = QStringLiteral("stale-conversation-new");
    staleSecond.messageId = QStringLiteral("stale-message-2");
    staleSecond.turnIndex = 1;
    staleSecond.contentHash = QString(64, QLatin1Char('e'));
    DatabaseTurnResult staleFirstResult;
    staleFirstResult.display.turnId = staleFirst.turnId;
    staleFirstResult.expectedAttemptCount = staleFirst.attemptCount;
    staleFirstResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("key"), QStringLiteral("score") },
              { QStringLiteral("value"), 1 },
          } } },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("ledger"), QJsonArray{} },
    };
    DatabaseTurnResult staleSecondResult = staleFirstResult;
    staleSecondResult.display.turnId = staleSecond.turnId;
    staleSecondResult.expectedAttemptCount = staleSecond.attemptCount;
    staleSecondResult.updates.insert(QStringLiteral("variables"), QJsonArray{ QJsonObject{
        { QStringLiteral("roleId"), QStringLiteral("main") },
        { QStringLiteral("key"), QStringLiteral("score") },
        { QStringLiteral("value"), 2 },
    } });
    if (!service.createPendingTurn(staleFirst).ok || !service.createPendingTurn(staleSecond).ok
        || !service.saveTurnResult(staleSecondResult).ok) {
        return fail(QStringLiteral("failed to prepare stale result ordering")) ? 0 : 1;
    }
    const DatabaseOperationResult staleSave = service.saveTurnResult(staleFirstResult);
    const DatabaseRuntimeView staleRuntime = service.runtimeView(staleCard);
    if (staleSave.ok || staleSave.code != QStringLiteral("stale_turn")
        || staleRuntime.variables.size() != 1
        || staleRuntime.variables.first().value(QStringLiteral("value")).toInt() != 2
        || service.turnById(staleFirst.turnId)->turn.status != DatabaseTurnStatus::Pending) {
        return fail(QStringLiteral("a late older result must not overwrite newer ready runtime state")) ? 0 : 1;
    }
    if (!service.markTurnError(
            staleFirst.turnId, QStringLiteral("provider_timeout"), QStringLiteral("late response"),
            staleFirst.attemptCount).ok) {
        return fail(QStringLiteral("failed to mark stale turn error")) ? 0 : 1;
    }
    const DatabaseOperationResult staleRetry = service.retryTurn(staleFirst.turnId);
    if (staleRetry.ok || staleRetry.code != QStringLiteral("stale_turn")
        || service.turnById(staleFirst.turnId)->turn.status != DatabaseTurnStatus::Error) {
        return fail(QStringLiteral("an older error turn must not retry after a newer active turn")) ? 0 : 1;
    }

    const QString connectionName = QStringLiteral("FantarealTurnRepositoryForeignKeyTest");
    bool foreignKeyRejected = false;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(service.paths().databasePath());
        if (database.open()) {
            QSqlQuery query(database);
            query.exec(QStringLiteral("PRAGMA foreign_keys = ON"));
            foreignKeyRejected = !query.exec(QStringLiteral(
                "INSERT INTO database_turn_displays (turn_id, title_json, record_json) VALUES ('missing', '{}', '{}')"));
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    if (!foreignKeyRejected) {
        return fail(QStringLiteral("turn display foreign key should reject orphan rows")) ? 0 : 1;
    }

    return 0;
}
