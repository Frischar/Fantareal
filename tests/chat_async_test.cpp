#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
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
        finishedResult.insert(QStringLiteral("message"), QStringLiteral("timed out waiting for chatGenerationFinished"));
        loop.quit();
    });

    timeout.start(timeoutMs);
    loop.exec();
    return finishedResult;
}

bool waitForPreview(FantarealBridge* bridge, const QString& expected, int timeoutMs = 1500) {
    if (bridge->chatStreamingPreview().contains(expected)) {
        return true;
    }

    QEventLoop loop;
    QTimer timeout;
    timeout.setSingleShot(true);
    bool found = false;

    QObject::connect(bridge, &FantarealBridge::chatGenerationChanged, &loop, [&]() {
        if (bridge->chatStreamingPreview().contains(expected)) {
            found = true;
            loop.quit();
        }
    });
    QObject::connect(&timeout, &QTimer::timeout, &loop, &QEventLoop::quit);

    timeout.start(timeoutMs);
    loop.exec();
    return found;
}

template <typename Predicate>
bool waitForCondition(Predicate predicate, int timeoutMs = 1500) {
    if (predicate()) {
        return true;
    }

    QEventLoop loop;
    QTimer poll;
    QTimer timeout;
    poll.setInterval(10);
    timeout.setSingleShot(true);
    bool found = false;

    QObject::connect(&poll, &QTimer::timeout, &loop, [&]() {
        if (predicate()) {
            found = true;
            loop.quit();
        }
    });
    QObject::connect(&timeout, &QTimer::timeout, &loop, &QEventLoop::quit);

    poll.start();
    timeout.start(timeoutMs);
    loop.exec();
    return found;
}

