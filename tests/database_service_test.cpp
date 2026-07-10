#include "database/databasepaths.h"
#include "database/databaseservice.h"
#include "database/legacystatejournaladapter.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonObject>
#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QTemporaryDir>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

bool queryScalar(const QString& databasePath, const QString& sql, QString* value, QString* errorMessage) {
    const QString connectionName = QStringLiteral("FantarealDatabaseServiceTest");
    bool ok = false;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(databasePath);
        if (!database.open()) {
            if (errorMessage) {
                *errorMessage = database.lastError().text();
            }
        } else {
            QSqlQuery query(database);
            if (!query.exec(sql) || !query.next()) {
                if (errorMessage) {
                    *errorMessage = query.lastError().text();
                }
            } else {
                if (value) {
                    *value = query.value(0).toString();
                }
                ok = true;
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return ok;
}

bool prepareSchemaV2Database(const DatabasePaths& paths) {
    if (!QDir().mkpath(paths.directoryPath())) {
        return false;
    }
    const QString connectionName = QStringLiteral("FantarealDatabaseServiceMigrationFixture");
    bool ok = false;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths.databasePath());
        if (database.open()) {
            QSqlQuery query(database);
            const QStringList statements = {
                QStringLiteral("CREATE TABLE database_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"),
                QStringLiteral("INSERT INTO database_meta (key, value) VALUES ('schema_version', '2')"),
                QStringLiteral("CREATE TABLE database_state_snapshots (id TEXT PRIMARY KEY, card_uid TEXT NOT NULL, scope TEXT NOT NULL, title TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"),
                QStringLiteral("CREATE TABLE database_stage_state (id INTEGER PRIMARY KEY AUTOINCREMENT, card_uid TEXT NOT NULL, role_id TEXT NOT NULL, stage_key TEXT NOT NULL, state_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(card_uid, role_id, stage_key))"),
                QStringLiteral("CREATE TABLE database_plot_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, card_uid TEXT NOT NULL, entry_type TEXT NOT NULL, content TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"),
                QStringLiteral("INSERT INTO database_stage_state (card_uid, role_id, stage_key, state_json) VALUES ('card', 'main', 'start', '{\"active\":true}')"),
                QStringLiteral("INSERT INTO database_plot_ledger (card_uid, entry_type, content) VALUES ('card', 'event', 'legacy entry')"),
            };
            ok = true;
            for (const QString& statement : statements) {
                if (!query.exec(statement)) {
                    ok = false;
                    break;
                }
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return ok;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    DatabasePaths legacyPaths(tempDir.path());
    if (!prepareSchemaV2Database(legacyPaths)) {
        return fail(QStringLiteral("failed to prepare v2 database fixture")) ? 0 : 1;
    }

    DatabaseService service(tempDir.path());
    const DatabaseStatus status = service.ensureInitialized();
    if (!status.ok) {
        return fail(QStringLiteral("ensureInitialized failed: %1").arg(status.message)) ? 0 : 1;
    }

    const DatabasePaths paths = service.paths();
    if (DatabasePaths::directoryRelativePath() != QStringLiteral("data/database")
        || DatabasePaths::databaseRelativePath() != QStringLiteral("data/database/database.db")
        || DatabasePaths::databaseRelativePath().contains(QStringLiteral("state_journal"))) {
        return fail(QStringLiteral("DatabasePaths should expose the new database runtime path")) ? 0 : 1;
    }
    if (status.databasePath != paths.databasePath()
        || !QFileInfo::exists(paths.databasePath())
        || !QFileInfo(paths.directoryPath()).isDir()) {
        return fail(QStringLiteral("database file and runtime directory should be created")) ? 0 : 1;
    }
    if (status.schemaVersion != 5) {
        return fail(QStringLiteral("unexpected schema version")) ? 0 : 1;
    }

    QString errorMessage;
    QString schemaVersion;
    if (!queryScalar(paths.databasePath(),
            QStringLiteral("SELECT value FROM database_meta WHERE key = 'schema_version'"),
            &schemaVersion,
            &errorMessage)
        || schemaVersion != QStringLiteral("5")) {
        return fail(QStringLiteral("schema version meta missing: %1").arg(errorMessage)) ? 0 : 1;
    }

    for (const QString& expectedTable : {
             QStringLiteral("database_state_snapshots"),
             QStringLiteral("database_runtime_values"),
             QStringLiteral("database_metric_history"),
             QStringLiteral("database_relationship_state"),
             QStringLiteral("database_relationship_history"),
             QStringLiteral("database_turn_records"),
             QStringLiteral("database_turn_displays"),
             QStringLiteral("database_turn_effects"),
             QStringLiteral("database_story_time_state"),
             QStringLiteral("database_story_time_history"),
             QStringLiteral("database_stage_history"),
             QStringLiteral("database_active_tags"),
         }) {
        QString tableName;
        if (!queryScalar(paths.databasePath(),
                QStringLiteral("SELECT name FROM sqlite_master WHERE type = 'table' AND name = '%1'").arg(expectedTable),
                &tableName,
                &errorMessage)
            || tableName != expectedTable) {
            return fail(QStringLiteral("%1 table missing: %2").arg(expectedTable, errorMessage)) ? 0 : 1;
        }
    }
    QString migratedColumn;
    if (!queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM pragma_table_info('database_stage_state') WHERE name = 'updated_by_turn_id'"),
            &migratedColumn, &errorMessage)
        || migratedColumn != QStringLiteral("1")
        || !queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM pragma_table_info('database_plot_ledger') WHERE name = 'turn_id'"),
            &migratedColumn, &errorMessage)
        || migratedColumn != QStringLiteral("1")
        || !queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM database_stage_state WHERE stage_key = 'start'"),
            &migratedColumn, &errorMessage)
        || migratedColumn != QStringLiteral("1")
        || !queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM database_plot_ledger WHERE content = 'legacy entry'"),
            &migratedColumn, &errorMessage)
        || migratedColumn != QStringLiteral("1")) {
        return fail(QStringLiteral("v2 database should migrate to v5 without losing existing state")) ? 0 : 1;
    }

    if (DatabasePaths::workerSettingsRelativePath() != QStringLiteral("data/database/worker_settings.json")
        || paths.workerSettingsPath().endsWith(QStringLiteral("state_journal.db"))) {
        return fail(QStringLiteral("DatabaseWorker settings path should be independent from legacy state journal")) ? 0 : 1;
    }

    const QJsonObject databaseConfig{
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("role_id"), QStringLiteral("main") },
              { QStringLiteral("var_key"), QStringLiteral("affection") },
          } } },
        { QStringLiteral("stages"), QJsonArray{ QJsonObject{
              { QStringLiteral("role_id"), QStringLiteral("main") },
              { QStringLiteral("stage_key"), QStringLiteral("trusted") },
          } } },
        { QStringLiteral("tags"), QJsonArray{
              QJsonObject{ { QStringLiteral("tag"), QStringLiteral("database.tag.allowed") } },
              QJsonObject{ { QStringLiteral("tag"), QStringLiteral("database.tag.ledger") } },
          } },
    };
    QStringList updateWarnings;
    const QJsonObject updates = normalizeDatabaseUpdates(QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{
              QJsonObject{ { QStringLiteral("roleId"), QStringLiteral("main") },
                  { QStringLiteral("key"), QStringLiteral("affection") }, { QStringLiteral("value"), 10 } },
              QJsonObject{ { QStringLiteral("roleId"), QStringLiteral("main") },
                  { QStringLiteral("key"), QStringLiteral("invented") }, { QStringLiteral("value"), 1 } },
          } },
        { QStringLiteral("stages"), QJsonArray{
              QJsonObject{ { QStringLiteral("roleId"), QStringLiteral("main") },
                  { QStringLiteral("stageKey"), QStringLiteral("trusted") },
                  { QStringLiteral("state"), QJsonObject{ { QStringLiteral("active"), true } } } },
              QJsonObject{ { QStringLiteral("roleId"), QStringLiteral("main") },
                  { QStringLiteral("stageKey"), QStringLiteral("invented") },
                  { QStringLiteral("state"), QJsonObject{ { QStringLiteral("active"), true } } } },
          } },
        { QStringLiteral("ledger"), QJsonArray{ QJsonObject{
              { QStringLiteral("entryType"), QStringLiteral("clue") },
              { QStringLiteral("content"), QStringLiteral("发现新的线索") },
              { QStringLiteral("activationTag"), QStringLiteral("database.tag.ledger") },
          } } },
        { QStringLiteral("relationships"), QJsonArray{ QJsonObject{
              { QStringLiteral("pair_key"), QStringLiteral("main→user") },
              { QStringLiteral("role_a"), QStringLiteral("主角色") },
              { QStringLiteral("role_b"), QStringLiteral("用户") },
              { QStringLiteral("stage"), QStringLiteral("信任") },
              { QStringLiteral("attitude"), QStringLiteral("愿意坦诚交流") },
              { QStringLiteral("summary"), QStringLiteral("双方建立了稳定信任") },
              { QStringLiteral("change"), QStringLiteral("共同处理危机后信任加深") },
          } } },
        { QStringLiteral("story_time_delta"), QJsonObject{
              { QStringLiteral("delta_seconds"), 300 },
              { QStringLiteral("confidence"), QStringLiteral("high") },
          } },
        { QStringLiteral("tags"), QJsonArray{
              QJsonObject{ { QStringLiteral("tag"), QStringLiteral("database.tag.allowed") },
                  { QStringLiteral("active"), true } },
              QJsonObject{ { QStringLiteral("tag"), QStringLiteral("database.stage.main.trusted") },
                  { QStringLiteral("active"), true } },
          } },
    }, databaseConfig, &updateWarnings);
    if (updates.value(QStringLiteral("variables")).toArray().size() != 1
        || updates.value(QStringLiteral("relationships")).toArray().size() != 1
        || updates.value(QStringLiteral("relationships")).toArray().at(0).toObject()
                .value(QStringLiteral("pairKey")).toString() != QStringLiteral("main→user")
        || !updates.value(QStringLiteral("stages")).toArray().isEmpty()
        || updates.value(QStringLiteral("tags")).toArray().size() != 2
        || updates.value(QStringLiteral("tags")).toArray().at(1).toObject()
                .value(QStringLiteral("sourceType")).toString() != QStringLiteral("ledger")
        || updates.value(QStringLiteral("storyTimeDelta")).toObject().value(QStringLiteral("deltaSeconds")).toInt() != 300
        || updateWarnings.size() != 3) {
        return fail(QStringLiteral("update contract should normalize durable relationships and keep Worker inside controlled runtime fields")) ? 0 : 1;
    }

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("enabled"), false);
    stateJournal.insert(QStringLiteral("unknown_state_field"), QStringLiteral("state-stays"));

    QJsonObject raw;
    raw.insert(QStringLiteral("stateJournal"), stateJournal);

    if (LegacyStateJournalAdapter::legacyDatabaseRelativePath() != QStringLiteral("data/mods/state_journal/state_journal.db")
        || !LegacyStateJournalAdapter::legacyStageTagPrefix().startsWith(QStringLiteral("state_journal.stage."))
        || !LegacyStateJournalAdapter::hasStateJournal(raw)
        || LegacyStateJournalAdapter::databaseEnabled(raw, true)) {
        return fail(QStringLiteral("legacy stateJournal adapter should read old compatibility fields")) ? 0 : 1;
    }

    const QJsonObject updatedRaw = LegacyStateJournalAdapter::applyDatabaseEnabled(raw, true);
    const QJsonObject updatedStateJournal = updatedRaw.value(QStringLiteral("stateJournal")).toObject();
    if (!updatedStateJournal.value(QStringLiteral("enabled")).toBool(false)
        || updatedStateJournal.value(QStringLiteral("unknown_state_field")).toString() != QStringLiteral("state-stays")) {
        return fail(QStringLiteral("legacy stateJournal adapter should preserve nested old fields")) ? 0 : 1;
    }

    const QJsonObject initializationConfig{
        { QStringLiteral("enabled"), true },
        { QStringLiteral("roles"), QJsonArray{
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("main") },
                  { QStringLiteral("enabled"), true },
                  { QStringLiteral("mode"), QStringLiteral("full") },
                  { QStringLiteral("initial_stage"), QStringLiteral("start") },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("snapshot") },
                  { QStringLiteral("enabled"), true },
                  { QStringLiteral("mode"), QStringLiteral("snapshot_only") },
                  { QStringLiteral("initial_stage"), QStringLiteral("ignored") },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("disabled") },
                  { QStringLiteral("enabled"), false },
                  { QStringLiteral("mode"), QStringLiteral("disabled") },
              },
          } },
        { QStringLiteral("variables"), QJsonArray{
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("main") },
                  { QStringLiteral("var_key"), QStringLiteral("affection") },
                  { QStringLiteral("var_name"), QStringLiteral("好感度") },
                  { QStringLiteral("default_value"), 10 },
                  { QStringLiteral("max_value"), 100 },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("snapshot") },
                  { QStringLiteral("var_key"), QStringLiteral("ignored") },
                  { QStringLiteral("default_value"), 1 },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("disabled") },
                  { QStringLiteral("var_key"), QStringLiteral("disabled_value") },
                  { QStringLiteral("default_value"), 1 },
              },
          } },
        { QStringLiteral("stages"), QJsonArray{
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("main") },
                  { QStringLiteral("stage_key"), QStringLiteral("start") },
                  { QStringLiteral("stage_name"), QStringLiteral("初始阶段") },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("snapshot") },
                  { QStringLiteral("stage_key"), QStringLiteral("ignored") },
              },
          } },
        { QStringLiteral("snapshotFields"), QJsonArray{
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("main") },
                  { QStringLiteral("key"), QStringLiteral("location") },
                  { QStringLiteral("initial_value"), QStringLiteral("咖啡馆") },
                  { QStringLiteral("scope"), QStringLiteral("current") },
                  { QStringLiteral("snapshot_title"), QStringLiteral("初始状态") },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("snapshot") },
                  { QStringLiteral("key"), QStringLiteral("outfit") },
                  { QStringLiteral("initial_value"), QStringLiteral("常服") },
                  { QStringLiteral("scope"), QStringLiteral("snapshot-only") },
              },
              QJsonObject{
                  { QStringLiteral("role_id"), QStringLiteral("main") },
                  { QStringLiteral("key"), QStringLiteral("no_default") },
              },
          } },
    };
    const DatabaseOperationResult initialized = service.initializeRuntime(QStringLiteral("init-card"), initializationConfig);
    if (!initialized.ok || initialized.affectedRows != 6) {
        return fail(QStringLiteral("runtime initialization should create variables, the initial stage, and explicit snapshots")) ? 0 : 1;
    }
    const DatabaseRuntimeView initializedRuntime = service.runtimeView(QStringLiteral("init-card"));
    if (initializedRuntime.variables.size() != 1 || initializedRuntime.stages.size() != 1
        || initializedRuntime.snapshots.size() != 2
        || initializedRuntime.activeTags.size() != 1
        || initializedRuntime.storyTime.isEmpty()
        || initializedRuntime.variables.first().value(QStringLiteral("value")).toInt(-1) != 10
        || initializedRuntime.stages.first().value(QStringLiteral("stageKey")).toString() != QStringLiteral("start")) {
        return fail(QStringLiteral("runtime initialization should respect role modes and configured defaults")) ? 0 : 1;
    }
    if (!queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM database_turn_records WHERE card_uid = 'init-card'"),
            &schemaVersion, &errorMessage)
        || schemaVersion != QStringLiteral("0")
        || !queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM database_metric_history WHERE card_uid = 'init-card'"),
            &schemaVersion, &errorMessage)
        || schemaVersion != QStringLiteral("0")
        || !queryScalar(paths.databasePath(),
            QStringLiteral("SELECT COUNT(*) FROM database_turn_effects"),
            &schemaVersion, &errorMessage)
        || schemaVersion != QStringLiteral("0")) {
        return fail(QStringLiteral("runtime initialization must not create turn or rollback history")) ? 0 : 1;
    }

    DatabaseTurnRecord preservedValueTurn;
    preservedValueTurn.turnId = QStringLiteral("preserved-initialization-value");
    preservedValueTurn.cardUid = QStringLiteral("init-card");
    preservedValueTurn.conversationId = QStringLiteral("init-conversation");
    preservedValueTurn.messageId = QStringLiteral("init-message");
    preservedValueTurn.contentHash = QString(64, QLatin1Char('i'));
    if (!service.createPendingTurn(preservedValueTurn).ok) {
        return fail(QStringLiteral("failed to create a turn for retained-value verification")) ? 0 : 1;
    }
    DatabaseTurnResult preservedValueResult;
    preservedValueResult.display.turnId = preservedValueTurn.turnId;
    preservedValueResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("key"), QStringLiteral("affection") },
              { QStringLiteral("value"), 42 },
          } } },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("ledger"), QJsonArray{} },
    };
    if (!service.saveTurnResult(preservedValueResult).ok) {
        return fail(QStringLiteral("failed to seed a retained runtime value")) ? 0 : 1;
    }
    const DatabaseOperationResult repeatedInitialization = service.initializeRuntime(
        QStringLiteral("init-card"), initializationConfig);
    const DatabaseRuntimeView retainedRuntime = service.runtimeView(QStringLiteral("init-card"));
    if (!repeatedInitialization.ok || repeatedInitialization.affectedRows != 0
        || retainedRuntime.variables.first().value(QStringLiteral("value")).toInt(-1) != 42) {
        return fail(QStringLiteral("runtime initialization should not overwrite existing values")) ? 0 : 1;
    }

    QJsonObject extendedInitializationConfig = initializationConfig;
    QJsonArray extendedSnapshotFields = extendedInitializationConfig.value(QStringLiteral("snapshotFields")).toArray();
    extendedSnapshotFields.append(QJsonObject{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("key"), QStringLiteral("mood") },
        { QStringLiteral("initial_value"), QStringLiteral("平静") },
        { QStringLiteral("scope"), QStringLiteral("current") },
    });
    extendedInitializationConfig.insert(QStringLiteral("snapshotFields"), extendedSnapshotFields);
    const DatabaseOperationResult extendedInitialization = service.initializeRuntime(
        QStringLiteral("init-card"), extendedInitializationConfig);
    const DatabaseRuntimeView extendedRuntime = service.runtimeView(QStringLiteral("init-card"));
    QJsonObject currentSnapshotPayload;
    for (const QJsonObject& snapshot : extendedRuntime.snapshots) {
        if (snapshot.value(QStringLiteral("scope")).toString() == QStringLiteral("current")) {
            currentSnapshotPayload = snapshot.value(QStringLiteral("payload")).toObject();
            break;
        }
    }
    if (!extendedInitialization.ok || extendedInitialization.affectedRows != 1
        || currentSnapshotPayload.value(QStringLiteral("location")).toString() != QStringLiteral("咖啡馆")
        || currentSnapshotPayload.value(QStringLiteral("mood")).toString() != QStringLiteral("平静")) {
        return fail(QStringLiteral("runtime initialization should add missing fields to an existing snapshot scope")) ? 0 : 1;
    }

    const DatabaseDebugTableView debugValues = service.debugTable(
        QStringLiteral("database_runtime_values"), QStringLiteral("init-card"), 0, 20);
    if (!debugValues.ok || debugValues.totalRows != 1 || debugValues.rows.size() != 1
        || !debugValues.columns.contains(QStringLiteral("value_json"))
        || debugValues.rows.first().value(QStringLiteral("value_json")).toObject()
                .value(QStringLiteral("value")).toInt(-1) != 42) {
        return fail(QStringLiteral("diagnostic table reads should be card-scoped and parse JSON cells")) ? 0 : 1;
    }
    const DatabaseDebugTableView rejectedDebug = service.debugTable(
        QStringLiteral("sqlite_master"), QStringLiteral("init-card"), 0, 20);
    if (rejectedDebug.ok || rejectedDebug.message.isEmpty()) {
        return fail(QStringLiteral("diagnostic table reads must reject tables outside the whitelist")) ? 0 : 1;
    }

    return 0;
}
