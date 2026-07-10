#include "database/databaserepository.h"
#include "database/databaserules.h"

#include <QFileInfo>
#include <QHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QMap>
#include <QRegularExpression>
#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QSqlRecord>
#include <QStringList>
#include <QUuid>
#include <QVariant>

#include <utility>

namespace {
constexpr int kDatabaseSchemaVersion = 5;

QString makeConnectionName() {
    return QStringLiteral("FantarealDatabase_%1").arg(QUuid::createUuid().toString(QUuid::Id128));
}

bool execSchemaStatement(QSqlQuery& query, const QString& sql, QString* errorMessage) {
    if (query.exec(sql)) {
        return true;
    }
    if (errorMessage) {
        *errorMessage = QStringLiteral("%1: %2").arg(query.lastError().text(), sql.simplified());
    }
    return false;
}

QStringList coreTableNames() {
    return {
        QStringLiteral("database_meta"),
        QStringLiteral("database_state_snapshots"),
        QStringLiteral("database_runtime_values"),
        QStringLiteral("database_metric_history"),
        QStringLiteral("database_relationship_state"),
        QStringLiteral("database_relationship_history"),
        QStringLiteral("database_stage_state"),
        QStringLiteral("database_stage_history"),
        QStringLiteral("database_story_time_state"),
        QStringLiteral("database_story_time_history"),
        QStringLiteral("database_active_tags"),
        QStringLiteral("database_plot_ledger"),
        QStringLiteral("database_turn_records"),
        QStringLiteral("database_turn_displays"),
        QStringLiteral("database_turn_effects"),
    };
}

struct DebugTableSpec {
    QString selectSql;
    QString countSql;
    bool requiresCardUid{};
};

std::optional<DebugTableSpec> debugTableSpec(const QString& tableName) {
    if (!coreTableNames().contains(tableName)) {
        return std::nullopt;
    }
    if (tableName == QStringLiteral("database_meta")) {
        return DebugTableSpec{
            QStringLiteral("SELECT m.* FROM database_meta m ORDER BY m.rowid DESC LIMIT ? OFFSET ?"),
            QStringLiteral("SELECT COUNT(*) FROM database_meta"),
            false,
        };
    }
    if (tableName == QStringLiteral("database_turn_displays")) {
        return DebugTableSpec{
            QStringLiteral(R"sql(
                SELECT d.* FROM database_turn_displays d
                INNER JOIN database_turn_records r ON r.turn_id = d.turn_id
                WHERE r.card_uid = ?
                ORDER BY r.rowid DESC LIMIT ? OFFSET ?
            )sql"),
            QStringLiteral(R"sql(
                SELECT COUNT(*) FROM database_turn_displays d
                INNER JOIN database_turn_records r ON r.turn_id = d.turn_id
                WHERE r.card_uid = ?
            )sql"),
            true,
        };
    }
    if (tableName == QStringLiteral("database_turn_effects")) {
        return DebugTableSpec{
            QStringLiteral(R"sql(
                SELECT e.* FROM database_turn_effects e
                INNER JOIN database_turn_records r ON r.turn_id = e.turn_id
                WHERE r.card_uid = ?
                ORDER BY e.rowid DESC LIMIT ? OFFSET ?
            )sql"),
            QStringLiteral(R"sql(
                SELECT COUNT(*) FROM database_turn_effects e
                INNER JOIN database_turn_records r ON r.turn_id = e.turn_id
                WHERE r.card_uid = ?
            )sql"),
            true,
        };
    }
    return DebugTableSpec{
        QStringLiteral("SELECT t.* FROM %1 t WHERE t.card_uid = ? ORDER BY t.rowid DESC LIMIT ? OFFSET ?")
            .arg(tableName),
        QStringLiteral("SELECT COUNT(*) FROM %1 t WHERE t.card_uid = ?").arg(tableName),
        true,
    };
}

QJsonValue debugCellValue(const QString& columnName, const QVariant& value) {
    if (!value.isValid() || value.isNull()) {
        return QJsonValue::Null;
    }
    if (columnName.endsWith(QStringLiteral("_json"))) {
        QJsonParseError error;
        const QJsonDocument document = QJsonDocument::fromJson(value.toString().toUtf8(), &error);
        if (error.error == QJsonParseError::NoError) {
            if (document.isObject()) {
                return document.object();
            }
            if (document.isArray()) {
                return document.array();
            }
        }
    }
    return QJsonValue::fromVariant(value);
}

DatabaseOperationResult failure(const QString& code, const QString& message, const QString& turnId = {}) {
    return {false, code, message, turnId};
}

DatabaseOperationResult success(const QString& message, const QString& turnId, int affectedRows = 0) {
    return {true, {}, message, turnId, affectedRows};
}

QString sanitizeErrorMessage(QString message) {
    message.replace(QRegularExpression(QStringLiteral("(Bearer\\s+)[^\\s]+"), QRegularExpression::CaseInsensitiveOption),
        QStringLiteral("\\1[REDACTED]"));
    message.replace(QRegularExpression(QStringLiteral("(api[_ -]?key\\s*[:=]\\s*)[^\\s,;]+"), QRegularExpression::CaseInsensitiveOption),
        QStringLiteral("\\1[REDACTED]"));
    return message.simplified().left(600);
}

QString normalizedWarnings(const QString& warningsJson) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(warningsJson.trimmed().toUtf8(), &error);
    if (error.error != QJsonParseError::NoError || !document.isArray()) {
        return QStringLiteral("[]");
    }
    return QString::fromUtf8(document.toJson(QJsonDocument::Compact));
}

QString sqlText(QString value) {
    return value.isNull() ? QStringLiteral("") : value;
}

QJsonObject jsonObject(const QVariant& value) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(value.toByteArray(), &error);
    return error.error == QJsonParseError::NoError && document.isObject() ? document.object() : QJsonObject{};
}

QJsonValue wrappedJsonValue(const QVariant& value) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(value.toByteArray(), &error);
    return error.error == QJsonParseError::NoError && document.isObject()
        ? document.object().value(QStringLiteral("value"))
        : QJsonValue{};
}

DatabaseTurnView turnViewFromQuery(const QSqlQuery& query) {
    DatabaseTurnView view;
    view.turn.turnId = query.value(0).toString();
    view.turn.cardUid = query.value(1).toString();
    view.turn.conversationId = query.value(2).toString();
    view.turn.messageId = query.value(3).toString();
    view.turn.turnIndex = query.value(4).toInt();
    view.turn.contentHash = query.value(5).toString();
    view.turn.status = databaseTurnStatusFromString(query.value(6).toString());
    view.turn.triggerSource = query.value(7).toString();
    view.turn.workerModel = query.value(8).toString();
    view.turn.attemptCount = query.value(9).toInt();
    view.turn.errorCode = query.value(10).toString();
    view.turn.errorMessage = query.value(11).toString();
    view.turn.warningsJson = query.value(12).toString();
    view.turn.createdAt = query.value(13).toString();
    view.turn.updatedAt = query.value(14).toString();
    view.turn.completedAt = query.value(15).toString();
    view.hasDisplay = !query.value(16).isNull();
    if (view.hasDisplay) {
        view.display.turnId = view.turn.turnId;
        view.display.title = jsonObject(query.value(17));
        view.display.record = jsonObject(query.value(18));
        view.display.createdAt = query.value(19).toString();
        view.display.updatedAt = query.value(20).toString();
        view.display.workerModel = view.turn.workerModel;
        view.display.warningsJson = view.turn.warningsJson;
    }
    return view;
}

QString turnSelectSql() {
    return QStringLiteral(R"sql(
        SELECT r.turn_id, r.card_uid, r.conversation_id, r.message_id,
               r.turn_index, r.content_hash, r.status, r.trigger_source,
               r.worker_model, r.attempt_count, r.error_code, r.error_message,
               r.warnings_json, r.created_at, r.updated_at, r.completed_at,
               d.turn_id, d.title_json, d.record_json, d.created_at, d.updated_at
        FROM database_turn_records r
        LEFT JOIN database_turn_displays d ON d.turn_id = r.turn_id
    )sql");
}

bool createBaselineSchema(QSqlQuery& query, QString* errorMessage) {
    const QStringList statements = {
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_state_snapshots (
                id TEXT PRIMARY KEY,
                card_uid TEXT NOT NULL,
                scope TEXT NOT NULL,
                title TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_stage_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                role_id TEXT NOT NULL,
                stage_key TEXT NOT NULL,
                state_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(card_uid, role_id, stage_key)
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_plot_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                entry_type TEXT NOT NULL,
                content TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_turn_records (
                turn_id TEXT PRIMARY KEY,
                card_uid TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL DEFAULT 0,
                content_hash TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'ready', 'error', 'superseded')),
                trigger_source TEXT NOT NULL DEFAULT 'chat_complete',
                worker_model TEXT NOT NULL DEFAULT '',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                warnings_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT NOT NULL DEFAULT '',
                UNIQUE(card_uid, message_id)
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_turn_records_conversation
            ON database_turn_records(card_uid, conversation_id, turn_index)
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_turn_records_status
            ON database_turn_records(card_uid, status, updated_at)
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_turn_displays (
                turn_id TEXT PRIMARY KEY,
                title_json TEXT NOT NULL DEFAULT '{}',
                record_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES database_turn_records(turn_id) ON DELETE CASCADE
            )
        )sql"),
    };
    for (const QString& statement : statements) {
        if (!execSchemaStatement(query, statement, errorMessage)) {
            return false;
        }
    }
    return true;
}

bool tableHasColumn(QSqlDatabase& database, const QString& tableName, const QString& columnName,
    QString* errorMessage) {
    QSqlQuery query(database);
    if (!query.exec(QStringLiteral("PRAGMA table_info(%1)").arg(tableName))) {
        if (errorMessage) {
            *errorMessage = query.lastError().text();
        }
        return false;
    }
    while (query.next()) {
        if (query.value(1).toString() == columnName) {
            return true;
        }
    }
    return false;
}

bool addColumnIfMissing(QSqlDatabase& database, const QString& tableName, const QString& columnDefinition,
    QString* errorMessage) {
    const QString columnName = columnDefinition.section(QLatin1Char(' '), 0, 0);
    if (tableHasColumn(database, tableName, columnName, errorMessage)) {
        return true;
    }
    QSqlQuery query(database);
    return execSchemaStatement(query,
        QStringLiteral("ALTER TABLE %1 ADD COLUMN %2").arg(tableName, columnDefinition), errorMessage);
}

std::optional<int> storedSchemaVersion(QSqlDatabase& database, QString* errorMessage) {
    QSqlQuery query(database);
    if (!query.exec(QStringLiteral("SELECT value FROM database_meta WHERE key = 'schema_version'"))) {
        if (errorMessage) {
            *errorMessage = query.lastError().text();
        }
        return std::nullopt;
    }
    if (!query.next()) {
        return 2;
    }
    bool ok = false;
    const int version = query.value(0).toString().toInt(&ok);
    if (!ok || version < 1) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("database schema version is invalid");
        }
        return std::nullopt;
    }
    return version;
}

bool storeSchemaVersion(QSqlDatabase& database, int version, QString* errorMessage) {
    QSqlQuery query(database);
    query.prepare(QStringLiteral(R"sql(
        INSERT INTO database_meta (key, value, updated_at)
        VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
    )sql"));
    query.addBindValue(QString::number(version));
    if (query.exec()) {
        return true;
    }
    if (errorMessage) {
        *errorMessage = query.lastError().text();
    }
    return false;
}

bool migrateToSchemaV3(QSqlDatabase& database, QString* errorMessage) {
    if (!addColumnIfMissing(database, QStringLiteral("database_state_snapshots"),
            QStringLiteral("updated_by_turn_id TEXT NOT NULL DEFAULT ''"), errorMessage)
        || !addColumnIfMissing(database, QStringLiteral("database_stage_state"),
            QStringLiteral("updated_by_turn_id TEXT NOT NULL DEFAULT ''"), errorMessage)
        || !addColumnIfMissing(database, QStringLiteral("database_plot_ledger"),
            QStringLiteral("turn_id TEXT NOT NULL DEFAULT ''"), errorMessage)) {
        return false;
    }

    QSqlQuery query(database);
    const QStringList statements = {
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_runtime_values (
                card_uid TEXT NOT NULL,
                role_id TEXT NOT NULL,
                field_key TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                value_json TEXT NOT NULL,
                maximum_json TEXT NOT NULL DEFAULT '',
                updated_by_turn_id TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(card_uid, role_id, field_key)
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_metric_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                role_id TEXT NOT NULL,
                field_key TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                value_json TEXT NOT NULL,
                maximum_json TEXT NOT NULL DEFAULT '',
                delta_json TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                turn_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES database_turn_records(turn_id) ON DELETE CASCADE
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_metric_history_turn
            ON database_metric_history(turn_id, id)
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_turn_effects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                target_json TEXT NOT NULL DEFAULT '{}',
                before_json TEXT NOT NULL DEFAULT '{}',
                after_json TEXT NOT NULL DEFAULT '{}',
                reverted_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(turn_id, sequence),
                FOREIGN KEY (turn_id) REFERENCES database_turn_records(turn_id) ON DELETE CASCADE
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_turn_effects_turn
            ON database_turn_effects(turn_id, reverted_at, sequence)
        )sql"),
    };
    for (const QString& statement : statements) {
        if (!execSchemaStatement(query, statement, errorMessage)) {
            return false;
        }
    }
    return true;
}

bool migrateToSchemaV4(QSqlDatabase& database, QString* errorMessage) {
    QSqlQuery query(database);
    const QStringList statements = {
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_story_time_state (
                card_uid TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0,
                show_in_record INTEGER NOT NULL DEFAULT 1,
                base_time TEXT NOT NULL DEFAULT '',
                current_time TEXT NOT NULL DEFAULT '',
                elapsed_seconds INTEGER NOT NULL DEFAULT 0,
                season TEXT NOT NULL DEFAULT '',
                time_slot TEXT NOT NULL DEFAULT '',
                advance_mode TEXT NOT NULL DEFAULT 'smart',
                custom_advance_type TEXT NOT NULL DEFAULT 'range',
                custom_advance_min_seconds INTEGER NOT NULL DEFAULT 300,
                custom_advance_max_seconds INTEGER NOT NULL DEFAULT 900,
                display_mode TEXT NOT NULL DEFAULT 'datetime_minute',
                last_delta_seconds INTEGER NOT NULL DEFAULT 0,
                last_delta_text TEXT NOT NULL DEFAULT '',
                last_confidence TEXT NOT NULL DEFAULT '',
                updated_by_turn_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_story_time_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                turn_id TEXT NOT NULL DEFAULT '',
                message_id TEXT NOT NULL DEFAULT '',
                turn_ordinal INTEGER NOT NULL DEFAULT 0,
                old_time TEXT NOT NULL DEFAULT '',
                new_time TEXT NOT NULL DEFAULT '',
                delta_seconds INTEGER NOT NULL DEFAULT 0,
                delta_text TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'worker',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_story_time_history_card
            ON database_story_time_history(card_uid, id DESC)
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_stage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                turn_id TEXT NOT NULL,
                turn_ordinal INTEGER NOT NULL DEFAULT 0,
                role_id TEXT NOT NULL,
                role_name TEXT NOT NULL DEFAULT '',
                from_stage_key TEXT NOT NULL DEFAULT '',
                from_stage_name TEXT NOT NULL DEFAULT '',
                to_stage_key TEXT NOT NULL,
                to_stage_name TEXT NOT NULL DEFAULT '',
                trigger_values_json TEXT NOT NULL DEFAULT '{}',
                reason TEXT NOT NULL DEFAULT '',
                active_tag TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES database_turn_records(turn_id) ON DELETE CASCADE
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_stage_history_card
            ON database_stage_history(card_uid, id DESC)
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_active_tags (
                card_uid TEXT NOT NULL,
                tag TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_key TEXT NOT NULL DEFAULT '',
                label TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                updated_by_turn_id TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(card_uid, tag)
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_active_tags_card
            ON database_active_tags(card_uid, active, source_type)
        )sql"),
    };
    for (const QString& statement : statements) {
        if (!execSchemaStatement(query, statement, errorMessage)) {
            return false;
        }
    }
    return true;
}

bool migrateToSchemaV5(QSqlDatabase& database, QString* errorMessage) {
    QSqlQuery query(database);
    const QStringList statements = {
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_relationship_state (
                card_uid TEXT NOT NULL,
                pair_key TEXT NOT NULL,
                role_a TEXT NOT NULL DEFAULT '',
                role_b TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT '',
                attitude TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                updated_by_turn_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(card_uid, pair_key)
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE TABLE IF NOT EXISTS database_relationship_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_uid TEXT NOT NULL,
                turn_id TEXT NOT NULL,
                pair_key TEXT NOT NULL,
                role_a TEXT NOT NULL DEFAULT '',
                role_b TEXT NOT NULL DEFAULT '',
                previous_stage TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT '',
                attitude TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                change_text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (turn_id) REFERENCES database_turn_records(turn_id) ON DELETE CASCADE
            )
        )sql"),
        QStringLiteral(R"sql(
            CREATE INDEX IF NOT EXISTS idx_database_relationship_history_card
            ON database_relationship_history(card_uid, id DESC)
        )sql"),
    };
    for (const QString& statement : statements) {
        if (!execSchemaStatement(query, statement, errorMessage)) {
            return false;
        }
    }
    return true;
}
}

