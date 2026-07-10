#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QVariantList>
#include <QVariantMap>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(tempDir.path()));
    FantarealBridge bridge;

    const QVariantMap status = bridge.databaseStatus();
    const QString databasePath = status.value(QStringLiteral("databasePath")).toString();
    if (!status.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("databaseStatus should be ok: %1").arg(status.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (status.value(QStringLiteral("relativePath")).toString() != QStringLiteral("data/database/database.db")
        || databasePath.contains(QStringLiteral("state_journal"))
        || !QFileInfo::exists(databasePath)) {
        return fail(QStringLiteral("databaseStatus should expose the new database runtime file")) ? 0 : 1;
    }
    if (status.value(QStringLiteral("schemaVersion")).toInt() != 1
        || !status.value(QStringLiteral("fileExists")).toBool()
        || status.value(QStringLiteral("fileSizeBytes")).toLongLong() <= 0) {
        return fail(QStringLiteral("databaseStatus should expose schema and file details")) ? 0 : 1;
    }

    const QVariantList tables = status.value(QStringLiteral("tables")).toList();
    if (tables.size() < 4) {
        return fail(QStringLiteral("databaseStatus should expose core database tables")) ? 0 : 1;
    }
    const QVariantMap counts = status.value(QStringLiteral("tableCounts")).toMap();
    if (!counts.contains(QStringLiteral("database_state_snapshots"))
        || !counts.contains(QStringLiteral("database_stage_state"))
        || !counts.contains(QStringLiteral("database_plot_ledger"))) {
        return fail(QStringLiteral("databaseStatus should expose table counts by table name")) ? 0 : 1;
    }

    const QStringList rows = bridge.databaseRows();
    if (rows.isEmpty()
        || !rows.join(QLatin1Char('\n')).contains(QStringLiteral("状态快照"))
        || !rows.join(QLatin1Char('\n')).contains(QStringLiteral("Schema"))) {
        return fail(QStringLiteral("databaseRows should expose user-facing database summary rows")) ? 0 : 1;
    }

    const QVariantMap refreshed = bridge.refreshDatabaseStatus();
    if (!refreshed.value(QStringLiteral("ok")).toBool()
        || refreshed.value(QStringLiteral("databasePath")).toString() != databasePath) {
        return fail(QStringLiteral("refreshDatabaseStatus should update and return the same runtime status")) ? 0 : 1;
    }

    return 0;
}
