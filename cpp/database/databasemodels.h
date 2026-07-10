#pragma once

#include <QJsonObject>
#include <QJsonValue>
#include <QMap>
#include <QString>
#include <QStringList>

enum class ReplyDisplayMode {
    SplitBubbles,
    StateRecord,
};

enum class DatabaseTurnStatus {
    Pending,
    Ready,
    Error,
    Superseded,
};

QString replyDisplayModeToString(ReplyDisplayMode mode);
ReplyDisplayMode replyDisplayModeFromString(const QString& value, bool* recognized = nullptr);
QString databaseTurnStatusToString(DatabaseTurnStatus status);
DatabaseTurnStatus databaseTurnStatusFromString(const QString& value, bool* recognized = nullptr);
QJsonObject normalizeDatabaseUpdates(const QJsonValue& value, const QJsonObject& databaseConfig,
    QStringList* warnings = nullptr);

struct DatabaseWorkerConfig {
    int schemaVersion{1};
    bool enabled{true};
    bool autoUpdate{true};
    QString apiType{QStringLiteral("openai_compatible")};
    QString apiBaseUrl;
    QString apiKey;
    QString model;
    double temperature{};
    int requestTimeout{120};
    int inputTurnCount{3};
    int maxRepairAttempts{1};

    bool apiKeyConfigured() const;
};

struct DatabaseTurnRecord {
    QString turnId;
    QString cardUid;
    QString conversationId;
    QString messageId;
    int turnIndex{};
    QString contentHash;
    DatabaseTurnStatus status{DatabaseTurnStatus::Pending};
    QString triggerSource{QStringLiteral("chat_complete")};
    QString workerModel;
    int attemptCount{};
    QString errorCode;
    QString errorMessage;
    QString warningsJson{QStringLiteral("[]")};
    QString createdAt;
    QString updatedAt;
    QString completedAt;
};

struct DatabaseTurnDisplay {
    QString turnId;
    QJsonObject title;
    QJsonObject record;
    QString workerModel;
    QString warningsJson{QStringLiteral("[]")};
    QString createdAt;
    QString updatedAt;
};

struct DatabaseTurnResult {
    DatabaseTurnDisplay display;
    QJsonObject updates;
    QJsonObject databaseConfig;
    int expectedAttemptCount{-1};
};

struct DatabaseTurnView {
    DatabaseTurnRecord turn;
    DatabaseTurnDisplay display;
    bool hasDisplay{};
};

struct DatabaseRuntimeView {
    QString cardUid;
    QList<QJsonObject> snapshots;
    QList<QJsonObject> characters;
    QList<QJsonObject> variables;
    QList<QJsonObject> metricHistory;
    QList<QJsonObject> relationships;
    QList<QJsonObject> relationshipHistory;
    QList<QJsonObject> stages;
    QList<QJsonObject> ledger;
    QJsonObject storyTime;
    QList<QJsonObject> storyTimeHistory;
    QList<QJsonObject> stageHistory;
    QList<QJsonObject> activeTags;
};

struct DatabaseDebugTableView {
    bool ok{};
    QString message;
    QString tableName;
    QStringList columns;
    QList<QJsonObject> rows;
    int totalRows{};
    int offset{};
    int limit{50};
};

struct DatabaseOperationResult {
    bool ok{};
    QString code;
    QString message;
    QString turnId;
    int affectedRows{};
};

struct DatabaseStatus {
    bool ok{};
    QString databasePath;
    QString message;
    int schemaVersion{};
};

struct DatabaseOverview {
    DatabaseStatus status;
    QString rootPath;
    QString directoryPath;
    QString relativePath;
    bool fileExists{};
    qint64 fileSizeBytes{};
    QStringList tableNames;
    QMap<QString, int> tableCounts;
};
