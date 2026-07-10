#include "database/databaserepository.h"

#include <QSqlDatabase>
#include <QSqlError>
#include <QSqlQuery>
#include <QStringList>
#include <QUuid>
#include <QFileInfo>
#include <QVariant>

#include <utility>

namespace {
constexpr int kDatabaseSchemaVersion = 1;

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
        QStringLiteral("database_stage_state"),
        QStringLiteral("database_plot_ledger"),
    };
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
        } else if (!database.transaction()) {
            errorMessage = QStringLiteral("failed to start database transaction: %1").arg(database.lastError().text());
        } else {
            QSqlQuery query(database);
            const QStringList statements = {
                QStringLiteral("PRAGMA foreign_keys = ON"),
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
                    INSERT OR REPLACE INTO database_meta (key, value, updated_at)
                    VALUES ('schema_version', '1', CURRENT_TIMESTAMP)
                )sql"),
            };

            bool statementsOk = true;
            for (const QString& statement : statements) {
                if (!execSchemaStatement(query, statement, &errorMessage)) {
                    statementsOk = false;
                    break;
                }
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

        database.close();
    }

    QSqlDatabase::removeDatabase(connectionName);

    status.ok = initialized;
    status.message = initialized
        ? QStringLiteral("database schema initialized")
        : errorMessage;
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
