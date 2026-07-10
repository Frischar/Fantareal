#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QEventLoop>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
#include <QTimer>
#include <QVariantMap>

#include <iostream>

namespace {
bool fail(const QString& message) {
    std::cerr << message.toStdString() << '\n';
    return false;
}

bool writeJson(const QString& path, const QJsonDocument& document) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    return file.write(document.toJson(QJsonDocument::Indented)) > 0;
}

QJsonArray readJsonArray(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).array();
}

bool makeRequiredFiles(const QDir& root) {
    const QStringList dirs = {
        QStringLiteral("data"),
        QStringLiteral("data/auto_saga"),
        QStringLiteral("data/database"),
        QStringLiteral("data/logs"),
        QStringLiteral("cards"),
    };
    for (const QString& dir : dirs) {
        if (!root.mkpath(dir)) {
            return false;
        }
    }

    const QHash<QString, QJsonValue> jsonFiles = {
        { QStringLiteral("data/settings.json"), QJsonObject{} },
        { QStringLiteral("data/route_forwarding.json"), QJsonObject{} },
        { QStringLiteral("data/current_role_card.json"), QJsonObject{} },
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

    for (auto it = jsonFiles.constBegin(); it != jsonFiles.constEnd(); ++it) {
        const QJsonDocument document = it.value().isArray()
            ? QJsonDocument(it.value().toArray())
            : QJsonDocument(it.value().toObject());
        if (!writeJson(root.absoluteFilePath(it.key()), document)) {
            return false;
        }
    }

    QFile(root.absoluteFilePath(QStringLiteral("data/database/database.db"))).open(QIODevice::WriteOnly);
    QFile(root.absoluteFilePath(QStringLiteral("data/logs/fantareal.log"))).open(QIODevice::WriteOnly);
    return true;
}

int contentLengthFromHeader(const QByteArray& header) {
    const QList<QByteArray> lines = header.split('\n');
    for (QByteArray line : lines) {
        line = line.trimmed();
        if (line.toLower().startsWith("content-length:")) {
            return line.mid(line.indexOf(':') + 1).trimmed().toInt();
        }
    }
    return 0;
}

QByteArray chatCompletionResponse(const QString& content) {
    QJsonObject message;
    message.insert(QStringLiteral("content"), content);
    QJsonObject choice;
    choice.insert(QStringLiteral("message"), message);
    QJsonObject root;
    root.insert(QStringLiteral("choices"), QJsonArray{ choice });
    return QJsonDocument(root).toJson(QJsonDocument::Compact);
}

QVariantMap waitForGeneration(FantarealBridge* bridge, int timeoutMs = 3000) {
    QEventLoop loop;
    QTimer timeout;
    timeout.setSingleShot(true);
    QVariantMap finishedResult;

    QObject::connect(bridge, &FantarealBridge::chatGenerationFinished, &loop, [&](const QVariantMap& result) {
        finishedResult = result;
        loop.quit();
    });
    QObject::connect(&timeout, &QTimer::timeout, &loop, [&]() {
        finishedResult.insert(QStringLiteral("ok"), false);
        finishedResult.insert(QStringLiteral("message"), QStringLiteral("timed out waiting for endChatConversation"));
        loop.quit();
    });

    timeout.start(timeoutMs);
    loop.exec();
    return finishedResult;
}
}

