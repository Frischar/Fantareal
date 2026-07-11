#pragma once

#include "database/databasemodels.h"

#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QList>
#include <QObject>
#include <QPointer>
#include <QSet>
#include <QStringList>

class QNetworkAccessManager;
class QNetworkReply;

struct DatabaseWorkerRequest {
    DatabaseTurnRecord turn;
    QString assistantContent;
    QString roleName;
    QJsonObject databaseConfig;
    QJsonArray recentHistory;
};

class DatabaseWorker final : public QObject {
    Q_OBJECT

public:
    explicit DatabaseWorker(QString rootPath, QObject* parent = nullptr);

    void start(const DatabaseWorkerRequest& request);
    void cancel(const QString& turnId);
    bool isActive(const QString& turnId) const;

    void fetchModels();
    void testConnection();

signals:
    void turnFinished(const QString& messageId, const DatabaseOperationResult& result);
    void modelsFetched(const QStringList& models, const DatabaseOperationResult& result);
    void connectionTested(const DatabaseOperationResult& result);

private:
    void dispatchNext(const QString& cardUid);
    void sendWorkerRequest(const DatabaseWorkerRequest& request, const DatabaseWorkerConfig& config,
        const QString& prompt, int repairAttempt, bool includeResponseFormat);
    void finishTurn(const DatabaseWorkerRequest& request, const DatabaseOperationResult& result,
        bool continueCardQueue = true);
    void failTurn(const DatabaseWorkerRequest& request, const QString& code, const QString& message);

    QString rootPath_;
    QNetworkAccessManager* network_{};
    QHash<QString, QList<DatabaseWorkerRequest>> queuedRequests_;
    QSet<QString> queuedTurnIds_;
    QHash<QString, QString> activeTurnByCard_;
    QHash<QString, QPointer<QNetworkReply>> activeReplies_;
    QHash<QString, DatabaseWorkerRequest> activeRequests_;
    QSet<QString> cancelledTurnIds_;
};
