#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
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

    const QDir root(tempDir.path());
    if (!QDir().mkpath(root.absoluteFilePath(QStringLiteral("data")))) {
        return fail(QStringLiteral("failed to create data directory")) ? 0 : 1;
    }
    const QJsonObject role{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("mode"), QStringLiteral("full") },
        { QStringLiteral("initial_stage"), QStringLiteral("start") },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("var_key"), QStringLiteral("affection") },
              { QStringLiteral("var_name"), QStringLiteral("好感度") },
              { QStringLiteral("default_value"), 12 },
              { QStringLiteral("max_value"), 100 },
          } } },
        { QStringLiteral("stages"), QJsonArray{ QJsonObject{
              { QStringLiteral("stage_key"), QStringLiteral("start") },
              { QStringLiteral("stage_name"), QStringLiteral("初始阶段") },
          } } },
        { QStringLiteral("snapshotFields"), QJsonArray{ QJsonObject{
              { QStringLiteral("key"), QStringLiteral("location") },
              { QStringLiteral("initial_value"), QStringLiteral("咖啡馆") },
          } } },
    };
    const QJsonObject card{
        { QStringLiteral("card_uid"), QStringLiteral("bridge-init-card") },
        { QStringLiteral("raw"), QJsonObject{
              { QStringLiteral("name"), QStringLiteral("数据库测试角色") },
              { QStringLiteral("stateJournal"), QJsonObject{
                    { QStringLiteral("enabled"), true },
                    { QStringLiteral("roles"), QJsonArray{ role } },
                } },
          } },
    };
    QFile cardFile(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")));
    if (!cardFile.open(QIODevice::WriteOnly | QIODevice::Text)
        || cardFile.write(QJsonDocument(card).toJson(QJsonDocument::Compact)) < 1) {
        return fail(QStringLiteral("failed to write runtime card fixture")) ? 0 : 1;
    }
    cardFile.close();

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
    if (status.value(QStringLiteral("schemaVersion")).toInt() != 5
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
    const QVariantMap runtime = bridge.databaseRuntime();
    if (!runtime.contains(QStringLiteral("snapshots")) || !runtime.contains(QStringLiteral("characters"))
        || !runtime.contains(QStringLiteral("variables"))
        || !runtime.contains(QStringLiteral("metricHistory"))
        || !runtime.contains(QStringLiteral("relationships"))
        || !runtime.contains(QStringLiteral("relationshipHistory"))
        || !runtime.contains(QStringLiteral("stages")) || !runtime.contains(QStringLiteral("ledger"))
        || !runtime.contains(QStringLiteral("storyTime"))
        || !runtime.contains(QStringLiteral("storyTimeHistory"))
        || !runtime.contains(QStringLiteral("stageHistory"))
        || !runtime.contains(QStringLiteral("activeTags"))) {
        return fail(QStringLiteral("database runtime property should expose all native UI sections")) ? 0 : 1;
    }

    const QStringList rows = bridge.databaseRows();
    if (rows.isEmpty()
        || !rows.join(QLatin1Char('\n')).contains(QStringLiteral("数据表快照"))
        || !rows.join(QLatin1Char('\n')).contains(QStringLiteral("Schema"))) {
        return fail(QStringLiteral("databaseRows should expose user-facing database summary rows")) ? 0 : 1;
    }

    const QVariantMap refreshed = bridge.refreshDatabaseStatus();
    if (!refreshed.value(QStringLiteral("ok")).toBool()
        || refreshed.value(QStringLiteral("databasePath")).toString() != databasePath) {
        return fail(QStringLiteral("refreshDatabaseStatus should update and return the same runtime status")) ? 0 : 1;
    }

    const QVariantMap initialized = bridge.initializeDatabaseRuntime();
    if (!initialized.value(QStringLiteral("ok")).toBool() || initialized.value(QStringLiteral("affectedRows")).toInt() < 4) {
        return fail(QStringLiteral("database bridge should initialize the current card runtime")) ? 0 : 1;
    }
    const QVariantMap initializedRuntime = bridge.databaseRuntime();
    if (initializedRuntime.value(QStringLiteral("variables")).toList().size() != 1
        || initializedRuntime.value(QStringLiteral("stages")).toList().size() != 1
        || initializedRuntime.value(QStringLiteral("snapshots")).toList().size() != 1
        || initializedRuntime.value(QStringLiteral("activeTags")).toList().isEmpty()
        || initializedRuntime.value(QStringLiteral("storyTime")).toMap().isEmpty()) {
        return fail(QStringLiteral("database bridge should refresh native runtime data after initialization")) ? 0 : 1;
    }
    const QVariantMap repeated = bridge.initializeDatabaseRuntime();
    if (!repeated.value(QStringLiteral("ok")).toBool() || repeated.value(QStringLiteral("affectedRows")).toInt() != 0) {
        return fail(QStringLiteral("database bridge initialization should retain existing runtime values")) ? 0 : 1;
    }
    const QVariantMap storyTimeSaved = bridge.saveDatabaseStoryTimeDraft(QVariantMap{
        { QStringLiteral("action"), QStringLiteral("initialize") },
        { QStringLiteral("baseTime"), QStringLiteral("2026-05-06 09:30:00") },
        { QStringLiteral("advanceMode"), QStringLiteral("smart") },
        { QStringLiteral("displayMode"), QStringLiteral("datetime_minute") },
    });
    const QVariantMap storyTimeRuntime = bridge.databaseRuntime().value(QStringLiteral("storyTime")).toMap();
    if (!storyTimeSaved.value(QStringLiteral("ok")).toBool()
        || !storyTimeRuntime.value(QStringLiteral("enabled")).toBool()
        || storyTimeRuntime.value(QStringLiteral("currentTime")).toString() != QStringLiteral("2026-05-06 09:30:00")) {
        return fail(QStringLiteral("database bridge should initialize and refresh story time settings")) ? 0 : 1;
    }
    const QVariantMap noAssistant = bridge.generateLatestDatabaseTurn();
    if (noAssistant.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("manual state record generation should reject an empty conversation")) ? 0 : 1;
    }
    const QVariantMap debugTable = bridge.loadDatabaseDebugTable(
        QStringLiteral("database_runtime_values"), 0, 20);
    if (!debugTable.value(QStringLiteral("ok")).toBool()
        || debugTable.value(QStringLiteral("tableName")).toString() != QStringLiteral("database_runtime_values")
        || debugTable.value(QStringLiteral("totalRows")).toInt() != 1
        || debugTable.value(QStringLiteral("rows")).toList().size() != 1) {
        return fail(QStringLiteral("database bridge should expose card-scoped diagnostic rows")) ? 0 : 1;
    }
    const QVariantMap rejectedTable = bridge.loadDatabaseDebugTable(
        QStringLiteral("sqlite_master"), 0, 20);
    if (rejectedTable.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("database bridge must reject arbitrary diagnostic table names")) ? 0 : 1;
    }

    return 0;
}