int main(int argc, char* argv[]) {
    QCoreApplication app(argc, argv);
    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        return fail(QStringLiteral("failed to create temporary directory")) ? 0 : 1;
    }

    QDir root(tempDir.path());
    if (!makeRequiredFiles(root)) {
        return fail(QStringLiteral("failed to create temporary Fantareal fixture")) ? 0 : 1;
    }

    QTcpServer server;
    QByteArray capturedRequestBody;
    int requestCount = 0;
    if (!server.listen(QHostAddress::LocalHost, 0)) {
        return fail(QStringLiteral("failed to start local fake memory server")) ? 0 : 1;
    }

    QObject::connect(&server, &QTcpServer::newConnection, [&]() {
        QTcpSocket* socket = server.nextPendingConnection();
        QByteArray* buffer = new QByteArray;
        QObject::connect(socket, &QTcpSocket::readyRead, [&, socket, buffer]() {
            buffer->append(socket->readAll());
            const int split = buffer->indexOf("\r\n\r\n");
            if (split < 0) {
                return;
            }
            const QByteArray header = buffer->left(split);
            const int expectedLength = contentLengthFromHeader(header);
            const QByteArray body = buffer->mid(split + 4);
            if (body.size() < expectedLength) {
                return;
            }

            capturedRequestBody = body.left(expectedLength);
            ++requestCount;
            const QString memoryJson = QStringLiteral(
                R"({"title":"蓝色仪式","content":"用户和 Astra 约定以后每次跃迁前都要复查安全清单，并把这称为蓝色仪式。","tags":["对话总结","Astra","安全清单"],"notes":"由结束对话流程生成。"})");
            const QByteArray responseBody = chatCompletionResponse(memoryJson);
            const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                + QByteArray::number(responseBody.size())
                + QByteArray("\r\nConnection: close\r\n\r\n")
                + responseBody;
            socket->write(response);
            socket->flush();
            socket->disconnectFromHost();
        });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() {
            delete buffer;
        });
    });

    QJsonObject settings;
    settings.insert(QStringLiteral("temperature"), 0.2);
    settings.insert(QStringLiteral("history_limit"), 10);
    settings.insert(QStringLiteral("request_timeout"), 10);
    settings.insert(QStringLiteral("demo_mode"), false);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/settings.json")), QJsonDocument(settings))) {
        return fail(QStringLiteral("failed to write settings fixture")) ? 0 : 1;
    }

    QJsonObject provider;
    provider.insert(QStringLiteral("id"), QStringLiteral("local"));
    provider.insert(QStringLiteral("enabled"), true);
    provider.insert(QStringLiteral("priority"), 1);
    provider.insert(QStringLiteral("base_url"), QStringLiteral("http://127.0.0.1:%1/v1").arg(server.serverPort()));
    provider.insert(QStringLiteral("model"), QStringLiteral("memory-model"));
    provider.insert(QStringLiteral("keys"), QJsonArray{ QStringLiteral("route-key") });

    QJsonObject routes;
    routes.insert(QStringLiteral("enabled"), true);
    routes.insert(QStringLiteral("providers"), QJsonArray{ provider });
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/route_forwarding.json")), QJsonDocument(routes))) {
        return fail(QStringLiteral("failed to write route fixture")) ? 0 : 1;
    }

    QJsonObject rawCard;
    rawCard.insert(QStringLiteral("name"), QStringLiteral("Astra"));
    QJsonObject currentCard;
    currentCard.insert(QStringLiteral("card_uid"), QStringLiteral("card-end"));
    currentCard.insert(QStringLiteral("raw"), rawCard);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(currentCard))) {
        return fail(QStringLiteral("failed to write current role card")) ? 0 : 1;
    }

    QJsonObject userMessage;
    userMessage.insert(QStringLiteral("role"), QStringLiteral("user"));
    userMessage.insert(QStringLiteral("content"), QStringLiteral("以后每次跃迁前都复查安全清单。"));
    QJsonObject assistantMessage;
    assistantMessage.insert(QStringLiteral("role"), QStringLiteral("assistant"));
    assistantMessage.insert(QStringLiteral("content"), QStringLiteral("Astra 点头，把这称为蓝色仪式。"));
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/conversations.json")), QJsonDocument(QJsonArray{ userMessage, assistantMessage }))) {
        return fail(QStringLiteral("failed to write conversation fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;

    const QVariantMap result = bridge.endChatConversation();
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("endChatConversation failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (!result.value(QStringLiteral("started")).toBool() || !bridge.chatGenerating()) {
        return fail(QStringLiteral("endChatConversation should start async memory organization")) ? 0 : 1;
    }
    const QJsonArray withStatus = readJsonArray(root.absoluteFilePath(QStringLiteral("data/conversations.json")));
    if (withStatus.size() != 3
        || withStatus.last().toObject().value(QStringLiteral("role")).toString() != QStringLiteral("assistant")
        || withStatus.last().toObject().value(QStringLiteral("content")).toString() != QStringLiteral("正在整理回忆中......")
        || !withStatus.last().toObject().value(QStringLiteral("transient_status")).toBool()
        || bridge.chatMessages().size() != 3) {
        return fail(QStringLiteral("endChatConversation should immediately append an assistant memory-organizing bubble")) ? 0 : 1;
    }
    const QVariantMap statusMessage = bridge.chatMessages().last().toMap();
    const QVariantList statusParts = statusMessage.value(QStringLiteral("parts")).toList();
    if (statusParts.size() != 1
        || statusParts.first().toString() != QStringLiteral("正在整理回忆中......")
        || !statusMessage.value(QStringLiteral("isTransientStatus")).toBool()) {
        return fail(QStringLiteral("memory-organizing status should stay as one transient bubble")) ? 0 : 1;
    }

    const QVariantMap finishResult = waitForGeneration(&bridge);
    if (!finishResult.value(QStringLiteral("ok")).toBool() || bridge.chatGenerating()) {
        return fail(QStringLiteral("endChatConversation should finish successfully: %1").arg(finishResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (requestCount != 1
        || !QString::fromUtf8(capturedRequestBody).contains(QStringLiteral("长期记忆整理器"))
        || !QString::fromUtf8(capturedRequestBody).contains(QStringLiteral("蓝色仪式"))) {
        return fail(QStringLiteral("endChatConversation should summarize the conversation through the model prompt")) ? 0 : 1;
    }
    if (finishResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(finishResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("conversation backup should be created before clearing context")) ? 0 : 1;
    }

    const QJsonArray clearedConversations = readJsonArray(root.absoluteFilePath(QStringLiteral("data/conversations.json")));
    if (!clearedConversations.isEmpty() || !bridge.chatMessages().isEmpty()) {
        return fail(QStringLiteral("endChatConversation should clear conversations and refresh chatMessages")) ? 0 : 1;
    }

    const QString memoriesPath = root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-end/memories.json"));
    const QJsonArray memories = readJsonArray(memoriesPath);
    if (memories.size() != 1
        || memories.first().toObject().value(QStringLiteral("title")).toString() != QStringLiteral("蓝色仪式")
        || !memories.first().toObject().value(QStringLiteral("content")).toString().contains(QStringLiteral("安全清单"))
        || memories.first().toObject().value(QStringLiteral("memory_status")).toString() != QStringLiteral("active")) {
        return fail(QStringLiteral("endChatConversation should append one active long-term memory entry")) ? 0 : 1;
    }
    if (bridge.memoryDrafts().size() != 1) {
        return fail(QStringLiteral("endChatConversation should refresh memoryDrafts")) ? 0 : 1;
    }

    return 0;
}