DatabaseRepository::DatabaseRepository(DatabasePaths paths)
    : paths_(std::move(paths)) {
}

DatabaseStatus DatabaseRepository::initializeSchema() const {
    DatabaseStatus status;
    status.databasePath = paths_.databasePath();
    status.schemaVersion = kDatabaseSchemaVersion;

    QString errorMessage;
    if (!paths_.ensureRuntimeDirectory(&errorMessage)) {
        status.message = errorMessage;
        return status;
    }

    const QString connectionName = makeConnectionName();
    bool initialized = false;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(status.databasePath);

        if (!database.open()) {
            errorMessage = QStringLiteral("failed to open database: %1").arg(database.lastError().text());
        } else {
            QSqlQuery pragma(database);
            if (!pragma.exec(QStringLiteral("PRAGMA foreign_keys = ON"))) {
                errorMessage = QStringLiteral("failed to enable database foreign keys: %1").arg(pragma.lastError().text());
            } else if (!database.transaction()) {
                errorMessage = QStringLiteral("failed to start database transaction: %1").arg(database.lastError().text());
            } else {
                QSqlQuery query(database);
                bool statementsOk = createBaselineSchema(query, &errorMessage);
                const std::optional<int> storedVersion = statementsOk ? storedSchemaVersion(database, &errorMessage) : std::nullopt;
                if (statementsOk && !storedVersion) {
                    statementsOk = false;
                }
                if (statementsOk && *storedVersion > kDatabaseSchemaVersion) {
                    errorMessage = QStringLiteral("database schema version %1 is newer than this application")
                                       .arg(*storedVersion);
                    statementsOk = false;
                }
                if (statementsOk) {
                    statementsOk = migrateToSchemaV3(database, &errorMessage);
                }
                if (statementsOk) {
                    statementsOk = migrateToSchemaV4(database, &errorMessage);
                }
                if (statementsOk) {
                    statementsOk = migrateToSchemaV5(database, &errorMessage);
                }
                if (statementsOk) {
                    statementsOk = storeSchemaVersion(database, kDatabaseSchemaVersion, &errorMessage);
                }
                if (statementsOk && !database.commit()) {
                    errorMessage = QStringLiteral("failed to commit database schema: %1").arg(database.lastError().text());
                    statementsOk = false;
                }
                if (!statementsOk) {
                    database.rollback();
                }
                initialized = statementsOk;
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);

    status.ok = initialized;
    status.message = initialized ? QStringLiteral("database schema initialized") : errorMessage;
    return status;
}

DatabaseOverview DatabaseRepository::describe() const {
    DatabaseOverview overview;
    overview.status = initializeSchema();
    overview.rootPath = paths_.rootPath();
    overview.directoryPath = paths_.directoryPath();
    overview.relativePath = DatabasePaths::databaseRelativePath();

    const QFileInfo databaseFile(paths_.databasePath());
    overview.fileExists = databaseFile.exists();
    overview.fileSizeBytes = databaseFile.exists() ? databaseFile.size() : 0;
    overview.tableNames = coreTableNames();
    for (const QString& tableName : overview.tableNames) {
        overview.tableCounts.insert(tableName, 0);
    }
    if (!overview.status.ok || !overview.fileExists) {
        return overview;
    }

    const QString connectionName = makeConnectionName();
    QString errorMessage;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(overview.status.databasePath);
        if (!database.open()) {
            errorMessage = QStringLiteral("failed to open database for overview: %1").arg(database.lastError().text());
        } else {
            QSqlQuery query(database);
            for (const QString& tableName : overview.tableNames) {
                if (!query.exec(QStringLiteral("SELECT COUNT(*) FROM %1").arg(tableName)) || !query.next()) {
                    errorMessage = QStringLiteral("failed to count %1: %2").arg(tableName, query.lastError().text());
                    break;
                }
                overview.tableCounts.insert(tableName, query.value(0).toInt());
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    if (!errorMessage.isEmpty()) {
        overview.status.ok = false;
        overview.status.message = errorMessage;
    }
    return overview;
}

DatabaseOperationResult DatabaseRepository::createPendingTurn(const DatabaseTurnRecord& record) const {
    if (record.turnId.trimmed().isEmpty() || record.cardUid.trimmed().isEmpty()
        || record.conversationId.trimmed().isEmpty() || record.messageId.trimmed().isEmpty()
        || record.contentHash.trimmed().isEmpty()) {
        return failure(QStringLiteral("invalid_turn"), QStringLiteral("pending turn identity is incomplete"), record.turnId);
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message, record.turnId);
    }

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text(), record.turnId);
        } else {
            QSqlQuery query(database);
            query.prepare(QStringLiteral(R"sql(
                INSERT INTO database_turn_records (
                    turn_id, card_uid, conversation_id, message_id, turn_index,
                    content_hash, status, trigger_source, worker_model, attempt_count,
                    error_code, error_message, warnings_json
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, '', '', ?)
            )sql"));
            query.addBindValue(record.turnId.trimmed());
            query.addBindValue(record.cardUid.trimmed());
            query.addBindValue(record.conversationId.trimmed());
            query.addBindValue(record.messageId.trimmed());
            query.addBindValue(qMax(0, record.turnIndex));
            query.addBindValue(record.contentHash.trimmed());
            query.addBindValue(record.triggerSource.trimmed().isEmpty() ? QStringLiteral("chat_complete") : record.triggerSource.trimmed());
            query.addBindValue(sqlText(record.workerModel.trimmed()));
            query.addBindValue(qMax(0, record.attemptCount));
            query.addBindValue(normalizedWarnings(record.warningsJson));
            result = query.exec()
                ? success(QStringLiteral("pending database turn created"), record.turnId, query.numRowsAffected())
                : failure(QStringLiteral("database_error"), query.lastError().text(), record.turnId);
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

namespace {
QString jsonText(const QJsonObject& value) {
    return QString::fromUtf8(QJsonDocument(value).toJson(QJsonDocument::Compact));
}

QJsonValue storedJsonValue(const QString& source) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(source.toUtf8(), &error);
    return error.error == QJsonParseError::NoError && document.isObject()
        ? document.object().value(QStringLiteral("value"))
        : QJsonValue{};
}

QString valueJson(const QJsonValue& value) {
    return jsonText(QJsonObject{ { QStringLiteral("value"), value } });
}

bool recordTurnEffect(QSqlDatabase& database, const QString& turnId, int* sequence, const QString& effectType,
    const QJsonObject& target, const QJsonObject& before, const QJsonObject& after, QString* errorMessage) {
    QSqlQuery query(database);
    query.prepare(QStringLiteral(R"sql(
        INSERT INTO database_turn_effects (turn_id, sequence, effect_type, target_json, before_json, after_json)
        VALUES (?, ?, ?, ?, ?, ?)
    )sql"));
    query.addBindValue(turnId);
    query.addBindValue((*sequence)++);
    query.addBindValue(effectType);
    query.addBindValue(jsonText(target));
    query.addBindValue(jsonText(before));
    query.addBindValue(jsonText(after));
    if (query.exec()) {
        return true;
    }
    if (errorMessage) {
        *errorMessage = query.lastError().text();
    }
    return false;
}

bool applyTurnUpdates(QSqlDatabase& database, const QString& cardUid, const QString& turnId,
    const QJsonObject& updates, int* sequence, QString* errorMessage) {
    const QJsonObject snapshot = updates.value(QStringLiteral("snapshot")).toObject();
    if (!snapshot.isEmpty()) {
        const QString scope = snapshot.value(QStringLiteral("scope")).toString();
        const QString snapshotId = QStringLiteral("runtime:%1:%2").arg(cardUid, scope);
        QJsonObject before{ { QStringLiteral("exists"), false } };
        QSqlQuery existing(database);
        existing.prepare(QStringLiteral(
            "SELECT title, payload_json, updated_by_turn_id FROM database_state_snapshots WHERE id = ?"));
        existing.addBindValue(snapshotId);
        if (!existing.exec()) {
            if (errorMessage) {
                *errorMessage = existing.lastError().text();
            }
            return false;
        }
        if (existing.next()) {
            before.insert(QStringLiteral("exists"), true);
            before.insert(QStringLiteral("title"), existing.value(0).toString());
            before.insert(QStringLiteral("payload"), jsonObject(existing.value(1)));
            before.insert(QStringLiteral("updatedByTurnId"), existing.value(2).toString());
        }
        QSqlQuery write(database);
        write.prepare(QStringLiteral(R"sql(
            INSERT INTO database_state_snapshots
                (id, card_uid, scope, title, payload_json, updated_by_turn_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title, payload_json = excluded.payload_json,
                updated_by_turn_id = excluded.updated_by_turn_id, updated_at = CURRENT_TIMESTAMP
        )sql"));
        write.addBindValue(snapshotId);
        write.addBindValue(cardUid);
        write.addBindValue(scope);
        write.addBindValue(snapshot.value(QStringLiteral("title")).toString());
        write.addBindValue(jsonText(snapshot.value(QStringLiteral("payload")).toObject()));
        write.addBindValue(turnId);
        if (!write.exec()
            || !recordTurnEffect(database, turnId, sequence, QStringLiteral("snapshot"),
                QJsonObject{ { QStringLiteral("id"), snapshotId } }, before, snapshot, errorMessage)) {
            if (errorMessage && errorMessage->isEmpty()) {
                *errorMessage = write.lastError().text();
            }
            return false;
        }
    }

    for (const QJsonValue& value : updates.value(QStringLiteral("variables")).toArray()) {
        const QJsonObject variable = value.toObject();
        const QString roleId = variable.value(QStringLiteral("roleId")).toString();
        const QString key = variable.value(QStringLiteral("key")).toString();
        QJsonObject before{ { QStringLiteral("exists"), false } };
        QSqlQuery existing(database);
        existing.prepare(QStringLiteral(R"sql(
            SELECT label, value_json, maximum_json, updated_by_turn_id
            FROM database_runtime_values WHERE card_uid = ? AND role_id = ? AND field_key = ?
        )sql"));
        existing.addBindValue(cardUid);
        existing.addBindValue(roleId);
        existing.addBindValue(key);
        if (!existing.exec()) {
            if (errorMessage) {
                *errorMessage = existing.lastError().text();
            }
            return false;
        }
        if (existing.next()) {
            before.insert(QStringLiteral("exists"), true);
            before.insert(QStringLiteral("label"), existing.value(0).toString());
            before.insert(QStringLiteral("value"), storedJsonValue(existing.value(1).toString()));
            if (!existing.value(2).toString().isEmpty()) {
                before.insert(QStringLiteral("maximum"), storedJsonValue(existing.value(2).toString()));
            }
            before.insert(QStringLiteral("updatedByTurnId"), existing.value(3).toString());
        }
        const QString maximum = variable.contains(QStringLiteral("maximum"))
            ? valueJson(variable.value(QStringLiteral("maximum"))) : QStringLiteral("");
        const QString label = variable.value(QStringLiteral("label")).toString().trimmed().isEmpty()
            ? key : variable.value(QStringLiteral("label")).toString().trimmed();
        const QString reason = variable.value(QStringLiteral("reason")).toString().trimmed().isEmpty()
            ? QStringLiteral("") : variable.value(QStringLiteral("reason")).toString().trimmed();
        QSqlQuery write(database);
        write.prepare(QStringLiteral(R"sql(
            INSERT INTO database_runtime_values
                (card_uid, role_id, field_key, label, value_json, maximum_json, updated_by_turn_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(card_uid, role_id, field_key) DO UPDATE SET
                label = excluded.label, value_json = excluded.value_json, maximum_json = excluded.maximum_json,
                updated_by_turn_id = excluded.updated_by_turn_id, updated_at = CURRENT_TIMESTAMP
        )sql"));
        write.addBindValue(cardUid);
        write.addBindValue(roleId);
        write.addBindValue(key);
        write.addBindValue(label);
        write.addBindValue(valueJson(variable.value(QStringLiteral("value"))));
        write.addBindValue(maximum);
        write.addBindValue(turnId);
        if (!write.exec()
            || !recordTurnEffect(database, turnId, sequence, QStringLiteral("runtime_value"),
                QJsonObject{ { QStringLiteral("cardUid"), cardUid }, { QStringLiteral("roleId"), roleId },
                    { QStringLiteral("key"), key } }, before, variable, errorMessage)) {
            if (errorMessage && errorMessage->isEmpty()) {
                *errorMessage = write.lastError().text();
            }
            return false;
        }

        if (variable.value(QStringLiteral("value")).isDouble()) {
            QSqlQuery history(database);
            history.prepare(QStringLiteral(R"sql(
                INSERT INTO database_metric_history
                    (card_uid, role_id, field_key, label, value_json, maximum_json, delta_json, reason, turn_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            )sql"));
            history.addBindValue(cardUid);
            history.addBindValue(roleId);
            history.addBindValue(key);
            history.addBindValue(label);
            history.addBindValue(valueJson(variable.value(QStringLiteral("value"))));
            history.addBindValue(maximum);
            history.addBindValue(variable.contains(QStringLiteral("delta"))
                    ? valueJson(variable.value(QStringLiteral("delta"))) : QStringLiteral(""));
            history.addBindValue(reason);
            history.addBindValue(turnId);
            if (!history.exec()
                || !recordTurnEffect(database, turnId, sequence, QStringLiteral("metric_history"),
                    QJsonObject{ { QStringLiteral("id"), history.lastInsertId().toLongLong() } }, {}, {}, errorMessage)) {
                if (errorMessage && errorMessage->isEmpty()) {
                    *errorMessage = history.lastError().text();
                }
                return false;
            }
        }
    }

    for (const QJsonValue& value : updates.value(QStringLiteral("relationships")).toArray()) {
        const QJsonObject relationship = value.toObject();
        const QString pairKey = relationship.value(QStringLiteral("pairKey")).toString().trimmed();
        QJsonObject before{ { QStringLiteral("exists"), false } };
        QSqlQuery existing(database);
        existing.prepare(QStringLiteral(R"sql(
            SELECT role_a, role_b, stage, attitude, summary, updated_by_turn_id
            FROM database_relationship_state WHERE card_uid = ? AND pair_key = ?
        )sql"));
        existing.addBindValue(cardUid);
        existing.addBindValue(pairKey);
        if (!existing.exec()) {
            if (errorMessage) {
                *errorMessage = existing.lastError().text();
            }
            return false;
        }
        if (existing.next()) {
            before.insert(QStringLiteral("exists"), true);
            before.insert(QStringLiteral("roleA"), existing.value(0).toString());
            before.insert(QStringLiteral("roleB"), existing.value(1).toString());
            before.insert(QStringLiteral("stage"), existing.value(2).toString());
            before.insert(QStringLiteral("attitude"), existing.value(3).toString());
            before.insert(QStringLiteral("summary"), existing.value(4).toString());
            before.insert(QStringLiteral("updatedByTurnId"), existing.value(5).toString());
        }

        auto mergedText = [&](const QString& key) {
            const QString incoming = relationship.value(key).toString(QStringLiteral("")).trimmed();
            return relationship.contains(key) && !incoming.isEmpty()
                ? incoming : before.value(key).toString(QStringLiteral("")).trimmed();
        };
        QString summary = mergedText(QStringLiteral("summary"));
        const QString change = relationship.value(QStringLiteral("change"))
                                   .toString(QStringLiteral(""))
                                   .trimmed();
        if (!before.value(QStringLiteral("exists")).toBool() && summary.isEmpty()) {
            summary = change;
        }
        const QJsonObject after{
            { QStringLiteral("pairKey"), pairKey },
            { QStringLiteral("roleA"), mergedText(QStringLiteral("roleA")) },
            { QStringLiteral("roleB"), mergedText(QStringLiteral("roleB")) },
            { QStringLiteral("stage"), mergedText(QStringLiteral("stage")) },
            { QStringLiteral("attitude"), mergedText(QStringLiteral("attitude")) },
            { QStringLiteral("summary"), summary },
        };
        const bool stateChanged = !before.value(QStringLiteral("exists")).toBool()
            || before.value(QStringLiteral("roleA")).toString() != after.value(QStringLiteral("roleA")).toString()
            || before.value(QStringLiteral("roleB")).toString() != after.value(QStringLiteral("roleB")).toString()
            || before.value(QStringLiteral("stage")).toString() != after.value(QStringLiteral("stage")).toString()
            || before.value(QStringLiteral("attitude")).toString() != after.value(QStringLiteral("attitude")).toString()
            || before.value(QStringLiteral("summary")).toString() != after.value(QStringLiteral("summary")).toString();

        if (stateChanged) {
            QSqlQuery write(database);
            write.prepare(QStringLiteral(R"sql(
                INSERT INTO database_relationship_state
                    (card_uid, pair_key, role_a, role_b, stage, attitude, summary,
                     updated_by_turn_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(card_uid, pair_key) DO UPDATE SET
                    role_a = excluded.role_a, role_b = excluded.role_b,
                    stage = excluded.stage, attitude = excluded.attitude,
                    summary = excluded.summary, updated_by_turn_id = excluded.updated_by_turn_id,
                    updated_at = CURRENT_TIMESTAMP
            )sql"));
            write.addBindValue(cardUid);
            write.addBindValue(pairKey);
            write.addBindValue(after.value(QStringLiteral("roleA")).toString());
            write.addBindValue(after.value(QStringLiteral("roleB")).toString());
            write.addBindValue(after.value(QStringLiteral("stage")).toString());
            write.addBindValue(after.value(QStringLiteral("attitude")).toString());
            write.addBindValue(after.value(QStringLiteral("summary")).toString());
            write.addBindValue(turnId);
            if (!write.exec()
                || !recordTurnEffect(database, turnId, sequence, QStringLiteral("relationship_state"),
                    QJsonObject{ { QStringLiteral("cardUid"), cardUid },
                        { QStringLiteral("pairKey"), pairKey } }, before, after, errorMessage)) {
                if (errorMessage && errorMessage->isEmpty()) {
                    *errorMessage = write.lastError().text();
                }
                return false;
            }
        }

        if (stateChanged || !change.isEmpty()) {
            QSqlQuery history(database);
            history.prepare(QStringLiteral(R"sql(
                INSERT INTO database_relationship_history
                    (card_uid, turn_id, pair_key, role_a, role_b, previous_stage,
                     stage, attitude, summary, change_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            )sql"));
            history.addBindValue(cardUid);
            history.addBindValue(turnId);
            history.addBindValue(pairKey);
            history.addBindValue(after.value(QStringLiteral("roleA")).toString());
            history.addBindValue(after.value(QStringLiteral("roleB")).toString());
            history.addBindValue(before.value(QStringLiteral("stage")).toString(QStringLiteral("")));
            history.addBindValue(after.value(QStringLiteral("stage")).toString());
            history.addBindValue(after.value(QStringLiteral("attitude")).toString());
            history.addBindValue(after.value(QStringLiteral("summary")).toString());
            history.addBindValue(change.isEmpty() ? QStringLiteral("关系状态已更新") : change);
            if (!history.exec()
                || !recordTurnEffect(database, turnId, sequence, QStringLiteral("relationship_history"),
                    QJsonObject{ { QStringLiteral("id"), history.lastInsertId().toLongLong() } }, {}, {},
                    errorMessage)) {
                if (errorMessage && errorMessage->isEmpty()) {
                    *errorMessage = history.lastError().text();
                }
                return false;
            }
        }
    }

    for (const QJsonValue& value : updates.value(QStringLiteral("ledger")).toArray()) {
        const QJsonObject entry = value.toObject();
        QSqlQuery write(database);
        write.prepare(QStringLiteral(R"sql(
            INSERT INTO database_plot_ledger (card_uid, entry_type, content, payload_json, turn_id)
            VALUES (?, ?, ?, ?, ?)
        )sql"));
        write.addBindValue(cardUid);
        write.addBindValue(entry.value(QStringLiteral("entryType")).toString());
        write.addBindValue(entry.value(QStringLiteral("content")).toString());
        write.addBindValue(jsonText(entry.value(QStringLiteral("payload")).toObject()));
        write.addBindValue(turnId);
        if (!write.exec()
            || !recordTurnEffect(database, turnId, sequence, QStringLiteral("ledger"),
                QJsonObject{ { QStringLiteral("id"), write.lastInsertId().toLongLong() } }, {}, entry, errorMessage)) {
            if (errorMessage && errorMessage->isEmpty()) {
                *errorMessage = write.lastError().text();
            }
            return false;
        }
    }
    return true;
}

QJsonObject storyTimeStateFromQuery(const QSqlQuery& query) {
    return {
        { QStringLiteral("cardUid"), query.value(0).toString() },
        { QStringLiteral("enabled"), query.value(1).toBool() },
        { QStringLiteral("showInRecord"), query.value(2).toBool() },
        { QStringLiteral("baseTime"), query.value(3).toString() },
        { QStringLiteral("currentTime"), query.value(4).toString() },
        { QStringLiteral("elapsedSeconds"), query.value(5).toLongLong() },
        { QStringLiteral("season"), query.value(6).toString() },
        { QStringLiteral("timeSlot"), query.value(7).toString() },
        { QStringLiteral("advanceMode"), query.value(8).toString() },
        { QStringLiteral("customAdvanceType"), query.value(9).toString() },
        { QStringLiteral("customAdvanceMinSeconds"), query.value(10).toInt() },
        { QStringLiteral("customAdvanceMaxSeconds"), query.value(11).toInt() },
        { QStringLiteral("displayMode"), query.value(12).toString() },
        { QStringLiteral("lastDeltaSeconds"), query.value(13).toInt() },
        { QStringLiteral("lastDeltaText"), query.value(14).toString() },
        { QStringLiteral("lastConfidence"), query.value(15).toString() },
        { QStringLiteral("updatedByTurnId"), query.value(16).toString() },
        { QStringLiteral("createdAt"), query.value(17).toString() },
        { QStringLiteral("updatedAt"), query.value(18).toString() },
    };
}

QJsonObject loadStoryTimeState(QSqlDatabase& database, const QString& cardUid) {
    QSqlQuery query(database);
    query.prepare(QStringLiteral(R"sql(
        SELECT card_uid, enabled, show_in_record, base_time, "current_time", elapsed_seconds,
               season, time_slot, advance_mode, custom_advance_type,
               custom_advance_min_seconds, custom_advance_max_seconds, display_mode,
               last_delta_seconds, last_delta_text, last_confidence, updated_by_turn_id,
               created_at, updated_at
        FROM database_story_time_state WHERE card_uid = ?
    )sql"));
    query.addBindValue(cardUid);
    return query.exec() && query.next() ? storyTimeStateFromQuery(query) : QJsonObject{};
}

bool writeStoryTimeState(QSqlDatabase& database, const QJsonObject& state, const QString& updatedByTurnId,
    QString* errorMessage) {
    QSqlQuery query(database);
    query.prepare(QStringLiteral(R"sql(
        INSERT INTO database_story_time_state (
            card_uid, enabled, show_in_record, base_time, current_time, elapsed_seconds,
            season, time_slot, advance_mode, custom_advance_type,
            custom_advance_min_seconds, custom_advance_max_seconds, display_mode,
            last_delta_seconds, last_delta_text, last_confidence, updated_by_turn_id,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(card_uid) DO UPDATE SET
            enabled = excluded.enabled, show_in_record = excluded.show_in_record,
            base_time = excluded.base_time, current_time = excluded.current_time,
            elapsed_seconds = excluded.elapsed_seconds, season = excluded.season,
            time_slot = excluded.time_slot, advance_mode = excluded.advance_mode,
            custom_advance_type = excluded.custom_advance_type,
            custom_advance_min_seconds = excluded.custom_advance_min_seconds,
            custom_advance_max_seconds = excluded.custom_advance_max_seconds,
            display_mode = excluded.display_mode, last_delta_seconds = excluded.last_delta_seconds,
            last_delta_text = excluded.last_delta_text, last_confidence = excluded.last_confidence,
            updated_by_turn_id = excluded.updated_by_turn_id, updated_at = CURRENT_TIMESTAMP
    )sql"));
    query.addBindValue(state.value(QStringLiteral("cardUid")).toString());
    query.addBindValue(state.value(QStringLiteral("enabled")).toBool() ? 1 : 0);
    query.addBindValue(state.value(QStringLiteral("showInRecord")).toBool(true) ? 1 : 0);
    query.addBindValue(sqlText(state.value(QStringLiteral("baseTime")).toString()));
    query.addBindValue(sqlText(state.value(QStringLiteral("currentTime")).toString()));
    query.addBindValue(state.value(QStringLiteral("elapsedSeconds")).toVariant());
    query.addBindValue(sqlText(state.value(QStringLiteral("season")).toString()));
    query.addBindValue(sqlText(state.value(QStringLiteral("timeSlot")).toString()));
    query.addBindValue(sqlText(state.value(QStringLiteral("advanceMode")).toString()));
    query.addBindValue(sqlText(state.value(QStringLiteral("customAdvanceType")).toString()));
    query.addBindValue(state.value(QStringLiteral("customAdvanceMinSeconds")).toInt());
    query.addBindValue(state.value(QStringLiteral("customAdvanceMaxSeconds")).toInt());
    query.addBindValue(sqlText(state.value(QStringLiteral("displayMode")).toString()));
    query.addBindValue(state.value(QStringLiteral("lastDeltaSeconds")).toInt());
    query.addBindValue(sqlText(state.value(QStringLiteral("lastDeltaText")).toString()));
    query.addBindValue(sqlText(state.value(QStringLiteral("lastConfidence")).toString()));
    query.addBindValue(sqlText(updatedByTurnId));
    if (query.exec()) {
        return true;
    }
    if (errorMessage) {
        *errorMessage = query.lastError().text();
    }
    return false;
}

bool applyStoryTimeUpdate(QSqlDatabase& database, const QString& cardUid, const QString& turnId,
    const QString& messageId, qint64 turnOrdinal, const QJsonObject& updates, int* sequence,
    QString* errorMessage) {
    const QJsonObject current = loadStoryTimeState(database, cardUid);
    if (current.isEmpty()) {
        return true;
    }
    const QJsonObject advanced = DatabaseRules::advanceStoryTime(
        current, updates.value(QStringLiteral("storyTimeDelta")).toObject(), turnId, messageId, turnOrdinal);
    if (advanced.isEmpty()) {
        return true;
    }
    QJsonObject before{
        { QStringLiteral("exists"), true },
        { QStringLiteral("state"), current },
        { QStringLiteral("updatedByTurnId"), current.value(QStringLiteral("updatedByTurnId")) },
    };
    if (!writeStoryTimeState(database, advanced, turnId, errorMessage)
        || !recordTurnEffect(database, turnId, sequence, QStringLiteral("story_time"),
            QJsonObject{ { QStringLiteral("cardUid"), cardUid } }, before, advanced, errorMessage)) {
        return false;
    }
    const int deltaSeconds = advanced.value(QStringLiteral("lastDeltaSeconds")).toInt();
    if (deltaSeconds <= 0) {
        return true;
    }
    QSqlQuery history(database);
    history.prepare(QStringLiteral(R"sql(
        INSERT INTO database_story_time_history (
            card_uid, turn_id, message_id, turn_ordinal, old_time, new_time,
            delta_seconds, delta_text, confidence, reason, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    )sql"));
    history.addBindValue(cardUid);
    history.addBindValue(turnId);
    history.addBindValue(messageId);
    history.addBindValue(turnOrdinal);
    history.addBindValue(advanced.value(QStringLiteral("oldTime")).toString());
    history.addBindValue(advanced.value(QStringLiteral("currentTime")).toString());
    history.addBindValue(deltaSeconds);
    history.addBindValue(advanced.value(QStringLiteral("lastDeltaText")).toString());
    history.addBindValue(advanced.value(QStringLiteral("lastConfidence")).toString());
    history.addBindValue(advanced.value(QStringLiteral("deltaReason")).toString());
    history.addBindValue(advanced.value(QStringLiteral("deltaSource")).toString());
    if (!history.exec()
        || !recordTurnEffect(database, turnId, sequence, QStringLiteral("story_time_history"),
            QJsonObject{ { QStringLiteral("id"), history.lastInsertId().toLongLong() } }, {}, {}, errorMessage)) {
        if (errorMessage && errorMessage->isEmpty()) {
            *errorMessage = history.lastError().text();
        }
        return false;
    }
    return true;
}

bool replaceActiveTagScope(QSqlDatabase& database, const QString& cardUid, const QString& turnId,
    const QString& sourceType, const QString& sourceKey, const QString& label,
    const QJsonArray& tags, int* sequence, QString* errorMessage) {
    QJsonArray beforeRows;
    QSqlQuery existing(database);
    existing.prepare(QStringLiteral(R"sql(
        SELECT tag, label, reason, active, updated_by_turn_id
        FROM database_active_tags WHERE card_uid = ? AND source_type = ? AND source_key = ?
    )sql"));
    existing.addBindValue(cardUid);
    existing.addBindValue(sourceType);
    existing.addBindValue(sourceKey);
    if (!existing.exec()) {
        if (errorMessage) *errorMessage = existing.lastError().text();
        return false;
    }
    while (existing.next()) {
        beforeRows.append(QJsonObject{
            { QStringLiteral("tag"), existing.value(0).toString() },
            { QStringLiteral("label"), existing.value(1).toString() },
            { QStringLiteral("reason"), existing.value(2).toString() },
            { QStringLiteral("active"), existing.value(3).toBool() },
            { QStringLiteral("updatedByTurnId"), existing.value(4).toString() },
        });
    }
    QSqlQuery remove(database);
    remove.prepare(QStringLiteral(
        "DELETE FROM database_active_tags WHERE card_uid = ? AND source_type = ? AND source_key = ?"));
    remove.addBindValue(cardUid);
    remove.addBindValue(sourceType);
    remove.addBindValue(sourceKey);
    if (!remove.exec()) {
        if (errorMessage) *errorMessage = remove.lastError().text();
        return false;
    }
    QJsonArray afterRows;
    for (const QJsonValue& tagValue : tags) {
        const QString tag = tagValue.toString().trimmed();
        if (tag.isEmpty()) {
            continue;
        }
        QSqlQuery insert(database);
        insert.prepare(QStringLiteral(R"sql(
            INSERT INTO database_active_tags
                (card_uid, tag, source_type, source_key, label, reason, active, updated_by_turn_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(card_uid, tag) DO UPDATE SET
                source_type = excluded.source_type, source_key = excluded.source_key,
                label = excluded.label, reason = excluded.reason, active = 1,
                updated_by_turn_id = excluded.updated_by_turn_id, updated_at = CURRENT_TIMESTAMP
        )sql"));
        insert.addBindValue(cardUid);
        insert.addBindValue(tag);
        insert.addBindValue(sourceType);
        insert.addBindValue(sourceKey);
        insert.addBindValue(label);
        insert.addBindValue(QStringLiteral("阶段规则命中"));
        insert.addBindValue(turnId);
        if (!insert.exec()) {
            if (errorMessage) *errorMessage = insert.lastError().text();
            return false;
        }
        afterRows.append(QJsonObject{ { QStringLiteral("tag"), tag }, { QStringLiteral("active"), true } });
    }
    return recordTurnEffect(database, turnId, sequence, QStringLiteral("active_tags_scope"),
        QJsonObject{
            { QStringLiteral("cardUid"), cardUid }, { QStringLiteral("sourceType"), sourceType },
            { QStringLiteral("sourceKey"), sourceKey },
        }, QJsonObject{ { QStringLiteral("rows"), beforeRows } },
        QJsonObject{ { QStringLiteral("rows"), afterRows } }, errorMessage);
}

bool applyRuntimeTags(QSqlDatabase& database, const QString& cardUid, const QString& turnId,
    const QJsonArray& tags, int* sequence, QString* errorMessage) {
    for (const QJsonValue& value : tags) {
        const QJsonObject item = value.toObject();
        const QString tag = item.value(QStringLiteral("tag")).toString().trimmed();
        if (tag.isEmpty()) {
            continue;
        }
        const QString sourceType = item.value(QStringLiteral("sourceType")).toString() == QStringLiteral("ledger")
            ? QStringLiteral("ledger") : QStringLiteral("runtime");
        const QString sourceKey = item.value(QStringLiteral("sourceKey")).toString(tag);
        QJsonObject before{ { QStringLiteral("exists"), false } };
        QSqlQuery existing(database);
        existing.prepare(QStringLiteral(R"sql(
            SELECT source_type, source_key, label, reason, active, updated_by_turn_id
            FROM database_active_tags WHERE card_uid = ? AND tag = ?
        )sql"));
        existing.addBindValue(cardUid);
        existing.addBindValue(tag);
        if (!existing.exec()) {
            if (errorMessage) *errorMessage = existing.lastError().text();
            return false;
        }
        if (existing.next()) {
            before = QJsonObject{
                { QStringLiteral("exists"), true },
                { QStringLiteral("sourceType"), existing.value(0).toString() },
                { QStringLiteral("sourceKey"), existing.value(1).toString() },
                { QStringLiteral("label"), existing.value(2).toString() },
                { QStringLiteral("reason"), existing.value(3).toString() },
                { QStringLiteral("active"), existing.value(4).toBool() },
                { QStringLiteral("updatedByTurnId"), existing.value(5).toString() },
            };
        }
        QSqlQuery write(database);
        write.prepare(QStringLiteral(R"sql(
            INSERT INTO database_active_tags
                (card_uid, tag, source_type, source_key, label, reason, active, updated_by_turn_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(card_uid, tag) DO UPDATE SET
                source_type = excluded.source_type, source_key = excluded.source_key, label = excluded.label,
                reason = excluded.reason, active = excluded.active,
                updated_by_turn_id = excluded.updated_by_turn_id, updated_at = CURRENT_TIMESTAMP
        )sql"));
        write.addBindValue(cardUid);
        write.addBindValue(tag);
        write.addBindValue(sourceType);
        write.addBindValue(sourceKey);
        write.addBindValue(tag);
        write.addBindValue(item.value(QStringLiteral("reason")).toString());
        write.addBindValue(item.value(QStringLiteral("active")).toBool(true) ? 1 : 0);
        write.addBindValue(turnId);
        if (!write.exec()
            || !recordTurnEffect(database, turnId, sequence, QStringLiteral("active_tag"),
                QJsonObject{ { QStringLiteral("cardUid"), cardUid }, { QStringLiteral("tag"), tag } },
                before, item, errorMessage)) {
            if (errorMessage && errorMessage->isEmpty()) *errorMessage = write.lastError().text();
            return false;
        }
    }
    return true;
}

bool applyStageRules(QSqlDatabase& database, const QString& cardUid, const QString& turnId,
    qint64 turnOrdinal, const QJsonObject& databaseConfig, int* sequence,
    QJsonObject* displayRecord, QString* errorMessage) {
    if (databaseConfig.isEmpty()) {
        return true;
    }
    QHash<QString, QJsonValue> runtimeValues;
    QSqlQuery values(database);
    values.prepare(QStringLiteral(
        "SELECT role_id, field_key, value_json FROM database_runtime_values WHERE card_uid = ?"));
    values.addBindValue(cardUid);
    if (!values.exec()) {
        if (errorMessage) *errorMessage = values.lastError().text();
        return false;
    }
    while (values.next()) {
        runtimeValues.insert(values.value(0).toString() + QLatin1Char('\x1f') + values.value(1).toString(),
            storedJsonValue(values.value(2).toString()));
    }

    QHash<QString, QJsonObject> currentStages;
    QSqlQuery current(database);
    current.prepare(QStringLiteral(R"sql(
        SELECT role_id, stage_key, state_json FROM database_stage_state
        WHERE card_uid = ? ORDER BY updated_at DESC, id DESC
    )sql"));
    current.addBindValue(cardUid);
    if (!current.exec()) {
        if (errorMessage) *errorMessage = current.lastError().text();
        return false;
    }
    while (current.next()) {
        const QString roleId = current.value(0).toString();
        if (!currentStages.contains(roleId)) {
            currentStages.insert(roleId, QJsonObject{
                { QStringLiteral("stageKey"), current.value(1).toString() },
                { QStringLiteral("state"), jsonObject(current.value(2)) },
            });
        }
    }
    const QList<QJsonObject> decisions = DatabaseRules::evaluateStages(
        databaseConfig, runtimeValues, DatabaseRules::storyTimeContext(loadStoryTimeState(database, cardUid)),
        currentStages, turnOrdinal);
    for (const QJsonObject& decision : decisions) {
        const QString roleId = decision.value(QStringLiteral("roleId")).toString();
        QJsonArray beforeRows;
        QSqlQuery beforeQuery(database);
        beforeQuery.prepare(QStringLiteral(R"sql(
            SELECT stage_key, state_json, updated_by_turn_id
            FROM database_stage_state WHERE card_uid = ? AND role_id = ? ORDER BY id
        )sql"));
        beforeQuery.addBindValue(cardUid);
        beforeQuery.addBindValue(roleId);
        if (!beforeQuery.exec()) {
            if (errorMessage) *errorMessage = beforeQuery.lastError().text();
            return false;
        }
        while (beforeQuery.next()) {
            beforeRows.append(QJsonObject{
                { QStringLiteral("stageKey"), beforeQuery.value(0).toString() },
                { QStringLiteral("state"), jsonObject(beforeQuery.value(1)) },
                { QStringLiteral("updatedByTurnId"), beforeQuery.value(2).toString() },
            });
        }
        QSqlQuery remove(database);
        remove.prepare(QStringLiteral("DELETE FROM database_stage_state WHERE card_uid = ? AND role_id = ?"));
        remove.addBindValue(cardUid);
        remove.addBindValue(roleId);
        if (!remove.exec()) {
            if (errorMessage) *errorMessage = remove.lastError().text();
            return false;
        }
        QSqlQuery insert(database);
        insert.prepare(QStringLiteral(R"sql(
            INSERT INTO database_stage_state
                (card_uid, role_id, stage_key, state_json, updated_by_turn_id, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        )sql"));
        insert.addBindValue(cardUid);
        insert.addBindValue(roleId);
        insert.addBindValue(decision.value(QStringLiteral("stageKey")).toString());
        insert.addBindValue(jsonText(decision.value(QStringLiteral("state")).toObject()));
        insert.addBindValue(turnId);
        if (!insert.exec()
            || !recordTurnEffect(database, turnId, sequence, QStringLiteral("stage_state"),
                QJsonObject{ { QStringLiteral("cardUid"), cardUid }, { QStringLiteral("roleId"), roleId } },
                QJsonObject{ { QStringLiteral("rows"), beforeRows } }, decision, errorMessage)) {
            if (errorMessage && errorMessage->isEmpty()) *errorMessage = insert.lastError().text();
            return false;
        }

        if (decision.value(QStringLiteral("changed")).toBool()) {
            QSqlQuery history(database);
            history.prepare(QStringLiteral(R"sql(
                INSERT INTO database_stage_history (
                    card_uid, turn_id, turn_ordinal, role_id, role_name,
                    from_stage_key, from_stage_name, to_stage_key, to_stage_name,
                    trigger_values_json, reason, active_tag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            )sql"));
            history.addBindValue(cardUid);
            history.addBindValue(turnId);
            history.addBindValue(turnOrdinal);
            history.addBindValue(roleId);
            history.addBindValue(decision.value(QStringLiteral("roleName")).toString());
            history.addBindValue(decision.value(QStringLiteral("previousStageKey")).toString());
            history.addBindValue(decision.value(QStringLiteral("previousStageName")).toString());
            history.addBindValue(decision.value(QStringLiteral("stageKey")).toString());
            history.addBindValue(decision.value(QStringLiteral("stageName")).toString());
            history.addBindValue(jsonText(decision.value(QStringLiteral("triggerValues")).toObject()));
            history.addBindValue(decision.value(QStringLiteral("reason")).toString());
            history.addBindValue(decision.value(QStringLiteral("state")).toObject()
                                     .value(QStringLiteral("activeTag")).toString());
            if (!history.exec()
                || !recordTurnEffect(database, turnId, sequence, QStringLiteral("stage_history"),
                    QJsonObject{ { QStringLiteral("id"), history.lastInsertId().toLongLong() } }, {}, {}, errorMessage)) {
                if (errorMessage && errorMessage->isEmpty()) *errorMessage = history.lastError().text();
                return false;
            }
        }
        const QString label = QStringLiteral("%1 · %2").arg(
            decision.value(QStringLiteral("roleName")).toString(),
            decision.value(QStringLiteral("stageName")).toString());
        if (!replaceActiveTagScope(database, cardUid, turnId, QStringLiteral("stage"), roleId,
                label, decision.value(QStringLiteral("tags")).toArray(), sequence, errorMessage)) {
            return false;
        }
        if (displayRecord) {
            QJsonArray relationships = displayRecord->value(QStringLiteral("relationships")).toArray();
            relationships.append(QJsonObject{
                { QStringLiteral("pair"), decision.value(QStringLiteral("roleName")) },
                { QStringLiteral("stage"), decision.value(QStringLiteral("changed")).toBool()
                        ? QStringLiteral("%1 → %2").arg(
                            decision.value(QStringLiteral("previousStageName")).toString(),
                            decision.value(QStringLiteral("stageName")).toString())
                        : QStringLiteral("当前阶段 · %1").arg(decision.value(QStringLiteral("stageName")).toString()) },
                { QStringLiteral("change"), decision.value(QStringLiteral("reason")) },
                { QStringLiteral("type"), QStringLiteral("database_stage") },
                { QStringLiteral("activeTag"), decision.value(QStringLiteral("state")).toObject()
                        .value(QStringLiteral("activeTag")) },
            });
            displayRecord->insert(QStringLiteral("relationships"), relationships);
        }
    }
    return true;
}

bool rollbackTurnEffects(QSqlDatabase& database, const QString& turnId, QString* errorMessage) {
    QSqlQuery effects(database);
    effects.prepare(QStringLiteral(R"sql(
        SELECT id, effect_type, target_json, before_json
        FROM database_turn_effects
        WHERE turn_id = ? AND reverted_at = ''
        ORDER BY sequence DESC
    )sql"));
    effects.addBindValue(turnId);
    if (!effects.exec()) {
        if (errorMessage) {
            *errorMessage = effects.lastError().text();
        }
        return false;
    }
    while (effects.next()) {
        const qlonglong effectId = effects.value(0).toLongLong();
        const QString type = effects.value(1).toString();
        const QJsonObject target = jsonObject(effects.value(2));
        const QJsonObject before = jsonObject(effects.value(3));
        const bool existed = before.value(QStringLiteral("exists")).toBool(false);
        QSqlQuery restore(database);
        bool restored = false;
        if (type == QStringLiteral("snapshot")) {
            if (!existed) {
                restore.prepare(QStringLiteral(
                    "DELETE FROM database_state_snapshots WHERE id = ? AND updated_by_turn_id = ?"));
                restore.addBindValue(target.value(QStringLiteral("id")).toString());
                restore.addBindValue(turnId);
            } else {
                restore.prepare(QStringLiteral(R"sql(
                    UPDATE database_state_snapshots
                    SET title = ?, payload_json = ?, updated_by_turn_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(before.value(QStringLiteral("title")).toString());
                restore.addBindValue(jsonText(before.value(QStringLiteral("payload")).toObject()));
                restore.addBindValue(before.value(QStringLiteral("updatedByTurnId")).toString());
                restore.addBindValue(target.value(QStringLiteral("id")).toString());
                restore.addBindValue(turnId);
            }
        } else if (type == QStringLiteral("runtime_value")) {
            if (!existed) {
                restore.prepare(QStringLiteral(R"sql(
                    DELETE FROM database_runtime_values WHERE card_uid = ? AND role_id = ? AND field_key = ?
                        AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(target.value(QStringLiteral("cardUid")).toString());
                restore.addBindValue(target.value(QStringLiteral("roleId")).toString());
                restore.addBindValue(target.value(QStringLiteral("key")).toString());
                restore.addBindValue(turnId);
            } else {
                restore.prepare(QStringLiteral(R"sql(
                    UPDATE database_runtime_values
                    SET label = ?, value_json = ?, maximum_json = ?, updated_by_turn_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE card_uid = ? AND role_id = ? AND field_key = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(before.value(QStringLiteral("label")).toString());
                restore.addBindValue(valueJson(before.value(QStringLiteral("value"))));
                restore.addBindValue(before.contains(QStringLiteral("maximum"))
                        ? valueJson(before.value(QStringLiteral("maximum"))) : QStringLiteral(""));
                restore.addBindValue(before.value(QStringLiteral("updatedByTurnId")).toString());
                restore.addBindValue(target.value(QStringLiteral("cardUid")).toString());
                restore.addBindValue(target.value(QStringLiteral("roleId")).toString());
                restore.addBindValue(target.value(QStringLiteral("key")).toString());
                restore.addBindValue(turnId);
            }
        } else if (type == QStringLiteral("stage")) {
            if (!existed) {
                restore.prepare(QStringLiteral(R"sql(
                    DELETE FROM database_stage_state WHERE card_uid = ? AND role_id = ? AND stage_key = ?
                        AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(target.value(QStringLiteral("cardUid")).toString());
                restore.addBindValue(target.value(QStringLiteral("roleId")).toString());
                restore.addBindValue(target.value(QStringLiteral("stageKey")).toString());
                restore.addBindValue(turnId);
            } else {
                restore.prepare(QStringLiteral(R"sql(
                    UPDATE database_stage_state
                    SET state_json = ?, updated_by_turn_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE card_uid = ? AND role_id = ? AND stage_key = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(jsonText(before.value(QStringLiteral("state")).toObject()));
                restore.addBindValue(before.value(QStringLiteral("updatedByTurnId")).toString());
                restore.addBindValue(target.value(QStringLiteral("cardUid")).toString());
                restore.addBindValue(target.value(QStringLiteral("roleId")).toString());
                restore.addBindValue(target.value(QStringLiteral("stageKey")).toString());
                restore.addBindValue(turnId);
            }
        } else if (type == QStringLiteral("story_time")) {
            QSqlQuery owner(database);
            owner.prepare(QStringLiteral(
                "SELECT updated_by_turn_id FROM database_story_time_state WHERE card_uid = ?"));
            owner.addBindValue(target.value(QStringLiteral("cardUid")).toString());
            if (!owner.exec() || !owner.next() || owner.value(0).toString() != turnId) {
                if (errorMessage) *errorMessage = QStringLiteral("story time ownership changed before turn rollback");
                return false;
            }
            if (!writeStoryTimeState(database, before.value(QStringLiteral("state")).toObject(),
                    before.value(QStringLiteral("updatedByTurnId")).toString(), errorMessage)) {
                return false;
            }
            restored = true;
        } else if (type == QStringLiteral("stage_state")) {
            const QString cardUid = target.value(QStringLiteral("cardUid")).toString();
            const QString roleId = target.value(QStringLiteral("roleId")).toString();
            QSqlQuery owners(database);
            owners.prepare(QStringLiteral(R"sql(
                SELECT COUNT(*), SUM(CASE WHEN updated_by_turn_id = ? THEN 0 ELSE 1 END)
                FROM database_stage_state WHERE card_uid = ? AND role_id = ?
            )sql"));
            owners.addBindValue(turnId);
            owners.addBindValue(cardUid);
            owners.addBindValue(roleId);
            if (!owners.exec() || !owners.next() || owners.value(0).toInt() < 1 || owners.value(1).toInt() != 0) {
                if (errorMessage) *errorMessage = QStringLiteral("stage ownership changed before turn rollback");
                return false;
            }
            QSqlQuery remove(database);
            remove.prepare(QStringLiteral("DELETE FROM database_stage_state WHERE card_uid = ? AND role_id = ?"));
            remove.addBindValue(cardUid);
            remove.addBindValue(roleId);
            if (!remove.exec()) {
                if (errorMessage) *errorMessage = remove.lastError().text();
                return false;
            }
            for (const QJsonValue& rowValue : before.value(QStringLiteral("rows")).toArray()) {
                const QJsonObject row = rowValue.toObject();
                QSqlQuery insert(database);
                insert.prepare(QStringLiteral(R"sql(
                    INSERT INTO database_stage_state
                        (card_uid, role_id, stage_key, state_json, updated_by_turn_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                )sql"));
                insert.addBindValue(cardUid);
                insert.addBindValue(roleId);
                insert.addBindValue(row.value(QStringLiteral("stageKey")).toString());
                insert.addBindValue(jsonText(row.value(QStringLiteral("state")).toObject()));
                insert.addBindValue(row.value(QStringLiteral("updatedByTurnId")).toString());
                if (!insert.exec()) {
                    if (errorMessage) *errorMessage = insert.lastError().text();
                    return false;
                }
            }
            restored = true;
        } else if (type == QStringLiteral("active_tag")) {
            const QString cardUid = target.value(QStringLiteral("cardUid")).toString();
            const QString tag = target.value(QStringLiteral("tag")).toString();
            QSqlQuery owner(database);
            owner.prepare(QStringLiteral(
                "SELECT updated_by_turn_id FROM database_active_tags WHERE card_uid = ? AND tag = ?"));
            owner.addBindValue(cardUid);
            owner.addBindValue(tag);
            if (!owner.exec() || !owner.next() || owner.value(0).toString() != turnId) {
                if (errorMessage) *errorMessage = QStringLiteral("active tag ownership changed before turn rollback");
                return false;
            }
            if (!existed) {
                restore.prepare(QStringLiteral("DELETE FROM database_active_tags WHERE card_uid = ? AND tag = ?"));
                restore.addBindValue(cardUid);
                restore.addBindValue(tag);
            } else {
                restore.prepare(QStringLiteral(R"sql(
                    UPDATE database_active_tags SET
                        source_type = ?, source_key = ?, label = ?, reason = ?, active = ?,
                        updated_by_turn_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE card_uid = ? AND tag = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(before.value(QStringLiteral("sourceType")).toString());
                restore.addBindValue(before.value(QStringLiteral("sourceKey")).toString());
                restore.addBindValue(before.value(QStringLiteral("label")).toString());
                restore.addBindValue(before.value(QStringLiteral("reason")).toString());
                restore.addBindValue(before.value(QStringLiteral("active")).toBool() ? 1 : 0);
                restore.addBindValue(before.value(QStringLiteral("updatedByTurnId")).toString());
                restore.addBindValue(cardUid);
                restore.addBindValue(tag);
                restore.addBindValue(turnId);
            }
        } else if (type == QStringLiteral("active_tags_scope")) {
            const QString cardUid = target.value(QStringLiteral("cardUid")).toString();
            const QString sourceType = target.value(QStringLiteral("sourceType")).toString();
            const QString sourceKey = target.value(QStringLiteral("sourceKey")).toString();
            QSqlQuery owners(database);
            owners.prepare(QStringLiteral(R"sql(
                SELECT SUM(CASE WHEN updated_by_turn_id = ? THEN 0 ELSE 1 END)
                FROM database_active_tags WHERE card_uid = ? AND source_type = ? AND source_key = ?
            )sql"));
            owners.addBindValue(turnId);
            owners.addBindValue(cardUid);
            owners.addBindValue(sourceType);
            owners.addBindValue(sourceKey);
            if (!owners.exec() || !owners.next() || owners.value(0).toInt() != 0) {
                if (errorMessage) *errorMessage = QStringLiteral("active tag scope ownership changed before turn rollback");
                return false;
            }
            QSqlQuery remove(database);
            remove.prepare(QStringLiteral(
                "DELETE FROM database_active_tags WHERE card_uid = ? AND source_type = ? AND source_key = ?"));
            remove.addBindValue(cardUid);
            remove.addBindValue(sourceType);
            remove.addBindValue(sourceKey);
            if (!remove.exec()) {
                if (errorMessage) *errorMessage = remove.lastError().text();
                return false;
            }
            for (const QJsonValue& rowValue : before.value(QStringLiteral("rows")).toArray()) {
                const QJsonObject row = rowValue.toObject();
                QSqlQuery insert(database);
                insert.prepare(QStringLiteral(R"sql(
                    INSERT INTO database_active_tags
                        (card_uid, tag, source_type, source_key, label, reason, active, updated_by_turn_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                )sql"));
                insert.addBindValue(cardUid);
                insert.addBindValue(row.value(QStringLiteral("tag")).toString());
                insert.addBindValue(sourceType);
                insert.addBindValue(sourceKey);
                insert.addBindValue(row.value(QStringLiteral("label")).toString());
                insert.addBindValue(row.value(QStringLiteral("reason")).toString());
                insert.addBindValue(row.value(QStringLiteral("active")).toBool() ? 1 : 0);
                insert.addBindValue(row.value(QStringLiteral("updatedByTurnId")).toString());
                if (!insert.exec()) {
                    if (errorMessage) *errorMessage = insert.lastError().text();
                    return false;
                }
            }
            restored = true;
        } else if (type == QStringLiteral("relationship_state")) {
            const QString cardUid = target.value(QStringLiteral("cardUid")).toString();
            const QString pairKey = target.value(QStringLiteral("pairKey")).toString();
            if (!existed) {
                restore.prepare(QStringLiteral(R"sql(
                    DELETE FROM database_relationship_state
                    WHERE card_uid = ? AND pair_key = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(cardUid);
                restore.addBindValue(pairKey);
                restore.addBindValue(turnId);
            } else {
                restore.prepare(QStringLiteral(R"sql(
                    UPDATE database_relationship_state SET
                        role_a = ?, role_b = ?, stage = ?, attitude = ?, summary = ?,
                        updated_by_turn_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE card_uid = ? AND pair_key = ? AND updated_by_turn_id = ?
                )sql"));
                restore.addBindValue(before.value(QStringLiteral("roleA")).toString());
                restore.addBindValue(before.value(QStringLiteral("roleB")).toString());
                restore.addBindValue(before.value(QStringLiteral("stage")).toString());
                restore.addBindValue(before.value(QStringLiteral("attitude")).toString());
                restore.addBindValue(before.value(QStringLiteral("summary")).toString());
                restore.addBindValue(before.value(QStringLiteral("updatedByTurnId")).toString());
                restore.addBindValue(cardUid);
                restore.addBindValue(pairKey);
                restore.addBindValue(turnId);
            }
        } else if (type == QStringLiteral("relationship_history")) {
            restore.prepare(QStringLiteral("DELETE FROM database_relationship_history WHERE id = ?"));
            restore.addBindValue(target.value(QStringLiteral("id")).toVariant());
        } else if (type == QStringLiteral("metric_history")) {
            restore.prepare(QStringLiteral("DELETE FROM database_metric_history WHERE id = ?"));
            restore.addBindValue(target.value(QStringLiteral("id")).toVariant());
        } else if (type == QStringLiteral("story_time_history")) {
            restore.prepare(QStringLiteral("DELETE FROM database_story_time_history WHERE id = ?"));
            restore.addBindValue(target.value(QStringLiteral("id")).toVariant());
        } else if (type == QStringLiteral("stage_history")) {
            restore.prepare(QStringLiteral("DELETE FROM database_stage_history WHERE id = ?"));
            restore.addBindValue(target.value(QStringLiteral("id")).toVariant());
        } else if (type == QStringLiteral("ledger")) {
            restore.prepare(QStringLiteral("DELETE FROM database_plot_ledger WHERE id = ?"));
            restore.addBindValue(target.value(QStringLiteral("id")).toVariant());
        } else {
            if (errorMessage) {
                *errorMessage = QStringLiteral("unknown database turn effect type: %1").arg(type);
            }
            return false;
        }
        if (!restored && (!restore.exec() || restore.numRowsAffected() != 1)) {
            if (errorMessage) {
                *errorMessage = restore.lastError().text().isEmpty()
                    ? QStringLiteral("runtime ownership changed before turn rollback")
                    : restore.lastError().text();
            }
            return false;
        }
        QSqlQuery markReverted(database);
        markReverted.prepare(QStringLiteral(
            "UPDATE database_turn_effects SET reverted_at = CURRENT_TIMESTAMP WHERE id = ? AND reverted_at = ''"));
        markReverted.addBindValue(effectId);
        if (!markReverted.exec() || markReverted.numRowsAffected() != 1) {
            if (errorMessage) {
                *errorMessage = markReverted.lastError().text();
            }
            return false;
        }
    }
    return true;
}
}

DatabaseOperationResult DatabaseRepository::saveTurnResult(const DatabaseTurnResult& resultPayload) const {
    DatabaseTurnDisplay display = resultPayload.display;
    if (display.turnId.trimmed().isEmpty()) {
        return failure(QStringLiteral("invalid_turn"), QStringLiteral("turn id is empty"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message, display.turnId);
    }

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text(), display.turnId);
        } else if (!database.transaction()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text(), display.turnId);
        } else {
            QSqlQuery pendingTurnQuery(database);
            pendingTurnQuery.prepare(QStringLiteral(R"sql(
                SELECT card_uid, rowid, attempt_count, status, message_id
                FROM database_turn_records
                WHERE turn_id = ?
            )sql"));
            pendingTurnQuery.addBindValue(display.turnId.trimmed());
            QString cardUid;
            qint64 turnRowId = 0;
            int attemptCount = -1;
            QString messageId;
            if (!pendingTurnQuery.exec()) {
                result = failure(QStringLiteral("database_error"), pendingTurnQuery.lastError().text(), display.turnId);
            } else if (!pendingTurnQuery.next()) {
                result = failure(QStringLiteral("invalid_state"), QStringLiteral("turn is missing"), display.turnId);
            } else {
                cardUid = pendingTurnQuery.value(0).toString();
                turnRowId = pendingTurnQuery.value(1).toLongLong();
                attemptCount = pendingTurnQuery.value(2).toInt();
                const QString status = pendingTurnQuery.value(3).toString();
                messageId = pendingTurnQuery.value(4).toString();
                if (resultPayload.expectedAttemptCount >= 0
                    && attemptCount != resultPayload.expectedAttemptCount) {
                    result = failure(
                        QStringLiteral("stale_attempt"),
                        QStringLiteral("database turn attempt is no longer current"),
                        display.turnId);
                } else if (status != QStringLiteral("pending")) {
                    result = failure(
                        QStringLiteral("invalid_state"),
                        QStringLiteral("turn is no longer pending"),
                        display.turnId);
                }
            }
            if (result.code.isEmpty()) {
                QSqlQuery newerTerminalTurn(database);
                newerTerminalTurn.prepare(QStringLiteral(R"sql(
                    SELECT 1 FROM database_turn_records
                    WHERE card_uid = ? AND rowid > ?
                      AND status IN ('ready', 'error')
                    LIMIT 1
                )sql"));
                newerTerminalTurn.addBindValue(cardUid);
                newerTerminalTurn.addBindValue(turnRowId);
                if (!newerTerminalTurn.exec()) {
                    result = failure(
                        QStringLiteral("database_error"), newerTerminalTurn.lastError().text(), display.turnId);
                } else if (newerTerminalTurn.next()) {
                    result = failure(
                        QStringLiteral("stale_turn"),
                        QStringLiteral("a newer database turn is already complete"),
                        display.turnId);
                }
            }
            QSqlQuery displayQuery(database);
            displayQuery.prepare(QStringLiteral(R"sql(
                INSERT INTO database_turn_displays (turn_id, title_json, record_json, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(turn_id) DO UPDATE SET
                    title_json = excluded.title_json,
                    record_json = excluded.record_json,
                    updated_at = CURRENT_TIMESTAMP
            )sql"));
            QSqlQuery turnQuery(database);
            turnQuery.prepare(QStringLiteral(R"sql(
                UPDATE database_turn_records AS current
                SET status = 'ready', worker_model = ?, warnings_json = ?,
                    error_code = '', error_message = '', updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE current.turn_id = ? AND current.status = 'pending'
                  AND current.attempt_count = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM database_turn_records AS newer
                      WHERE newer.card_uid = current.card_uid
                        AND newer.rowid > current.rowid
                        AND newer.status IN ('ready', 'error')
                  )
            )sql"));
            turnQuery.addBindValue(sqlText(display.workerModel.trimmed()));
            turnQuery.addBindValue(normalizedWarnings(display.warningsJson));
            turnQuery.addBindValue(display.turnId.trimmed());
            turnQuery.addBindValue(attemptCount);

            QString updateError;
            int effectSequence = 0;
            if (!result.code.isEmpty()) {
                // The pending-turn lookup above already set an actionable failure result.
            } else if (!applyTurnUpdates(database, cardUid, display.turnId.trimmed(), resultPayload.updates,
                    &effectSequence, &updateError)
                || !applyRuntimeTags(database, cardUid, display.turnId.trimmed(),
                    resultPayload.updates.value(QStringLiteral("tags")).toArray(), &effectSequence, &updateError)
                || !applyStoryTimeUpdate(database, cardUid, display.turnId.trimmed(), messageId, turnRowId,
                    resultPayload.updates, &effectSequence, &updateError)
                || !applyStageRules(database, cardUid, display.turnId.trimmed(), turnRowId,
                    resultPayload.databaseConfig, &effectSequence, &display.record, &updateError)) {
                result = failure(QStringLiteral("state_update_error"), updateError, display.turnId);
            } else {
                const QJsonObject storyTime = DatabaseRules::normalizeStoryTimeState(
                    loadStoryTimeState(database, cardUid), cardUid);
                if (storyTime.value(QStringLiteral("enabled")).toBool()
                    && storyTime.value(QStringLiteral("showInRecord")).toBool(true)
                    && storyTime.value(QStringLiteral("initialized")).toBool()) {
                    QJsonObject scene = display.title.value(QStringLiteral("scene")).toObject();
                    scene.insert(QStringLiteral("time"), storyTime.value(QStringLiteral("displayTime")));
                    scene.insert(QStringLiteral("timeSlot"), storyTime.value(QStringLiteral("timeSlotLabel")));
                    scene.insert(QStringLiteral("season"), storyTime.value(QStringLiteral("seasonLabel")));
                    if (!storyTime.value(QStringLiteral("lastDeltaText")).toString().isEmpty()) {
                        scene.insert(QStringLiteral("timeDelta"), storyTime.value(QStringLiteral("lastDeltaText")));
                    }
                    display.title.insert(QStringLiteral("scene"), scene);
                }
                displayQuery.addBindValue(display.turnId.trimmed());
                displayQuery.addBindValue(QString::fromUtf8(QJsonDocument(display.title).toJson(QJsonDocument::Compact)));
                displayQuery.addBindValue(QString::fromUtf8(QJsonDocument(display.record).toJson(QJsonDocument::Compact)));
                if (!displayQuery.exec()) {
                    result = failure(QStringLiteral("display_save_error"), displayQuery.lastError().text(), display.turnId);
                }
            }
            if (!result.code.isEmpty()) {
                // Runtime or display persistence failed above.
            } else if (!turnQuery.exec()) {
                result = failure(QStringLiteral("database_error"), turnQuery.lastError().text(), display.turnId);
            } else if (turnQuery.numRowsAffected() != 1) {
                result = failure(QStringLiteral("invalid_state"), QStringLiteral("turn is no longer pending"), display.turnId);
            } else if (!database.commit()) {
                result = failure(QStringLiteral("database_error"), database.lastError().text(), display.turnId);
            } else {
                result = success(QStringLiteral("database turn result saved"), display.turnId, 1);
            }
            if (!result.ok) {
                database.rollback();
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

namespace {
QString runtimeRoleId(const QJsonObject& item) {
    const QString roleId = item.value(QStringLiteral("role_id")).toString().trimmed();
    if (!roleId.isEmpty()) {
        return roleId;
    }
    return item.value(QStringLiteral("roleId")).toString().trimmed();
}

QString runtimeItemKey(const QJsonObject& item, const QString& primaryKey, const QString& fallbackKey) {
    const QString primary = item.value(primaryKey).toString().trimmed();
    return primary.isEmpty() ? item.value(fallbackKey).toString().trimmed() : primary;
}

QString runtimeRoleMode(const QJsonObject& role) {
    if (role.value(QStringLiteral("enabled")).isBool() && !role.value(QStringLiteral("enabled")).toBool()) {
        return QStringLiteral("disabled");
    }
    QString mode = role.value(QStringLiteral("mode")).toString(
        role.value(QStringLiteral("stateJournalMode")).toString()).trimmed().toLower();
    return mode.isEmpty() ? QStringLiteral("full") : mode;
}

bool roleUsesVariables(const QString& mode) {
    return mode != QStringLiteral("disabled") && mode != QStringLiteral("snapshot_only")
        && mode != QStringLiteral("stages");
}

bool roleUsesStages(const QString& mode) {
    return mode != QStringLiteral("disabled") && mode != QStringLiteral("snapshot_only")
        && mode != QStringLiteral("variables");
}

bool roleUsesSnapshots(const QString& mode) {
    return mode != QStringLiteral("disabled");
}

QJsonValue initialVariableValue(const QJsonObject& variable) {
    const QString valueType = variable.value(QStringLiteral("value_type")).toString().trimmed().toLower();
    if ((valueType == QStringLiteral("text") || valueType == QStringLiteral("string"))
        && variable.contains(QStringLiteral("initial_value"))) {
        return variable.value(QStringLiteral("initial_value"));
    }
    if (variable.contains(QStringLiteral("default_value"))) {
        return variable.value(QStringLiteral("default_value"));
    }
    return variable.value(QStringLiteral("initial_value"));
}

bool explicitSnapshotValue(const QJsonObject& field, QJsonValue* value) {
    for (const QString& key : { QStringLiteral("initial_value"), QStringLiteral("default_value"), QStringLiteral("value") }) {
        if (field.contains(key) && !field.value(key).isNull() && !field.value(key).isUndefined()) {
            if (value) {
                *value = field.value(key);
            }
            return true;
        }
    }
    return false;
}

bool executeInitializationInsert(QSqlQuery& query, int* inserted, int* retained, QString* errorMessage) {
    if (!query.exec()) {
        if (errorMessage) {
            *errorMessage = query.lastError().text();
        }
        return false;
    }
    if (query.numRowsAffected() > 0) {
        ++(*inserted);
    } else {
        ++(*retained);
    }
    return true;
}
}

DatabaseOperationResult DatabaseRepository::initializeRuntime(const QString& cardUid, const QJsonObject& databaseConfig) const {
    const QString card = cardUid.trimmed();
    if (card.isEmpty()) {
        return failure(QStringLiteral("invalid_card"), QStringLiteral("card uid is empty"));
    }
    if (databaseConfig.value(QStringLiteral("enabled")).isBool()
        && !databaseConfig.value(QStringLiteral("enabled")).toBool()) {
        return failure(QStringLiteral("database_disabled"), QStringLiteral("database is disabled for the current card"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message);
    }

    QHash<QString, QString> roleModes;
    QHash<QString, QString> initialStages;
    for (const QJsonValue& value : databaseConfig.value(QStringLiteral("roles")).toArray()) {
        const QJsonObject role = value.toObject();
        const QString roleId = runtimeRoleId(role);
        if (roleId.isEmpty()) {
            continue;
        }
        roleModes.insert(roleId, runtimeRoleMode(role));
        initialStages.insert(roleId, role.value(QStringLiteral("initial_stage")).toString().trimmed());
    }
    const auto modeForRole = [&roleModes](const QString& roleId) {
        return roleModes.value(roleId, QStringLiteral("full"));
    };

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text());
        } else if (!database.transaction()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text());
        } else {
            int inserted = 0;
            int retained = 0;
            int skipped = 0;
            QString errorMessage;

            for (const QJsonValue& value : databaseConfig.value(QStringLiteral("variables")).toArray()) {
                const QJsonObject variable = value.toObject();
                const QString roleId = runtimeRoleId(variable);
                const QString key = runtimeItemKey(variable, QStringLiteral("var_key"), QStringLiteral("key"));
                if (roleId.isEmpty() || key.isEmpty() || !variable.value(QStringLiteral("enabled")).toBool(true)
                    || !roleUsesVariables(modeForRole(roleId))) {
                    ++skipped;
                    continue;
                }
                const QJsonValue initialValue = initialVariableValue(variable);
                if (initialValue.isUndefined() || initialValue.isNull()) {
                    ++skipped;
                    continue;
                }
                const QString label = variable.value(QStringLiteral("var_name")).toString(
                    variable.value(QStringLiteral("label")).toString(key)).trimmed();
                QSqlQuery write(database);
                write.prepare(QStringLiteral(R"sql(
                    INSERT INTO database_runtime_values
                        (card_uid, role_id, field_key, label, value_json, maximum_json, updated_by_turn_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, '', CURRENT_TIMESTAMP)
                    ON CONFLICT(card_uid, role_id, field_key) DO NOTHING
                )sql"));
                write.addBindValue(card);
                write.addBindValue(roleId);
                write.addBindValue(key);
                write.addBindValue(label.isEmpty() ? key : label);
                write.addBindValue(valueJson(initialValue));
                write.addBindValue(variable.value(QStringLiteral("max_value")).isDouble()
                        ? valueJson(variable.value(QStringLiteral("max_value"))) : QStringLiteral(""));
                if (!executeInitializationInsert(write, &inserted, &retained, &errorMessage)) {
                    break;
                }
            }

            if (errorMessage.isEmpty()) {
                for (const QJsonValue& value : databaseConfig.value(QStringLiteral("stages")).toArray()) {
                    const QJsonObject stage = value.toObject();
                    const QString roleId = runtimeRoleId(stage);
                    const QString stageKey = runtimeItemKey(stage, QStringLiteral("stage_key"), QStringLiteral("stageKey"));
                    if (roleId.isEmpty() || stageKey.isEmpty() || !stage.value(QStringLiteral("enabled")).toBool(true)
                        || !roleUsesStages(modeForRole(roleId))
                        || initialStages.value(roleId) != stageKey) {
                        ++skipped;
                        continue;
                    }
                    QJsonObject state{
                        { QStringLiteral("active"), true },
                        { QStringLiteral("source"), QStringLiteral("initialization") },
                        { QStringLiteral("stageName"), stage.value(QStringLiteral("stage_name")).toString(stageKey) },
                        { QStringLiteral("changed"), false },
                        { QStringLiteral("candidateStageKey"), QString() },
                        { QStringLiteral("candidateCount"), 0 },
                        { QStringLiteral("changedAtTurn"), 0 },
                        { QStringLiteral("cooldownUntilTurn"), 0 },
                    };
                    QString activeTag = stage.value(QStringLiteral("activation_tag")).toString(
                        stage.value(QStringLiteral("active_tag")).toString()).trimmed();
                    if (activeTag.isEmpty()) {
                        activeTag = QStringLiteral("database.stage.%1.%2").arg(roleId, stageKey);
                    }
                    QJsonArray stageTags{activeTag};
                    for (const QJsonValue& tagValue : stage.value(QStringLiteral("emits_tags")).toArray()) {
                        const QString tag = tagValue.toString().trimmed();
                        if (!tag.isEmpty() && !stageTags.contains(tag)) {
                            stageTags.append(tag);
                        }
                    }
                    state.insert(QStringLiteral("activeTag"), activeTag);
                    state.insert(QStringLiteral("emitsTags"), stageTags);
                    const QString title = stage.value(QStringLiteral("stage_name")).toString(
                        stage.value(QStringLiteral("title")).toString()).trimmed();
                    if (!title.isEmpty()) {
                        state.insert(QStringLiteral("title"), title);
                    }
                    QSqlQuery write(database);
                    write.prepare(QStringLiteral(R"sql(
                        INSERT INTO database_stage_state
                            (card_uid, role_id, stage_key, state_json, updated_by_turn_id, updated_at)
                        VALUES (?, ?, ?, ?, '', CURRENT_TIMESTAMP)
                        ON CONFLICT(card_uid, role_id, stage_key) DO NOTHING
                    )sql"));
                    write.addBindValue(card);
                    write.addBindValue(roleId);
                    write.addBindValue(stageKey);
                    write.addBindValue(jsonText(state));
                    if (!executeInitializationInsert(write, &inserted, &retained, &errorMessage)) {
                        break;
                    }
                    for (const QJsonValue& tagValue : stageTags) {
                        QSqlQuery tagWrite(database);
                        tagWrite.prepare(QStringLiteral(R"sql(
                            INSERT INTO database_active_tags
                                (card_uid, tag, source_type, source_key, label, reason, active, updated_by_turn_id, updated_at)
                            VALUES (?, ?, 'stage', ?, ?, '初始阶段', 1, '', CURRENT_TIMESTAMP)
                            ON CONFLICT(card_uid, tag) DO NOTHING
                        )sql"));
                        tagWrite.addBindValue(card);
                        tagWrite.addBindValue(tagValue.toString());
                        tagWrite.addBindValue(roleId);
                        tagWrite.addBindValue(title.isEmpty() ? stageKey : title);
                        if (!executeInitializationInsert(tagWrite, &inserted, &retained, &errorMessage)) {
                            break;
                        }
                    }
                    if (!errorMessage.isEmpty()) {
                        break;
                    }
                }
            }

            if (errorMessage.isEmpty()) {
                const QJsonObject defaultStoryTime = DatabaseRules::defaultStoryTimeState(card);
                QSqlQuery storyTime(database);
                storyTime.prepare(QStringLiteral(R"sql(
                    INSERT INTO database_story_time_state (
                        card_uid, enabled, show_in_record, base_time, current_time, elapsed_seconds,
                        season, time_slot, advance_mode, custom_advance_type,
                        custom_advance_min_seconds, custom_advance_max_seconds, display_mode,
                        last_delta_seconds, last_delta_text, last_confidence, updated_by_turn_id,
                        created_at, updated_at
                    ) VALUES (?, 0, 1, ?, '', 0, ?, ?, 'smart', 'range', 300, 900,
                        'datetime_minute', 0, '', '', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(card_uid) DO NOTHING
                )sql"));
                storyTime.addBindValue(card);
                storyTime.addBindValue(defaultStoryTime.value(QStringLiteral("baseTime")).toString());
                storyTime.addBindValue(defaultStoryTime.value(QStringLiteral("season")).toString());
                storyTime.addBindValue(defaultStoryTime.value(QStringLiteral("timeSlot")).toString());
                if (!executeInitializationInsert(storyTime, &inserted, &retained, &errorMessage)) {
                    // Keep the actionable database error from the helper.
                }
            }

            if (errorMessage.isEmpty()) {
                QMap<QString, QJsonObject> snapshotPayloads;
                QMap<QString, QString> snapshotTitles;
                for (const QJsonValue& value : databaseConfig.value(QStringLiteral("snapshotFields")).toArray()) {
                    const QJsonObject field = value.toObject();
                    const QString roleId = runtimeRoleId(field);
                    const QString key = runtimeItemKey(field, QStringLiteral("key"), QStringLiteral("id"));
                    QJsonValue initialValue;
                    if (roleId.isEmpty() || key.isEmpty() || !field.value(QStringLiteral("enabled")).toBool(true)
                        || !roleUsesSnapshots(modeForRole(roleId)) || !explicitSnapshotValue(field, &initialValue)) {
                        ++skipped;
                        continue;
                    }
                    const QString scope = field.value(QStringLiteral("scope")).toString(
                        field.value(QStringLiteral("snapshot_scope")).toString(QStringLiteral("current"))).trimmed();
                    const QString snapshotScope = scope.isEmpty() ? QStringLiteral("current") : scope;
                    QJsonObject payload = snapshotPayloads.value(snapshotScope);
                    QString payloadKey = key;
                    if (payload.contains(payloadKey)) {
                        payloadKey = QStringLiteral("%1.%2").arg(roleId, key);
                    }
                    payload.insert(payloadKey, initialValue);
                    snapshotPayloads.insert(snapshotScope, payload);
                    const QString title = field.value(QStringLiteral("snapshot_title")).toString(
                        field.value(QStringLiteral("title")).toString(QStringLiteral("初始状态"))).trimmed();
                    if (!snapshotTitles.contains(snapshotScope)) {
                        snapshotTitles.insert(snapshotScope, title.isEmpty() ? QStringLiteral("初始状态") : title);
                    }
                }
                for (auto it = snapshotPayloads.cbegin(); it != snapshotPayloads.cend(); ++it) {
                    const QString snapshotId = QStringLiteral("runtime:%1:%2").arg(card, it.key());
                    QSqlQuery existing(database);
                    existing.prepare(QStringLiteral(
                        "SELECT payload_json FROM database_state_snapshots WHERE id = ?"));
                    existing.addBindValue(snapshotId);
                    if (!existing.exec()) {
                        errorMessage = existing.lastError().text();
                        break;
                    }
                    if (existing.next()) {
                        QJsonObject mergedPayload = jsonObject(existing.value(0));
                        bool changed = false;
                        for (auto field = it.value().constBegin(); field != it.value().constEnd(); ++field) {
                            if (!mergedPayload.contains(field.key())) {
                                mergedPayload.insert(field.key(), field.value());
                                changed = true;
                            }
                        }
                        if (!changed) {
                            ++retained;
                            continue;
                        }
                        QSqlQuery update(database);
                        update.prepare(QStringLiteral(R"sql(
                            UPDATE database_state_snapshots
                            SET payload_json = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        )sql"));
                        update.addBindValue(jsonText(mergedPayload));
                        update.addBindValue(snapshotId);
                        if (!executeInitializationInsert(update, &inserted, &retained, &errorMessage)) {
                            break;
                        }
                        continue;
                    }
                    QSqlQuery write(database);
                    write.prepare(QStringLiteral(R"sql(
                        INSERT INTO database_state_snapshots
                            (id, card_uid, scope, title, payload_json, updated_by_turn_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    )sql"));
                    write.addBindValue(snapshotId);
                    write.addBindValue(card);
                    write.addBindValue(it.key());
                    write.addBindValue(snapshotTitles.value(it.key()));
                    write.addBindValue(jsonText(it.value()));
                    if (!executeInitializationInsert(write, &inserted, &retained, &errorMessage)) {
                        break;
                    }
                }
            }

            if (!errorMessage.isEmpty()) {
                result = failure(QStringLiteral("database_error"), errorMessage);
            } else if (!database.commit()) {
                result = failure(QStringLiteral("database_error"), database.lastError().text());
            } else {
                result = success(
                    QStringLiteral("已初始化 %1 项；%2 项已有运行态保持不变，%3 项未满足初始化条件已跳过")
                        .arg(inserted).arg(retained).arg(skipped),
                    {}, inserted);
            }
            if (!result.ok) {
                database.rollback();
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

DatabaseOperationResult DatabaseRepository::configureStoryTime(
    const QString& cardUid, const QJsonObject& draft) const {
    const QString card = cardUid.trimmed();
    if (card.isEmpty()) {
        return failure(QStringLiteral("invalid_card"), QStringLiteral("card uid is empty"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message);
    }
    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open() || !database.transaction()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text());
        } else {
            QJsonObject current = loadStoryTimeState(database, card);
            if (current.isEmpty()) {
                current = DatabaseRules::defaultStoryTimeState(card);
            }
            const QJsonObject configured = DatabaseRules::configureStoryTime(current, draft, card);
            QString errorMessage;
            if (!writeStoryTimeState(database, configured, QString(), &errorMessage)) {
                result = failure(QStringLiteral("database_error"), errorMessage);
            } else {
                const QString oldTime = current.value(QStringLiteral("currentTime")).toString();
                const QString newTime = configured.value(QStringLiteral("currentTime")).toString();
                if (oldTime != newTime && !newTime.isEmpty()) {
                    QSqlQuery history(database);
                    history.prepare(QStringLiteral(R"sql(
                        INSERT INTO database_story_time_history (
                            card_uid, old_time, new_time, delta_seconds, delta_text,
                            confidence, reason, source
                        ) VALUES (?, ?, ?, ?, ?, 'high', ?, 'manual')
                    )sql"));
                    history.addBindValue(card);
                    history.addBindValue(oldTime);
                    history.addBindValue(newTime);
                    history.addBindValue(configured.value(QStringLiteral("elapsedSeconds")).toVariant().toLongLong()
                        - current.value(QStringLiteral("elapsedSeconds")).toVariant().toLongLong());
                    history.addBindValue(QStringLiteral("手动调整剧情时间"));
                    history.addBindValue(draft.value(QStringLiteral("action")).toString(QStringLiteral("configure")));
                    if (!history.exec()) {
                        result = failure(QStringLiteral("database_error"), history.lastError().text());
                    }
                }
                if (result.code.isEmpty() && database.commit()) {
                    result = success(QStringLiteral("剧情时间设置已保存：%1")
                            .arg(configured.value(QStringLiteral("currentTime")).toString()), {}, 1);
                } else if (result.code.isEmpty()) {
                    result = failure(QStringLiteral("database_error"), database.lastError().text());
                }
            }
            if (!result.ok) {
                database.rollback();
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

DatabaseOperationResult DatabaseRepository::markTurnError(
    const QString& turnId, const QString& code, const QString& message, int expectedAttemptCount) const {
    const QString id = turnId.trimmed();
    if (id.isEmpty()) {
        return failure(QStringLiteral("invalid_turn"), QStringLiteral("turn id is empty"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message, id);
    }

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text(), id);
        } else {
            QSqlQuery query(database);
            if (expectedAttemptCount >= 0) {
                query.prepare(QStringLiteral(R"sql(
                    UPDATE database_turn_records
                    SET status = 'error', error_code = ?, error_message = ?,
                        updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                    WHERE turn_id = ? AND status = 'pending' AND attempt_count = ?
                )sql"));
            } else {
                query.prepare(QStringLiteral(R"sql(
                    UPDATE database_turn_records
                    SET status = 'error', error_code = ?, error_message = ?,
                        updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                    WHERE turn_id = ? AND status IN ('pending', 'error')
                )sql"));
            }
            query.addBindValue(code.trimmed().left(80));
            query.addBindValue(sanitizeErrorMessage(message));
            query.addBindValue(id);
            if (expectedAttemptCount >= 0) {
                query.addBindValue(expectedAttemptCount);
            }
            if (!query.exec()) {
                result = failure(QStringLiteral("database_error"), query.lastError().text(), id);
            } else if (query.numRowsAffected() != 1) {
                QSqlQuery current(database);
                current.prepare(QStringLiteral(
                    "SELECT status, attempt_count FROM database_turn_records WHERE turn_id = ?"));
                current.addBindValue(id);
                if (!current.exec()) {
                    result = failure(QStringLiteral("database_error"), current.lastError().text(), id);
                } else if (!current.next()) {
                    result = failure(QStringLiteral("invalid_state"), QStringLiteral("turn is missing"), id);
                } else if (expectedAttemptCount >= 0
                    && current.value(1).toInt() != expectedAttemptCount) {
                    result = failure(
                        QStringLiteral("stale_attempt"),
                        QStringLiteral("database turn attempt is no longer current"),
                        id);
                } else {
                    result = failure(
                        QStringLiteral("invalid_state"),
                        QStringLiteral("turn status does not accept an error update"),
                        id);
                }
            } else {
                result = success(QStringLiteral("database turn marked error"), id, 1);
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

DatabaseOperationResult DatabaseRepository::markMessageSuperseded(const QString& cardUid, const QString& messageId) const {
    return markMessagesSuperseded(cardUid, QStringList{messageId});
}

DatabaseOperationResult DatabaseRepository::markMessagesSuperseded(
    const QString& cardUid, const QStringList& messageIds) const {
    const QString card = cardUid.trimmed();
    QStringList messages;
    for (const QString& messageId : messageIds) {
        const QString message = messageId.trimmed();
        if (!message.isEmpty() && !messages.contains(message)) {
            messages.append(message);
        }
    }
    if (card.isEmpty() || messages.isEmpty()) {
        return failure(QStringLiteral("invalid_turn"), QStringLiteral("card uid or message ids are empty"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message);
    }

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text());
        } else if (!database.transaction()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text());
        } else {
            int affectedRows = 0;
            QString lastTurnId;
            for (int index = messages.size() - 1; index >= 0 && result.code.isEmpty(); --index) {
                QSqlQuery lookup(database);
                lookup.prepare(QStringLiteral(R"sql(
                    SELECT turn_id FROM database_turn_records
                    WHERE card_uid = ? AND message_id = ? AND status != 'superseded'
                )sql"));
                lookup.addBindValue(card);
                lookup.addBindValue(messages.at(index));
                if (!lookup.exec()) {
                    result = failure(QStringLiteral("database_error"), lookup.lastError().text());
                    break;
                }
                if (!lookup.next()) {
                    continue;
                }
                const QString turnId = lookup.value(0).toString();
                QString rollbackError;
                if (!rollbackTurnEffects(database, turnId, &rollbackError)) {
                    result = failure(QStringLiteral("rollback_error"), rollbackError, turnId);
                    break;
                }

                QSqlQuery update(database);
                update.prepare(QStringLiteral(R"sql(
                    UPDATE database_turn_records
                    SET status = 'superseded', updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                    WHERE turn_id = ? AND status != 'superseded'
                )sql"));
                update.addBindValue(turnId);
                if (!update.exec()) {
                    result = failure(QStringLiteral("database_error"), update.lastError().text(), turnId);
                    break;
                }
                if (update.numRowsAffected() != 1) {
                    result = failure(
                        QStringLiteral("turn_not_found"), QStringLiteral("active database turn not found"), turnId);
                    break;
                }
                lastTurnId = turnId;
                ++affectedRows;
            }
            if (!result.code.isEmpty()) {
                // The lookup, effect rollback, or turn update already set an actionable failure result.
            } else if (!database.commit()) {
                result = failure(QStringLiteral("database_error"), database.lastError().text(), lastTurnId);
            } else {
                result = success(
                    QStringLiteral("%1 database turns superseded and runtime updates reverted").arg(affectedRows),
                    lastTurnId,
                    affectedRows);
            }
            if (!result.ok) {
                database.rollback();
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

DatabaseOperationResult DatabaseRepository::retryTurn(const QString& turnId) const {
    const QString id = turnId.trimmed();
    if (id.isEmpty()) {
        return failure(QStringLiteral("invalid_turn"), QStringLiteral("turn id is empty"));
    }
    const DatabaseStatus schema = initializeSchema();
    if (!schema.ok) {
        return failure(QStringLiteral("database_error"), schema.message, id);
    }

    const QString connectionName = makeConnectionName();
    DatabaseOperationResult result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            result = failure(QStringLiteral("database_error"), database.lastError().text(), id);
        } else {
            QSqlQuery query(database);
            query.prepare(QStringLiteral(R"sql(
                UPDATE database_turn_records AS current
                SET status = 'pending', attempt_count = attempt_count + 1,
                    error_code = '', error_message = '', updated_at = CURRENT_TIMESTAMP,
                    completed_at = ''
                WHERE turn_id = ? AND status = 'error'
                  AND NOT EXISTS (
                      SELECT 1 FROM database_turn_records AS newer
                      WHERE newer.card_uid = current.card_uid
                        AND newer.rowid > current.rowid
                        AND newer.status != 'superseded'
                  )
            )sql"));
            query.addBindValue(id);
            if (!query.exec()) {
                result = failure(QStringLiteral("database_error"), query.lastError().text(), id);
            } else if (query.numRowsAffected() != 1) {
                QSqlQuery stale(database);
                stale.prepare(QStringLiteral(R"sql(
                    SELECT 1
                    FROM database_turn_records AS current
                    WHERE current.turn_id = ? AND current.status = 'error'
                       AND EXISTS (
                           SELECT 1 FROM database_turn_records AS newer
                           WHERE newer.card_uid = current.card_uid
                             AND newer.rowid > current.rowid
                             AND newer.status != 'superseded'
                       )
                    LIMIT 1
                )sql"));
                stale.addBindValue(id);
                if (!stale.exec()) {
                    result = failure(QStringLiteral("database_error"), stale.lastError().text(), id);
                } else if (stale.next()) {
                    result = failure(
                        QStringLiteral("stale_turn"),
                        QStringLiteral("a newer database turn already exists"),
                        id);
                } else {
                    result = failure(
                        QStringLiteral("invalid_state"), QStringLiteral("only error turns can be retried"), id);
                }
            } else {
                result = success(QStringLiteral("database turn queued for retry"), id, 1);
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

std::optional<DatabaseTurnView> DatabaseRepository::turnByMessageId(const QString& cardUid, const QString& messageId) const {
    const QString connectionName = makeConnectionName();
    std::optional<DatabaseTurnView> result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (database.open()) {
            QSqlQuery query(database);
            query.prepare(turnSelectSql() + QStringLiteral(" WHERE r.card_uid = ? AND r.message_id = ? LIMIT 1"));
            query.addBindValue(cardUid.trimmed());
            query.addBindValue(messageId.trimmed());
            if (query.exec() && query.next()) {
                result = turnViewFromQuery(query);
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

std::optional<DatabaseTurnView> DatabaseRepository::turnById(const QString& turnId) const {
    const QString connectionName = makeConnectionName();
    std::optional<DatabaseTurnView> result;
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (database.open()) {
            QSqlQuery query(database);
            query.prepare(turnSelectSql() + QStringLiteral(" WHERE r.turn_id = ? LIMIT 1"));
            query.addBindValue(turnId.trimmed());
            if (query.exec() && query.next()) {
                result = turnViewFromQuery(query);
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

QList<DatabaseTurnView> DatabaseRepository::recentTurns(const QString& cardUid, int limit) const {
    QList<DatabaseTurnView> result;
    const QString connectionName = makeConnectionName();
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (database.open()) {
            QSqlQuery query(database);
            query.prepare(turnSelectSql() + QStringLiteral(R"sql(
                WHERE r.card_uid = ? AND r.status != 'superseded'
                ORDER BY r.updated_at DESC, r.turn_index DESC
                LIMIT ?
            )sql"));
            query.addBindValue(cardUid.trimmed());
            query.addBindValue(qBound(1, limit, 200));
            if (query.exec()) {
                while (query.next()) {
                    result.append(turnViewFromQuery(query));
                }
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return result;
}

DatabaseRuntimeView DatabaseRepository::runtimeView(const QString& cardUid, int ledgerLimit) const {
    DatabaseRuntimeView view;
    view.cardUid = cardUid.trimmed();
    if (view.cardUid.isEmpty() || !initializeSchema().ok) {
        return view;
    }

    const QString connectionName = makeConnectionName();
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (database.open()) {
            QSqlQuery snapshots(database);
            snapshots.prepare(QStringLiteral(R"sql(
                SELECT scope, title, payload_json, updated_at
                FROM database_state_snapshots WHERE card_uid = ?
                ORDER BY updated_at DESC, scope ASC
            )sql"));
            snapshots.addBindValue(view.cardUid);
            if (snapshots.exec()) {
                while (snapshots.next()) {
                    view.snapshots.append(QJsonObject{
                        { QStringLiteral("scope"), snapshots.value(0).toString() },
                        { QStringLiteral("title"), snapshots.value(1).toString() },
                        { QStringLiteral("payload"), jsonObject(snapshots.value(2)) },
                        { QStringLiteral("updatedAt"), snapshots.value(3).toString() },
                    });
                }
            }

            QSqlQuery latestDisplay(database);
            latestDisplay.prepare(QStringLiteral(R"sql(
                SELECT d.record_json
                FROM database_turn_displays d
                INNER JOIN database_turn_records r ON r.turn_id = d.turn_id
                WHERE r.card_uid = ? AND r.status = 'ready'
                ORDER BY r.rowid DESC LIMIT 1
            )sql"));
            latestDisplay.addBindValue(view.cardUid);
            if (latestDisplay.exec() && latestDisplay.next()) {
                const QJsonArray characters = jsonObject(latestDisplay.value(0))
                    .value(QStringLiteral("characters")).toArray();
                for (const QJsonValue& character : characters) {
                    if (character.isObject()) {
                        view.characters.append(character.toObject());
                    }
                }
            }

            QSqlQuery variables(database);
            variables.prepare(QStringLiteral(R"sql(
                SELECT role_id, field_key, label, value_json, maximum_json, updated_at
                FROM database_runtime_values WHERE card_uid = ?
                ORDER BY role_id COLLATE NOCASE, field_key COLLATE NOCASE
            )sql"));
            variables.addBindValue(view.cardUid);
            if (variables.exec()) {
                while (variables.next()) {
                    QJsonObject item{
                        { QStringLiteral("roleId"), variables.value(0).toString() },
                        { QStringLiteral("key"), variables.value(1).toString() },
                        { QStringLiteral("label"), variables.value(2).toString() },
                        { QStringLiteral("value"), wrappedJsonValue(variables.value(3)) },
                        { QStringLiteral("updatedAt"), variables.value(5).toString() },
                    };
                    if (!variables.value(4).toString().isEmpty()) {
                        item.insert(QStringLiteral("maximum"), wrappedJsonValue(variables.value(4)));
                    }
                    view.variables.append(item);
                }
            }

            QSqlQuery metricHistory(database);
            metricHistory.prepare(QStringLiteral(R"sql(
                SELECT role_id, field_key, label, value_json, maximum_json,
                       delta_json, reason, turn_id, created_at
                FROM database_metric_history WHERE card_uid = ?
                ORDER BY id DESC LIMIT 100
            )sql"));
            metricHistory.addBindValue(view.cardUid);
            if (metricHistory.exec()) {
                while (metricHistory.next()) {
                    QJsonObject item{
                        { QStringLiteral("roleId"), metricHistory.value(0).toString() },
                        { QStringLiteral("key"), metricHistory.value(1).toString() },
                        { QStringLiteral("label"), metricHistory.value(2).toString() },
                        { QStringLiteral("value"), wrappedJsonValue(metricHistory.value(3)) },
                        { QStringLiteral("reason"), metricHistory.value(6).toString() },
                        { QStringLiteral("turnId"), metricHistory.value(7).toString() },
                        { QStringLiteral("createdAt"), metricHistory.value(8).toString() },
                    };
                    if (!metricHistory.value(4).toString().isEmpty()) {
                        item.insert(QStringLiteral("maximum"), wrappedJsonValue(metricHistory.value(4)));
                    }
                    if (!metricHistory.value(5).toString().isEmpty()) {
                        item.insert(QStringLiteral("delta"), wrappedJsonValue(metricHistory.value(5)));
                    }
                    view.metricHistory.append(item);
                }
            }

            QSqlQuery relationships(database);
            relationships.prepare(QStringLiteral(R"sql(
                SELECT pair_key, role_a, role_b, stage, attitude, summary, updated_at
                FROM database_relationship_state WHERE card_uid = ?
                ORDER BY updated_at DESC, pair_key COLLATE NOCASE
            )sql"));
            relationships.addBindValue(view.cardUid);
            if (relationships.exec()) {
                while (relationships.next()) {
                    view.relationships.append(QJsonObject{
                        { QStringLiteral("pairKey"), relationships.value(0).toString() },
                        { QStringLiteral("roleA"), relationships.value(1).toString() },
                        { QStringLiteral("roleB"), relationships.value(2).toString() },
                        { QStringLiteral("stage"), relationships.value(3).toString() },
                        { QStringLiteral("attitude"), relationships.value(4).toString() },
                        { QStringLiteral("summary"), relationships.value(5).toString() },
                        { QStringLiteral("updatedAt"), relationships.value(6).toString() },
                    });
                }
            }

            QSqlQuery relationshipHistory(database);
            relationshipHistory.prepare(QStringLiteral(R"sql(
                SELECT pair_key, role_a, role_b, previous_stage, stage,
                       attitude, summary, change_text, created_at
                FROM database_relationship_history WHERE card_uid = ?
                ORDER BY id DESC LIMIT 100
            )sql"));
            relationshipHistory.addBindValue(view.cardUid);
            if (relationshipHistory.exec()) {
                while (relationshipHistory.next()) {
                    view.relationshipHistory.append(QJsonObject{
                        { QStringLiteral("pairKey"), relationshipHistory.value(0).toString() },
                        { QStringLiteral("roleA"), relationshipHistory.value(1).toString() },
                        { QStringLiteral("roleB"), relationshipHistory.value(2).toString() },
                        { QStringLiteral("previousStage"), relationshipHistory.value(3).toString() },
                        { QStringLiteral("stage"), relationshipHistory.value(4).toString() },
                        { QStringLiteral("attitude"), relationshipHistory.value(5).toString() },
                        { QStringLiteral("summary"), relationshipHistory.value(6).toString() },
                        { QStringLiteral("change"), relationshipHistory.value(7).toString() },
                        { QStringLiteral("createdAt"), relationshipHistory.value(8).toString() },
                    });
                }
            }

            QSqlQuery stages(database);
            stages.prepare(QStringLiteral(R"sql(
                SELECT role_id, stage_key, state_json, updated_at
                FROM database_stage_state WHERE card_uid = ?
                ORDER BY role_id COLLATE NOCASE, stage_key COLLATE NOCASE
            )sql"));
            stages.addBindValue(view.cardUid);
            if (stages.exec()) {
                while (stages.next()) {
                    view.stages.append(QJsonObject{
                        { QStringLiteral("roleId"), stages.value(0).toString() },
                        { QStringLiteral("stageKey"), stages.value(1).toString() },
                        { QStringLiteral("state"), jsonObject(stages.value(2)) },
                        { QStringLiteral("updatedAt"), stages.value(3).toString() },
                    });
                }
            }

            QSqlQuery ledger(database);
            ledger.prepare(QStringLiteral(R"sql(
                SELECT entry_type, content, payload_json, created_at
                FROM database_plot_ledger WHERE card_uid = ?
                ORDER BY id DESC LIMIT ?
            )sql"));
            ledger.addBindValue(view.cardUid);
            ledger.addBindValue(qBound(1, ledgerLimit, 200));
            if (ledger.exec()) {
                while (ledger.next()) {
                    view.ledger.append(QJsonObject{
                        { QStringLiteral("entryType"), ledger.value(0).toString() },
                        { QStringLiteral("content"), ledger.value(1).toString() },
                        { QStringLiteral("payload"), jsonObject(ledger.value(2)) },
                        { QStringLiteral("createdAt"), ledger.value(3).toString() },
                    });
                }
            }

            view.storyTime = DatabaseRules::normalizeStoryTimeState(
                loadStoryTimeState(database, view.cardUid), view.cardUid);

            QSqlQuery storyHistory(database);
            storyHistory.prepare(QStringLiteral(R"sql(
                SELECT old_time, new_time, delta_seconds, delta_text, confidence,
                       reason, source, turn_ordinal, created_at
                FROM database_story_time_history WHERE card_uid = ?
                ORDER BY id DESC LIMIT 50
            )sql"));
            storyHistory.addBindValue(view.cardUid);
            if (storyHistory.exec()) {
                while (storyHistory.next()) {
                    view.storyTimeHistory.append(QJsonObject{
                        { QStringLiteral("oldTime"), storyHistory.value(0).toString() },
                        { QStringLiteral("newTime"), storyHistory.value(1).toString() },
                        { QStringLiteral("deltaSeconds"), storyHistory.value(2).toInt() },
                        { QStringLiteral("deltaText"), storyHistory.value(3).toString() },
                        { QStringLiteral("confidence"), storyHistory.value(4).toString() },
                        { QStringLiteral("reason"), storyHistory.value(5).toString() },
                        { QStringLiteral("source"), storyHistory.value(6).toString() },
                        { QStringLiteral("turnOrdinal"), storyHistory.value(7).toLongLong() },
                        { QStringLiteral("createdAt"), storyHistory.value(8).toString() },
                    });
                }
            }

            QSqlQuery stageHistory(database);
            stageHistory.prepare(QStringLiteral(R"sql(
                SELECT role_id, role_name, from_stage_key, from_stage_name,
                       to_stage_key, to_stage_name, trigger_values_json, reason,
                       active_tag, turn_ordinal, created_at
                FROM database_stage_history WHERE card_uid = ?
                ORDER BY id DESC LIMIT 50
            )sql"));
            stageHistory.addBindValue(view.cardUid);
            if (stageHistory.exec()) {
                while (stageHistory.next()) {
                    view.stageHistory.append(QJsonObject{
                        { QStringLiteral("roleId"), stageHistory.value(0).toString() },
                        { QStringLiteral("roleName"), stageHistory.value(1).toString() },
                        { QStringLiteral("fromStageKey"), stageHistory.value(2).toString() },
                        { QStringLiteral("fromStageName"), stageHistory.value(3).toString() },
                        { QStringLiteral("toStageKey"), stageHistory.value(4).toString() },
                        { QStringLiteral("toStageName"), stageHistory.value(5).toString() },
                        { QStringLiteral("triggerValues"), jsonObject(stageHistory.value(6)) },
                        { QStringLiteral("reason"), stageHistory.value(7).toString() },
                        { QStringLiteral("activeTag"), stageHistory.value(8).toString() },
                        { QStringLiteral("turnOrdinal"), stageHistory.value(9).toLongLong() },
                        { QStringLiteral("createdAt"), stageHistory.value(10).toString() },
                    });
                }
            }

            QSqlQuery activeTags(database);
            activeTags.prepare(QStringLiteral(R"sql(
                SELECT tag, source_type, source_key, label, reason, updated_at
                FROM database_active_tags WHERE card_uid = ? AND active = 1
                ORDER BY source_type, tag COLLATE NOCASE
            )sql"));
            activeTags.addBindValue(view.cardUid);
            if (activeTags.exec()) {
                while (activeTags.next()) {
                    view.activeTags.append(QJsonObject{
                        { QStringLiteral("tag"), activeTags.value(0).toString() },
                        { QStringLiteral("sourceType"), activeTags.value(1).toString() },
                        { QStringLiteral("sourceKey"), activeTags.value(2).toString() },
                        { QStringLiteral("label"), activeTags.value(3).toString() },
                        { QStringLiteral("reason"), activeTags.value(4).toString() },
                        { QStringLiteral("updatedAt"), activeTags.value(5).toString() },
                    });
                }
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return view;
}

DatabaseDebugTableView DatabaseRepository::debugTable(
    const QString& tableName, const QString& cardUid, int offset, int limit) const {
    DatabaseDebugTableView view;
    view.tableName = tableName.trimmed();
    view.offset = qMax(0, offset);
    view.limit = qBound(1, limit, 200);

    const std::optional<DebugTableSpec> spec = debugTableSpec(view.tableName);
    if (!spec) {
        view.message = QStringLiteral("table is not available for database diagnostics");
        return view;
    }
    if (spec->requiresCardUid && cardUid.trimmed().isEmpty()) {
        view.message = QStringLiteral("current card uid is required for database diagnostics");
        return view;
    }
    const DatabaseStatus status = initializeSchema();
    if (!status.ok) {
        view.message = status.message;
        return view;
    }

    const QString connectionName = makeConnectionName();
    {
        QSqlDatabase database = QSqlDatabase::addDatabase(QStringLiteral("QSQLITE"), connectionName);
        database.setDatabaseName(paths_.databasePath());
        if (!database.open()) {
            view.message = database.lastError().text();
        } else {
            QSqlQuery count(database);
            count.prepare(spec->countSql);
            if (spec->requiresCardUid) {
                count.addBindValue(cardUid.trimmed());
            }
            if (!count.exec() || !count.next()) {
                view.message = count.lastError().text();
            } else {
                view.totalRows = count.value(0).toInt();

                QSqlQuery rows(database);
                rows.prepare(spec->selectSql);
                if (spec->requiresCardUid) {
                    rows.addBindValue(cardUid.trimmed());
                }
                rows.addBindValue(view.limit);
                rows.addBindValue(view.offset);
                if (!rows.exec()) {
                    view.message = rows.lastError().text();
                } else {
                    const QSqlRecord record = rows.record();
                    for (int column = 0; column < record.count(); ++column) {
                        view.columns.append(record.fieldName(column));
                    }
                    while (rows.next()) {
                        QJsonObject item;
                        for (int column = 0; column < record.count(); ++column) {
                            const QString columnName = record.fieldName(column);
                            item.insert(columnName, debugCellValue(columnName, rows.value(column)));
                        }
                        view.rows.append(item);
                    }
                    view.ok = true;
                    view.message = QStringLiteral("database diagnostic table loaded");
                }
            }
        }
        database.close();
    }
    QSqlDatabase::removeDatabase(connectionName);
    return view;
}
