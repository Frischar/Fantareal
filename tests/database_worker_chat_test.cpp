#include "fantarealbridge.h"
#include "database/databaseservice.h"
#include "database/databaseworker.h"

#include <QCoreApplication>
#include <QDir>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QFile>
#include <QHash>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>

#include <iostream>
#include <functional>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

bool writeJson(const QString& path, const QJsonDocument& document) {
    QFile file(path);
    return file.open(QIODevice::WriteOnly | QIODevice::Text)
        && file.write(document.toJson(QJsonDocument::Indented)) > 0;
}

bool prepareRuntime(const QDir& root) {
    const QStringList directories = {
        QStringLiteral("data"), QStringLiteral("data/auto_saga"), QStringLiteral("data/database"),
        QStringLiteral("data/logs"), QStringLiteral("cards"),
    };
    for (const QString& directory : directories) {
        if (!root.mkpath(directory)) {
            return false;
        }
    }
    const QHash<QString, QJsonValue> files = {
        { QStringLiteral("data/route_forwarding.json"), QJsonObject{} },
        { QStringLiteral("data/preset.json"), QJsonObject{} },
        { QStringLiteral("data/worldbook.json"), QJsonObject{} },
        { QStringLiteral("data/worldbook_runtime_state.json"), QJsonObject{} },
        { QStringLiteral("data/creative_workshop_state.json"), QJsonObject{} },
        { QStringLiteral("data/persona.json"), QJsonObject{} },
        { QStringLiteral("data/user_profile.json"), QJsonObject{} },
        { QStringLiteral("data/auto_saga/state.json"), QJsonObject{} },
        { QStringLiteral("cards/template_single_role_card.json"), QJsonObject{} },
        { QStringLiteral("cards/template_multi_role_card.json"), QJsonObject{} },
        { QStringLiteral("data/conversations.json"), QJsonArray{} },
    };
    for (auto it = files.constBegin(); it != files.constEnd(); ++it) {
        const QJsonDocument document = it.value().isArray()
            ? QJsonDocument(it.value().toArray())
            : QJsonDocument(it.value().toObject());
        if (!writeJson(root.absoluteFilePath(it.key()), document)) {
            return false;
        }
    }
    QFile(root.absoluteFilePath(QStringLiteral("data/logs/fantareal.log"))).open(QIODevice::WriteOnly);
    return true;
}

int contentLength(const QByteArray& header) {
    for (QByteArray line : header.split('\n')) {
        line = line.trimmed();
        if (line.toLower().startsWith("content-length:")) {
            return line.mid(line.indexOf(':') + 1).trimmed().toInt();
        }
    }
    return 0;
}

QByteArray completion(const QString& content) {
    QJsonObject message;
    message.insert(QStringLiteral("content"), content);
    QJsonObject choice;
    choice.insert(QStringLiteral("message"), message);
    QJsonObject response;
    response.insert(QStringLiteral("choices"), QJsonArray{ choice });
    return QJsonDocument(response).toJson(QJsonDocument::Compact);
}

bool waitFor(const std::function<bool()>& predicate, int timeoutMs = 5000) {
    QElapsedTimer timer;
    timer.start();
    while (!predicate() && timer.elapsed() < timeoutMs) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 50);
    }
    return predicate();
}

