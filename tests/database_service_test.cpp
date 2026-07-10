#include "database/databasepaths.h"
#include "database/databaseservice.h"
#include "database/legacystatejournaladapter.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
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
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
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
    if (status.schemaVersion != 1) {
        return fail(QStringLiteral("unexpected schema version")) ? 0 : 1;
    }

    QString errorMessage;
    QString schemaVersion;
    if (!queryScalar(paths.databasePath(),
            QStringLiteral("SELECT value FROM database_meta WHERE key = 'schema_version'"),
            &schemaVersion,
            &errorMessage)
        || schemaVersion != QStringLiteral("1")) {
        return fail(QStringLiteral("schema version meta missing: %1").arg(errorMessage)) ? 0 : 1;
    }

    QString tableName;
    if (!queryScalar(paths.databasePath(),
            QStringLiteral("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'database_state_snapshots'"),
            &tableName,
            &errorMessage)
        || tableName != QStringLiteral("database_state_snapshots")) {
        return fail(QStringLiteral("database_state_snapshots table missing: %1").arg(errorMessage)) ? 0 : 1;
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

    return 0;
}