void spinEvents(int durationMs) {
    QEventLoop loop;
    QTimer::singleShot(durationMs, &loop, &QEventLoop::quit);
    loop.exec();
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
    int requestCount = 0;
    int mainRequestCount = 0;
    int splitterRequestCount = 0;
    QByteArray firstRequestBody;
    QList<QPointer<QTcpSocket>> heldSockets;
    if (!server.listen(QHostAddress::LocalHost, 0)) {
        return fail(QStringLiteral("failed to start local fake chat server")) ? 0 : 1;
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

            const QByteArray requestBody = body.left(expectedLength);
            const bool splitterRequest = QString::fromUtf8(requestBody).contains(QStringLiteral("聊天输出后处理器"));
            ++requestCount;
            if (splitterRequest) {
                ++splitterRequestCount;
                const QByteArray responseBody = QByteArray(R"({"choices":[{"message":{"content":"[\"async assistant reply\"]"}}]})");
                const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                    + QByteArray::number(responseBody.size())
                    + QByteArray("\r\nConnection: close\r\n\r\n")
                    + responseBody;
                socket->write(response);
                socket->disconnectFromHost();
                return;
            }
            ++mainRequestCount;
            if (mainRequestCount == 1) {
                firstRequestBody = requestBody;
                socket->write("HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n");
                socket->write("data: {\"choices\":[{\"delta\":{\"content\":\"async \"}}]}\n\n");
                socket->flush();
                QTimer::singleShot(200, socket, [socket]() {
                    socket->write("data: {\"choices\":[{\"delta\":{\"content\":\"assistant reply\"}}]}\n\n");
                    socket->write("data: [DONE]\n\n");
                    socket->flush();
                    socket->disconnectFromHost();
                });
            } else {
                heldSockets.append(socket);
            }
        });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() {
            delete buffer;
        });
    });

    QJsonObject settings;
    settings.insert(QStringLiteral("temperature"), 0.3);
    settings.insert(QStringLiteral("history_limit"), 8);
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
    provider.insert(QStringLiteral("model"), QStringLiteral("route-model"));
    provider.insert(QStringLiteral("keys"), QJsonArray{ QStringLiteral("route-key") });

    QJsonObject routes;
    routes.insert(QStringLiteral("enabled"), true);
    routes.insert(QStringLiteral("providers"), QJsonArray{ provider });
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/route_forwarding.json")), QJsonDocument(routes))) {
        return fail(QStringLiteral("failed to write route fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;

    const QString conversationPath = root.absoluteFilePath(QStringLiteral("data/conversations.json"));
    const QVariantMap startResult = bridge.startChatMessageWithReply(QStringLiteral("async hello"));
    if (!startResult.value(QStringLiteral("ok")).toBool()
        || !startResult.value(QStringLiteral("started")).toBool()
        || !bridge.chatGenerating()) {
        return fail(QStringLiteral("async chat generation should start without blocking")) ? 0 : 1;
    }
    const QJsonArray afterStart = readJsonArray(conversationPath);
    if (afterStart.size() != 1
        || afterStart.first().toObject().value(QStringLiteral("role")).toString() != QStringLiteral("user")
        || afterStart.first().toObject().value(QStringLiteral("content")).toString() != QStringLiteral("async hello")
        || bridge.chatMessages().size() != 1) {
        return fail(QStringLiteral("async generation should write and expose the user message immediately")) ? 0 : 1;
    }
    if (!waitForCondition([&]() { return mainRequestCount == 1; })) {
        return fail(QStringLiteral("async chat generation should reach the streaming response")) ? 0 : 1;
    }
    if (!waitForPreview(&bridge, QStringLiteral("async "))) {
        return fail(QStringLiteral("streaming preview should show partial text while output splitting is enabled")) ? 0 : 1;
    }
    if (!QString::fromUtf8(firstRequestBody).contains(QStringLiteral("\"stream\":true"))) {
        return fail(QStringLiteral("async chat generation should request streaming responses")) ? 0 : 1;
    }

    const QVariantMap finishResult = waitForGeneration(&bridge);
    if (!finishResult.value(QStringLiteral("ok")).toBool() || bridge.chatGenerating()) {
        return fail(QStringLiteral("async chat generation should finish successfully")) ? 0 : 1;
    }
    if (!bridge.chatStreamingPreview().isEmpty()) {
        return fail(QStringLiteral("streaming preview should clear after generation finishes")) ? 0 : 1;
    }
    if (mainRequestCount != 1 || splitterRequestCount != 1 || requestCount != 2) {
        return fail(QStringLiteral("async generation should run one main request and one output-splitting request")) ? 0 : 1;
    }

    const QJsonArray saved = readJsonArray(conversationPath);
    if (saved.size() != 2
        || saved.at(0).toObject().value(QStringLiteral("role")).toString() != QStringLiteral("user")
        || saved.at(1).toObject().value(QStringLiteral("content")).toString() != QStringLiteral("async assistant reply")
        || bridge.chatMessages().size() != 2) {
        return fail(QStringLiteral("async generation should write user plus assistant and refresh chatMessages")) ? 0 : 1;
    }
    if (saved.at(1).toObject().value(QStringLiteral("display_parts")).toArray().size() != 1
        || saved.at(1).toObject().value(QStringLiteral("display_parts")).toArray().first().toString() != QStringLiteral("async assistant reply")) {
        return fail(QStringLiteral("async assistant message should store output-split display parts")) ? 0 : 1;
    }
    if (finishResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(finishResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("async generation should create a backup before writing")) ? 0 : 1;
    }

    const QVariantMap retryStart = bridge.startRegenerateLastChatReply();
    if (!retryStart.value(QStringLiteral("ok")).toBool()
        || !retryStart.value(QStringLiteral("started")).toBool()
        || !bridge.chatGenerating()) {
        return fail(QStringLiteral("async retry generation should start")) ? 0 : 1;
    }
    const QJsonArray afterRetryStart = readJsonArray(conversationPath);
    if (afterRetryStart.size() != 1
        || afterRetryStart.first().toObject().value(QStringLiteral("role")).toString() != QStringLiteral("user")
        || afterRetryStart.first().toObject().value(QStringLiteral("content")).toString() != QStringLiteral("async hello")
        || bridge.chatMessages().size() != 1) {
        return fail(QStringLiteral("async retry should delete the latest assistant reply before the new reply returns")) ? 0 : 1;
    }

    QVariantMap stopResult;
    QTimer::singleShot(50, [&]() {
        stopResult = bridge.stopChatGeneration();
    });
    const QVariantMap stoppedResult = waitForGeneration(&bridge, 5000);
    if (!stopResult.value(QStringLiteral("ok")).toBool()
        || stoppedResult.value(QStringLiteral("ok")).toBool()
        || !stoppedResult.value(QStringLiteral("message")).toString().contains(QStringLiteral("停止"))
        || bridge.chatGenerating()) {
        return fail(QStringLiteral("stopChatGeneration should abort the active request and emit a failed finish")) ? 0 : 1;
    }

    const QJsonArray afterStop = readJsonArray(conversationPath);
    if (afterStop.size() != 1
        || afterStop.at(0).toObject().value(QStringLiteral("content")).toString() != saved.at(0).toObject().value(QStringLiteral("content")).toString()
        || bridge.chatMessages().size() != 1) {
        return fail(QStringLiteral("stopped retry should keep the deleted-assistant context and not write a partial reply")) ? 0 : 1;
    }

    for (const QPointer<QTcpSocket>& socket : heldSockets) {
        if (socket) {
            socket->disconnectFromHost();
        }
    }

    return 0;
}