int rowCount(const QString& databasePath, const QString& sql) {
    const QString connectionName = QStringLiteral("FantarealDatabaseWorkerChatCount_%1").arg(qHash(sql));
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
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }
    QDir root(tempDir.path());
    if (!prepareRuntime(root)) {
        return fail(QStringLiteral("failed to prepare runtime fixture")) ? 0 : 1;
    }

    QTcpServer server;
    if (!server.listen(QHostAddress::LocalHost, 0)) {
        return fail(QStringLiteral("failed to start fake provider")) ? 0 : 1;
    }
    int mainRequests = 0;
    int workerRequests = 0;
    QString workerPrompt;
    QStringList workerPrompts;
    bool delayNextWorkerResponse = false;
    bool queueTestMode = false;
    QPointer<QTcpSocket> delayedWorkerSocket;
    QByteArray delayedWorkerResponse;
    QObject::connect(&server, &QTcpServer::newConnection, [&]() {
        QTcpSocket* socket = server.nextPendingConnection();
        auto* buffer = new QByteArray;
        QObject::connect(socket, &QTcpSocket::readyRead, [&, socket, buffer]() {
            buffer->append(socket->readAll());
            const int headerEnd = buffer->indexOf("\r\n\r\n");
            if (headerEnd < 0) {
                return;
            }
            const int expected = contentLength(buffer->left(headerEnd));
            const QByteArray body = buffer->mid(headerEnd + 4);
            if (body.size() < expected) {
                return;
            }
            const QJsonObject request = QJsonDocument::fromJson(body.left(expected)).object();
            const QString model = request.value(QStringLiteral("model")).toString();
            QByteArray responseBody;
            if (model == QStringLiteral("worker-model")) {
                ++workerRequests;
                workerPrompt = request.value(QStringLiteral("messages")).toArray().at(1).toObject().value(QStringLiteral("content")).toString();
                workerPrompts.append(workerPrompt);
                QJsonObject display;
                display.insert(QStringLiteral("title"), QStringLiteral("本轮记录"));
                display.insert(QStringLiteral("summary"), QStringLiteral("角色状态已更新"));
                display.insert(QStringLiteral("characters"), QJsonArray{ QJsonObject{
                    { QStringLiteral("roleId"), QStringLiteral("main") },
                    { QStringLiteral("name"), QStringLiteral("测试角色") },
                    { QStringLiteral("emotion"), QStringLiteral("平静而专注") },
                    { QStringLiteral("posture"), QStringLiteral("端坐并看向用户") },
                    { QStringLiteral("metrics"), QJsonArray{ QJsonObject{
                          { QStringLiteral("key"), QStringLiteral("affection") },
                          { QStringLiteral("label"), QStringLiteral("好感度") },
                          { QStringLiteral("value"), 37 },
                          { QStringLiteral("maximum"), 100 },
                          { QStringLiteral("delta"), 0 },
                      } } },
                } });
                display.insert(QStringLiteral("relationships"), QJsonArray{ QJsonObject{
                    { QStringLiteral("pair"), QStringLiteral("测试角色-用户") },
                    { QStringLiteral("stage"), QStringLiteral("稳定") },
                    { QStringLiteral("change"), QStringLiteral("本轮关系保持稳定") },
                } });
                responseBody = completion(QString::fromUtf8(QJsonDocument(QJsonObject{
                    { QStringLiteral("updates"), QJsonObject{
                          { QStringLiteral("schemaVersion"), 1 },
                          { QStringLiteral("snapshot"), QJsonObject{
                                { QStringLiteral("scope"), QStringLiteral("current") },
                                { QStringLiteral("title"), QStringLiteral("当前状态") },
                                { QStringLiteral("payload"), QJsonObject{
                                      { QStringLiteral("location"), queueTestMode
                                              ? QStringLiteral("queue-runtime-marker")
                                              : QStringLiteral("咖啡馆") },
                                  } },
                            } },
                          { QStringLiteral("variables"), QJsonArray{} },
                          { QStringLiteral("relationships"), QJsonArray{ QJsonObject{
                                { QStringLiteral("pairKey"), QStringLiteral("测试角色→用户") },
                                { QStringLiteral("roleA"), QStringLiteral("测试角色") },
                                { QStringLiteral("roleB"), QStringLiteral("用户") },
                                { QStringLiteral("stage"), QStringLiteral("稳定") },
                                { QStringLiteral("attitude"), QStringLiteral("愿意继续交流") },
                                { QStringLiteral("summary"), QStringLiteral("双方保持稳定信任") },
                                { QStringLiteral("change"), QStringLiteral("本轮关系进一步稳定") },
                            } } },
                          { QStringLiteral("stages"), QJsonArray{} },
                          { QStringLiteral("ledger"), QJsonArray{ QJsonObject{
                                { QStringLiteral("entryType"), QStringLiteral("event") },
                                { QStringLiteral("content"), QStringLiteral("完成本轮对话") },
                            } } },
                      } },
                    { QStringLiteral("display"), display },
                }).toJson(QJsonDocument::Compact)));
            } else {
                ++mainRequests;
                responseBody = completion(QStringLiteral("这是完整的角色回复正文。"));
            }
            const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                + QByteArray::number(responseBody.size())
                + QByteArray("\r\nConnection: close\r\n\r\n") + responseBody;
            if (model == QStringLiteral("worker-model") && delayNextWorkerResponse) {
                delayNextWorkerResponse = false;
                delayedWorkerSocket = socket;
                delayedWorkerResponse = response;
                return;
            }
            socket->write(response);
            socket->disconnectFromHost();
        });
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() { delete buffer; });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
    });

    const QString baseUrl = QStringLiteral("http://127.0.0.1:%1/v1").arg(server.serverPort());
    QJsonObject settings;
    settings.insert(QStringLiteral("llm_base_url"), baseUrl);
    settings.insert(QStringLiteral("llm_api_key"), QStringLiteral("main-key"));
    settings.insert(QStringLiteral("llm_model"), QStringLiteral("chat-model"));
    settings.insert(QStringLiteral("reply_display_mode"), QStringLiteral("state_record"));
    settings.insert(QStringLiteral("output_splitting_enabled"), false);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/settings.json")), QJsonDocument(settings))) {
        return fail(QStringLiteral("failed to save chat settings")) ? 0 : 1;
    }

    QJsonObject stateJournal;
    stateJournal.insert(QStringLiteral("enabled"), true);
    stateJournal.insert(QStringLiteral("roles"), QJsonArray{ QJsonObject{
        { QStringLiteral("role_id"), QStringLiteral("main") },
        { QStringLiteral("role_name"), QStringLiteral("测试角色") },
        { QStringLiteral("enabled"), true },
        { QStringLiteral("mode"), QStringLiteral("full") },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("var_key"), QStringLiteral("affection") },
              { QStringLiteral("var_name"), QStringLiteral("好感度") },
              { QStringLiteral("default_value"), 37 },
              { QStringLiteral("max_value"), 100 },
          } } },
        { QStringLiteral("snapshotFields"), QJsonArray{ QJsonObject{
              { QStringLiteral("key"), QStringLiteral("emotion") },
              { QStringLiteral("label"), QStringLiteral("情绪") },
              { QStringLiteral("instruction"), QStringLiteral("记录可观察情绪") },
          } } },
    } });
    QJsonObject raw;
    raw.insert(QStringLiteral("name"), QStringLiteral("测试角色"));
    raw.insert(QStringLiteral("stateJournal"), stateJournal);
    QJsonObject card;
    card.insert(QStringLiteral("card_uid"), QStringLiteral("card-worker-test"));
    card.insert(QStringLiteral("raw"), raw);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(card))) {
        return fail(QStringLiteral("failed to save role card")) ? 0 : 1;
    }

    const QString historyConversationId = QStringLiteral("worker-history");
    QJsonArray history;
    for (const auto& item : {
             qMakePair(QStringLiteral("user"), QStringLiteral("更早用户")),
             qMakePair(QStringLiteral("assistant"), QStringLiteral("更早助手")),
             qMakePair(QStringLiteral("user"), QStringLiteral("中间用户")),
             qMakePair(QStringLiteral("assistant"), QStringLiteral("中间助手")),
             qMakePair(QStringLiteral("user"), QStringLiteral("最近用户")),
             qMakePair(QStringLiteral("assistant"), QStringLiteral("最近助手")),
         }) {
        history.append(QJsonObject{
            { QStringLiteral("role"), item.first },
            { QStringLiteral("content"), item.second },
            { QStringLiteral("message_id"), QStringLiteral("history-%1").arg(history.size() + 1) },
            { QStringLiteral("conversation_id"), historyConversationId },
        });
    }
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/conversations.json")), QJsonDocument(history))) {
        return fail(QStringLiteral("failed to save chat history fixture")) ? 0 : 1;
    }

    QJsonObject workerSettings;
    workerSettings.insert(QStringLiteral("enabled"), true);
    workerSettings.insert(QStringLiteral("auto_update"), true);
    workerSettings.insert(QStringLiteral("api_base_url"), baseUrl);
    workerSettings.insert(QStringLiteral("api_key"), QStringLiteral("worker-key"));
    workerSettings.insert(QStringLiteral("model"), QStringLiteral("worker-model"));
    workerSettings.insert(QStringLiteral("input_turn_count"), 2);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/database/worker_settings.json")), QJsonDocument(workerSettings))) {
        return fail(QStringLiteral("failed to save worker settings")) ? 0 : 1;
    }

    DatabaseService contextDatabase(root.absolutePath());
    DatabaseTurnRecord contextTurn;
    contextTurn.turnId = QStringLiteral("runtime-context-turn");
    contextTurn.cardUid = QStringLiteral("card-worker-test");
    contextTurn.conversationId = historyConversationId;
    contextTurn.messageId = QStringLiteral("runtime-context-message");
    contextTurn.contentHash = QString(64, QLatin1Char('c'));
    contextTurn.workerModel = QStringLiteral("worker-model");
    const DatabaseOperationResult contextPending = contextDatabase.createPendingTurn(contextTurn);
    if (!contextPending.ok) {
        return fail(QStringLiteral("failed to create runtime context turn: %1 / %2")
                        .arg(contextPending.code, contextPending.message)) ? 0 : 1;
    }
    DatabaseTurnResult contextResult;
    contextResult.display.turnId = contextTurn.turnId;
    contextResult.updates = QJsonObject{
        { QStringLiteral("schemaVersion"), 1 },
        { QStringLiteral("variables"), QJsonArray{ QJsonObject{
              { QStringLiteral("roleId"), QStringLiteral("main") },
              { QStringLiteral("key"), QStringLiteral("affection") },
              { QStringLiteral("label"), QStringLiteral("好感度") },
              { QStringLiteral("value"), 37 },
          } } },
        { QStringLiteral("stages"), QJsonArray{} },
        { QStringLiteral("ledger"), QJsonArray{} },
    };
    const DatabaseOperationResult contextSaved = contextDatabase.saveTurnResult(contextResult);
    if (!contextSaved.ok) {
        return fail(QStringLiteral("failed to seed runtime context: %1 / %2")
                        .arg(contextSaved.code, contextSaved.message)) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    int workersWhenChatFinished = -1;
    QObject::connect(&bridge, &FantarealBridge::chatGenerationFinished, [&](const QVariantMap&) {
        workersWhenChatFinished = workerRequests;
    });

    const QVariantMap start = bridge.startChatMessageWithReply(QStringLiteral("开始记录"));
    if (!start.value(QStringLiteral("ok")).toBool() || !start.value(QStringLiteral("started")).toBool()) {
        return fail(QStringLiteral("chat request should start")) ? 0 : 1;
    }
    if (!waitFor([&]() { return !bridge.chatGenerating() && mainRequests == 1; })) {
        return fail(QStringLiteral("main chat should finish")) ? 0 : 1;
    }
    if (workersWhenChatFinished != 0) {
        return fail(QStringLiteral("DatabaseWorker must start after chatGenerationFinished")) ? 0 : 1;
    }
    if (bridge.chatMessages().size() != 8
        || bridge.chatMessages().last().toMap().value(QStringLiteral("content")).toString() != QStringLiteral("这是完整的角色回复正文。")) {
        return fail(QStringLiteral("state record mode should preserve one complete assistant bubble")) ? 0 : 1;
    }
    if (!waitFor([&]() {
            const QVariantList messages = bridge.chatMessages();
            return workerRequests == 1 && messages.size() == 8
                && messages.last().toMap().value(QStringLiteral("stateRecord")).toMap().value(QStringLiteral("status")).toString() == QStringLiteral("ready");
    })) {
        return fail(QStringLiteral("worker result should attach a ready state record to the assistant message")) ? 0 : 1;
    }
    const QVariantMap stateRecord = bridge.chatMessages().last().toMap().value(QStringLiteral("stateRecord")).toMap();
    if (stateRecord.value(QStringLiteral("titleCard")).toMap().value(QStringLiteral("title")).toString() != QStringLiteral("本轮记录")) {
        return fail(QStringLiteral("state record title should use normalized worker display")) ? 0 : 1;
    }
    const QVariantMap recordCard = stateRecord.value(QStringLiteral("recordCard")).toMap();
    const QVariantList characters = recordCard.value(QStringLiteral("characters")).toList();
    const QVariantMap character = characters.isEmpty() ? QVariantMap{} : characters.first().toMap();
    const QVariantList fields = character.value(QStringLiteral("fields")).toList();
    if (characters.size() != 1 || fields.size() < 2
        || fields.first().toMap().value(QStringLiteral("label")).toString() != QStringLiteral("情绪")
        || character.value(QStringLiteral("metrics")).toList().size() != 1
        || recordCard.value(QStringLiteral("relationships")).toList().size() != 1) {
        return fail(QStringLiteral("state record display should preserve readable character fields, metrics, and relationships")) ? 0 : 1;
    }
    if (!workerPrompt.contains(QStringLiteral("\"database\"")) || workerPrompt.contains(QStringLiteral("stateJournal"))
        || !workerPrompt.contains(QStringLiteral("runtime_context"))
        || !workerPrompt.contains(QStringLiteral("relationships 只记录"))
        || !workerPrompt.contains(QStringLiteral("fields 每项为"))
        || !workerPrompt.contains(QStringLiteral("\"affection\""))
        || !workerPrompt.contains(QStringLiteral("最近用户")) || !workerPrompt.contains(QStringLiteral("最近助手"))
        || workerPrompt.contains(QStringLiteral("更早用户")) || workerPrompt.contains(QStringLiteral("更早助手"))) {
        return fail(QStringLiteral("DatabaseWorker prompt should contain bounded runtime state and recent history")) ? 0 : 1;
    }
    const DatabaseService database(root.absolutePath());
    if (rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_state_snapshots")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_state")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_history")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_plot_ledger")) != 1) {
        return fail(QStringLiteral("worker output should write snapshots, durable relationships, and ledger entries with the display result")) ? 0 : 1;
    }

    const QString supersededMessageId = bridge.chatMessages().last().toMap().value(QStringLiteral("message_id")).toString();
    const QVariantMap regenerate = bridge.startRegenerateLastChatReply();
    if (!regenerate.value(QStringLiteral("ok")).toBool() || !regenerate.value(QStringLiteral("started")).toBool()) {
        return fail(QStringLiteral("regenerating a reply with a state record should start")) ? 0 : 1;
    }
    if (!waitFor([&]() {
            return !bridge.chatGenerating() && mainRequests == 2 && workerRequests == 2
                && bridge.chatMessages().size() == 8
                && bridge.chatMessages().last().toMap().value(QStringLiteral("stateRecord")).toMap().value(QStringLiteral("status")).toString()
                    == QStringLiteral("ready");
    })) {
        return fail(QStringLiteral("regenerated reply should produce a new ready state record")) ? 0 : 1;
    }
    const std::optional<DatabaseTurnView> supersededTurn = database.turnByMessageId(QStringLiteral("card-worker-test"), supersededMessageId);
    if (!supersededTurn || supersededTurn->turn.status != DatabaseTurnStatus::Superseded) {
        return fail(QStringLiteral("regenerating a reply must supersede the replaced state record")) ? 0 : 1;
    }
    if (rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_state_snapshots")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_state")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_relationship_history")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_plot_ledger")) != 1
        || rowCount(database.paths().databasePath(), QStringLiteral("SELECT COUNT(*) FROM database_turn_effects WHERE reverted_at != ''")) != 4) {
        return fail(QStringLiteral("regenerating a reply should roll back old runtime updates before saving the new result")) ? 0 : 1;
    }

    workerSettings.insert(QStringLiteral("auto_update"), false);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/database/worker_settings.json")), QJsonDocument(workerSettings))) {
        return fail(QStringLiteral("failed to disable automatic worker updates")) ? 0 : 1;
    }
    const QVariantMap manualChat = bridge.startChatMessageWithReply(QStringLiteral("改为手动生成状态记录"));
    if (!manualChat.value(QStringLiteral("ok")).toBool() || !manualChat.value(QStringLiteral("started")).toBool()) {
        return fail(QStringLiteral("manual worker chat should start")) ? 0 : 1;
    }
    if (!waitFor([&]() { return !bridge.chatGenerating() && mainRequests == 3; })) {
        return fail(QStringLiteral("manual worker chat should finish its main reply")) ? 0 : 1;
    }
    if (workerRequests != 2) {
        return fail(QStringLiteral("automatic worker should remain idle when auto_update is disabled")) ? 0 : 1;
    }
    const QVariantMap manualGeneration = bridge.generateLatestDatabaseTurn();
    if (!manualGeneration.value(QStringLiteral("ok")).toBool() || !manualGeneration.value(QStringLiteral("started")).toBool()) {
        return fail(QStringLiteral("manual worker generation should start for the latest assistant message")) ? 0 : 1;
    }
    if (!waitFor([&]() {
            const QVariantList messages = bridge.chatMessages();
            return workerRequests == 3 && !messages.isEmpty()
                && messages.last().toMap().value(QStringLiteral("stateRecord")).toMap().value(QStringLiteral("status")).toString()
                    == QStringLiteral("ready");
        })) {
        return fail(QStringLiteral("manual worker generation should create a ready state record")) ? 0 : 1;
    }
    const QVariantMap repeatedManualGeneration = bridge.generateLatestDatabaseTurn();
    if (!repeatedManualGeneration.value(QStringLiteral("ok")).toBool()
        || repeatedManualGeneration.value(QStringLiteral("started")).toBool()
        || workerRequests != 3) {
        return fail(QStringLiteral("manual worker generation should keep a ready state record idempotent")) ? 0 : 1;
    }

    const int queueWorkerBaseline = workerRequests;
    const QString queueCardUid = QStringLiteral("queue-card");
    DatabaseTurnRecord queueFirstTurn;
    queueFirstTurn.turnId = QStringLiteral("queue-turn-1");
    queueFirstTurn.cardUid = queueCardUid;
    queueFirstTurn.conversationId = QStringLiteral("queue-conversation");
    queueFirstTurn.messageId = QStringLiteral("queue-message-1");
    queueFirstTurn.turnIndex = 1;
    queueFirstTurn.contentHash = QString(64, QLatin1Char('f'));
    queueFirstTurn.workerModel = QStringLiteral("worker-model");
    DatabaseTurnRecord queueSecondTurn = queueFirstTurn;
    queueSecondTurn.turnId = QStringLiteral("queue-turn-2");
    queueSecondTurn.messageId = QStringLiteral("queue-message-2");
    queueSecondTurn.turnIndex = 2;
    queueSecondTurn.contentHash = QString(64, QLatin1Char('g'));
    if (!database.createPendingTurn(queueFirstTurn).ok || !database.createPendingTurn(queueSecondTurn).ok) {
        return fail(QStringLiteral("failed to create queued worker turns")) ? 0 : 1;
    }

    DatabaseWorkerRequest queueFirstRequest;
    queueFirstRequest.turn = queueFirstTurn;
    queueFirstRequest.assistantContent = QStringLiteral("queue assistant one");
    queueFirstRequest.roleName = QStringLiteral("queue role");
    DatabaseWorkerRequest queueSecondRequest = queueFirstRequest;
    queueSecondRequest.turn = queueSecondTurn;
    queueSecondRequest.assistantContent = QStringLiteral("queue assistant two");

    DatabaseWorker queueWorker(root.absolutePath());
    int queueFinished = 0;
    QObject::connect(&queueWorker, &DatabaseWorker::turnFinished,
        [&](const QString&, const DatabaseOperationResult&) {
            ++queueFinished;
    });
    queueTestMode = true;
    delayNextWorkerResponse = true;
    queueWorker.start(queueFirstRequest);
    queueWorker.start(queueSecondRequest);
    if (!waitFor([&]() {
            return workerRequests == queueWorkerBaseline + 1 && !delayedWorkerSocket.isNull();
        })) {
        return fail(QStringLiteral("first queued worker request should reach the provider")) ? 0 : 1;
    }
    QElapsedTimer serializationWindow;
    serializationWindow.start();
    while (serializationWindow.elapsed() < 250) {
        QCoreApplication::processEvents(QEventLoop::AllEvents, 25);
    }
    if (workerRequests != queueWorkerBaseline + 1 || !queueWorker.isActive(queueSecondTurn.turnId)) {
        return fail(QStringLiteral("second worker request for the same card must remain queued")) ? 0 : 1;
    }

    delayedWorkerSocket->write(delayedWorkerResponse);
    delayedWorkerSocket->disconnectFromHost();
    if (!waitFor([&]() {
            return queueFinished == 2 && workerRequests == queueWorkerBaseline + 2;
        })) {
        return fail(QStringLiteral("queued worker requests should finish in order")) ? 0 : 1;
    }
    if (workerPrompts.isEmpty() || !workerPrompts.last().contains(QStringLiteral("queue-runtime-marker"))
        || database.turnById(queueFirstTurn.turnId)->turn.status != DatabaseTurnStatus::Ready
        || database.turnById(queueSecondTurn.turnId)->turn.status != DatabaseTurnStatus::Ready) {
        return fail(QStringLiteral("second worker dispatch should include the first result in runtime context")) ? 0 : 1;
    }

    const int retryWorkerBaseline = workerRequests;
    DatabaseTurnRecord retryWorkerTurn;
    retryWorkerTurn.turnId = QStringLiteral("worker-retry-turn");
    retryWorkerTurn.cardUid = QStringLiteral("worker-retry-card");
    retryWorkerTurn.conversationId = QStringLiteral("worker-retry-conversation");
    retryWorkerTurn.messageId = QStringLiteral("worker-retry-message");
    retryWorkerTurn.turnIndex = 1;
    retryWorkerTurn.contentHash = QString(64, QLatin1Char('j'));
    retryWorkerTurn.workerModel = QStringLiteral("worker-model");
    if (!database.createPendingTurn(retryWorkerTurn).ok
        || !database.markTurnError(retryWorkerTurn.turnId, QStringLiteral("provider_timeout"),
            QStringLiteral("first attempt failed"), retryWorkerTurn.attemptCount).ok
        || !database.retryTurn(retryWorkerTurn.turnId).ok) {
        return fail(QStringLiteral("failed to prepare worker retry turn")) ? 0 : 1;
    }

    DatabaseWorkerRequest retryWorkerRequest;
    retryWorkerRequest.turn = retryWorkerTurn;
    retryWorkerRequest.assistantContent = QStringLiteral("retry assistant content");
    retryWorkerRequest.roleName = QStringLiteral("retry role");
    DatabaseWorker retryWorker(root.absolutePath());
    int retryFinished = 0;
    DatabaseOperationResult retryResult;
    QObject::connect(&retryWorker, &DatabaseWorker::turnFinished,
        [&](const QString&, const DatabaseOperationResult& result) {
            ++retryFinished;
            retryResult = result;
        });
    queueTestMode = false;
    retryWorker.start(retryWorkerRequest);
    if (!waitFor([&]() {
            return retryFinished == 1 && workerRequests == retryWorkerBaseline + 1;
        })) {
        return fail(QStringLiteral("retried worker request should finish")) ? 0 : 1;
    }
    const std::optional<DatabaseTurnView> retriedWorkerView = database.turnById(retryWorkerTurn.turnId);
    if (!retryResult.ok || !retriedWorkerView
        || retriedWorkerView->turn.status != DatabaseTurnStatus::Ready
        || retriedWorkerView->turn.attemptCount != 1) {
        return fail(QStringLiteral("worker dispatch must refresh the current retry attempt before saving")) ? 0 : 1;
    }

    const int cancelWorkerBaseline = workerRequests;
    const QString cancelCardUid = QStringLiteral("cancel-card");
    DatabaseTurnRecord cancelFirstTurn = queueFirstTurn;
    cancelFirstTurn.turnId = QStringLiteral("cancel-turn-1");
    cancelFirstTurn.cardUid = cancelCardUid;
    cancelFirstTurn.conversationId = QStringLiteral("cancel-conversation");
    cancelFirstTurn.messageId = QStringLiteral("cancel-message-1");
    cancelFirstTurn.contentHash = QString(64, QLatin1Char('h'));
    DatabaseTurnRecord cancelSecondTurn = cancelFirstTurn;
    cancelSecondTurn.turnId = QStringLiteral("cancel-turn-2");
    cancelSecondTurn.messageId = QStringLiteral("cancel-message-2");
    cancelSecondTurn.turnIndex = 2;
    cancelSecondTurn.contentHash = QString(64, QLatin1Char('i'));
    if (!database.createPendingTurn(cancelFirstTurn).ok || !database.createPendingTurn(cancelSecondTurn).ok) {
        return fail(QStringLiteral("failed to create cancel worker turns")) ? 0 : 1;
    }

    DatabaseWorkerRequest cancelFirstRequest = queueFirstRequest;
    cancelFirstRequest.turn = cancelFirstTurn;
    DatabaseWorkerRequest cancelSecondRequest = cancelFirstRequest;
    cancelSecondRequest.turn = cancelSecondTurn;
    DatabaseWorker cancelWorker(root.absolutePath());
    int cancelFinished = 0;
    DatabaseOperationResult cancelResult;
    QObject::connect(&cancelWorker, &DatabaseWorker::turnFinished,
        [&](const QString&, const DatabaseOperationResult& result) {
            ++cancelFinished;
            cancelResult = result;
        });
    queueTestMode = false;
    delayNextWorkerResponse = true;
    delayedWorkerSocket.clear();
    delayedWorkerResponse.clear();
    cancelWorker.start(cancelFirstRequest);
    cancelWorker.start(cancelSecondRequest);
    if (!waitFor([&]() {
            return workerRequests == cancelWorkerBaseline + 1 && !delayedWorkerSocket.isNull();
        })) {
        return fail(QStringLiteral("active worker request should reach the provider before cancellation")) ? 0 : 1;
    }
    const DatabaseOperationResult supersededCancelTurns = database.markMessagesSuperseded(
        cancelCardUid, QStringList{cancelFirstTurn.messageId, cancelSecondTurn.messageId});
    if (!supersededCancelTurns.ok) {
        return fail(QStringLiteral("failed to supersede cancel worker turns")) ? 0 : 1;
    }
    cancelWorker.cancel(cancelFirstTurn.turnId);
    cancelWorker.cancel(cancelSecondTurn.turnId);
    if (!waitFor([&]() {
            return cancelFinished == 1
                && !cancelWorker.isActive(cancelFirstTurn.turnId)
                && !cancelWorker.isActive(cancelSecondTurn.turnId);
        })) {
        return fail(QStringLiteral("active and queued worker cancellation should settle")) ? 0 : 1;
    }
    if (!cancelResult.ok || !cancelResult.code.isEmpty()
        || workerRequests != cancelWorkerBaseline + 1
        || database.turnById(cancelFirstTurn.turnId)->turn.status != DatabaseTurnStatus::Superseded
        || database.turnById(cancelSecondTurn.turnId)->turn.status != DatabaseTurnStatus::Superseded) {
        return fail(QStringLiteral("cancelled worker requests must not become provider errors or dispatch queued work")) ? 0 : 1;
    }
    return 0;
}
