#include "fantarealbridge.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QHash>
#include <QHostAddress>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QList>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTemporaryDir>
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
    int mainRequestCount = 0;
    int splitterRequestCount = 0;
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
            QByteArray responseBody;
            if (splitterRequest) {
                ++splitterRequestCount;
                responseBody = splitterRequestCount == 1
                    ? chatCompletionResponse(QStringLiteral("[\"她轻轻看了你一眼。\",\"“今天也辛苦了。”\",\"然后她慢慢把书合上。\"]"))
                    : chatCompletionResponse(QStringLiteral("not json"));
            } else {
                ++mainRequestCount;
                if (mainRequestCount == 1) {
                    responseBody = chatCompletionResponse(QStringLiteral("{状态：她有些困了，声音变轻}\n\n她轻轻看了你一眼。\n\n“今天也辛苦了。”\n\n然后她慢慢把书合上。"));
                } else if (mainRequestCount == 2) {
                    responseBody = chatCompletionResponse(QStringLiteral("Astra looked up from the report.\n\n\"Enough.\"\n\nShe closed the file and waited."));
                } else {
                    responseBody = chatCompletionResponse(QStringLiteral("disabled raw line"));
                }
            }

            const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                + QByteArray::number(responseBody.size())
                + QByteArray("\r\nConnection: close\r\n\r\n")
                + responseBody;
            socket->write(response);
            socket->disconnectFromHost();
        });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() {
            delete buffer;
        });
    });

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

    const QVariantMap firstResult = bridge.sendChatMessageWithReply(QStringLiteral("first"));
    if (!firstResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("first sendChatMessageWithReply failed")) ? 0 : 1;
    }
    if (mainRequestCount != 1 || splitterRequestCount != 1) {
        return fail(QStringLiteral("first reply should call main model and output splitter")) ? 0 : 1;
    }

    const QString conversationPath = root.absoluteFilePath(QStringLiteral("data/conversations.json"));
    QJsonArray saved = readJsonArray(conversationPath);
    const QJsonObject firstAssistant = saved.at(1).toObject();
    const QString firstRaw = firstAssistant.value(QStringLiteral("content")).toString();
    const QJsonArray firstParts = firstAssistant.value(QStringLiteral("display_parts")).toArray();
    if (!firstRaw.contains(QStringLiteral("{状态：她有些困了")) || firstParts.size() != 3) {
        return fail(QStringLiteral("first assistant should preserve raw content and store three display parts")) ? 0 : 1;
    }
    if (firstParts.first().toString().contains(QStringLiteral("状态"))
        || firstParts.first().toString() != QStringLiteral("她轻轻看了你一眼。")
        || firstParts.at(1).toString() != QStringLiteral("“今天也辛苦了。”")
        || firstParts.at(2).toString() != QStringLiteral("然后她慢慢把书合上。")) {
        return fail(QStringLiteral("output splitter should filter status and keep original visible text")) ? 0 : 1;
    }
    const QVariantList exposedParts = bridge.chatMessages().at(1).toMap().value(QStringLiteral("parts")).toList();
    if (exposedParts.size() != 3 || exposedParts.at(1).toString() != QStringLiteral("“今天也辛苦了。”")) {
        return fail(QStringLiteral("chatMessages should expose split parts to QML")) ? 0 : 1;
    }
    const QString exposedContent = bridge.chatMessages().at(1).toMap().value(QStringLiteral("content")).toString();
    if (exposedContent.contains(QStringLiteral("状态"))
        || !exposedContent.contains(QStringLiteral("她轻轻看了你一眼。"))
        || !exposedContent.contains(QStringLiteral("然后她慢慢把书合上。"))) {
        return fail(QStringLiteral("chatMessages should not expose raw assistant content when output splitting is enabled")) ? 0 : 1;
    }

    const QVariantMap secondResult = bridge.sendChatMessageWithReply(QStringLiteral("second"));
    if (!secondResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("second sendChatMessageWithReply failed")) ? 0 : 1;
    }
    if (mainRequestCount != 2 || splitterRequestCount != 2) {
        return fail(QStringLiteral("second reply should also call output splitter")) ? 0 : 1;
    }

    saved = readJsonArray(conversationPath);
    const QJsonObject secondAssistant = saved.at(3).toObject();
    const QJsonArray fallbackParts = secondAssistant.value(QStringLiteral("display_parts")).toArray();
    if (secondAssistant.value(QStringLiteral("content")).toString() != QStringLiteral("Astra looked up from the report.\n\n\"Enough.\"\n\nShe closed the file and waited.")
        || fallbackParts.size() != 3
        || fallbackParts.first().toString() != QStringLiteral("Astra looked up from the report.")
        || fallbackParts.at(1).toString() != QStringLiteral("\"Enough.\"")
        || fallbackParts.at(2).toString() != QStringLiteral("She closed the file and waited.")) {
        return fail(QStringLiteral("invalid splitter JSON should use local bubble splitting instead of exposing raw text")) ? 0 : 1;
    }
    const QVariantList fallbackExposedParts = bridge.chatMessages().at(3).toMap().value(QStringLiteral("parts")).toList();
    if (fallbackExposedParts.size() != 3
        || fallbackExposedParts.at(1).toString() != QStringLiteral("\"Enough.\"")) {
        return fail(QStringLiteral("chatMessages should expose local fallback bubbles when the splitter fails")) ? 0 : 1;
    }

    QJsonObject disabledSettings;
    disabledSettings.insert(QStringLiteral("output_splitting_enabled"), false);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/settings.json")), QJsonDocument(disabledSettings))) {
        return fail(QStringLiteral("failed to disable output splitting")) ? 0 : 1;
    }
    bridge.refreshLegacyScan();

    const QVariantMap thirdResult = bridge.sendChatMessageWithReply(QStringLiteral("third"));
    if (!thirdResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("third sendChatMessageWithReply failed")) ? 0 : 1;
    }
    if (mainRequestCount != 3 || splitterRequestCount != 2) {
        return fail(QStringLiteral("disabled output splitting should skip the subagent request")) ? 0 : 1;
    }

    saved = readJsonArray(conversationPath);
    const QJsonObject thirdAssistant = saved.at(5).toObject();
    if (thirdAssistant.contains(QStringLiteral("display_parts"))) {
        return fail(QStringLiteral("disabled output splitting should not store display_parts")) ? 0 : 1;
    }
    const QVariantList disabledExposedParts = bridge.chatMessages().at(5).toMap().value(QStringLiteral("parts")).toList();
    if (disabledExposedParts.size() != 1
        || disabledExposedParts.first().toString() != thirdAssistant.value(QStringLiteral("content")).toString()) {
        return fail(QStringLiteral("disabled output splitting should expose the raw reply as one bubble")) ? 0 : 1;
    }

    return 0;
}
