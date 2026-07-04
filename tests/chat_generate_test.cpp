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

QJsonObject readJsonObject(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).object();
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
        QStringLiteral("data/mods/state_journal"),
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

    QFile(root.absoluteFilePath(QStringLiteral("data/mods/state_journal/state_journal.db"))).open(QIODevice::WriteOnly);
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
    QByteArray capturedRequest;
    QList<QByteArray> mainRequestBodies;
    QList<QByteArray> splitterRequestBodies;
    bool responded = false;
    int requestCount = 0;
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
            capturedRequest = header;
            ++requestCount;
            const bool splitterRequest = QString::fromUtf8(requestBody).contains(QStringLiteral("聊天输出后处理器"));
            QByteArray responseBody;
            if (splitterRequest) {
                splitterRequestBodies.append(requestBody);
                responseBody = QStringLiteral(R"({"choices":[{"message":{"content":"[\"assistant route reply %1\"]"}}]})")
                    .arg(splitterRequestBodies.size())
                    .toUtf8();
            } else {
                mainRequestBodies.append(requestBody);
                responseBody = QStringLiteral(R"({"choices":[{"message":{"content":"assistant route reply %1"}}]})")
                    .arg(mainRequestBodies.size())
                    .toUtf8();
            }
            const QByteArray response = QByteArray("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ")
                + QByteArray::number(responseBody.size())
                + QByteArray("\r\nConnection: close\r\n\r\n")
                + responseBody;
            socket->write(response);
            socket->flush();
            socket->disconnectFromHost();
            responded = true;
        });
        QObject::connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        QObject::connect(socket, &QTcpSocket::destroyed, [buffer]() {
            delete buffer;
        });
    });

    QJsonObject settings;
    settings.insert(QStringLiteral("temperature"), 0.4);
    settings.insert(QStringLiteral("history_limit"), 8);
    settings.insert(QStringLiteral("request_timeout"), 10);
    settings.insert(QStringLiteral("demo_mode"), false);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/settings.json")), QJsonDocument(settings))) {
        return fail(QStringLiteral("failed to write settings fixture")) ? 0 : 1;
    }

    QJsonObject provider;
    provider.insert(QStringLiteral("id"), QStringLiteral("local"));
    provider.insert(QStringLiteral("name"), QStringLiteral("Local Fake"));
    provider.insert(QStringLiteral("enabled"), true);
    provider.insert(QStringLiteral("priority"), 1);
    provider.insert(QStringLiteral("base_url"), QStringLiteral("http://127.0.0.1:%1").arg(server.serverPort()));
    provider.insert(QStringLiteral("model"), QStringLiteral("Route Model"));
    provider.insert(QStringLiteral("keys"), QJsonArray{ QStringLiteral("route-key") });

    QJsonObject routes;
    routes.insert(QStringLiteral("enabled"), true);
    routes.insert(QStringLiteral("providers"), QJsonArray{ provider });
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/route_forwarding.json")), QJsonDocument(routes))) {
        return fail(QStringLiteral("failed to write route fixture")) ? 0 : 1;
    }

    QJsonObject rawCard;
    rawCard.insert(QStringLiteral("name"), QStringLiteral("Astra"));
    rawCard.insert(QStringLiteral("description"), QStringLiteral("A calm starship navigator."));
    rawCard.insert(QStringLiteral("personality"), QStringLiteral("Patient and observant."));
    rawCard.insert(QStringLiteral("scenario"), QStringLiteral("A quiet bridge before a jump."));
    QJsonObject card;
    card.insert(QStringLiteral("source_name"), QStringLiteral("astra.json"));
    card.insert(QStringLiteral("card_uid"), QStringLiteral("card-astra"));
    card.insert(QStringLiteral("raw"), rawCard);
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/current_role_card.json")), QJsonDocument(card))) {
        return fail(QStringLiteral("failed to write card fixture")) ? 0 : 1;
    }

    QJsonObject userProfile;
    userProfile.insert(QStringLiteral("nickname"), QStringLiteral("Pilot"));
    userProfile.insert(QStringLiteral("profile_text"), QStringLiteral("Likes careful navigation."));
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/user_profile.json")), QJsonDocument(userProfile))) {
        return fail(QStringLiteral("failed to write user profile fixture")) ? 0 : 1;
    }

    QJsonObject worldbookSettings;
    worldbookSettings.insert(QStringLiteral("enabled"), true);
    worldbookSettings.insert(QStringLiteral("max_hits"), 2);
    worldbookSettings.insert(QStringLiteral("default_match_mode"), QStringLiteral("any"));
    worldbookSettings.insert(QStringLiteral("default_secondary_mode"), QStringLiteral("all"));
    worldbookSettings.insert(QStringLiteral("default_group_operator"), QStringLiteral("and"));
    worldbookSettings.insert(QStringLiteral("default_chance"), 100);

    QJsonObject constantEntry;
    constantEntry.insert(QStringLiteral("id"), QStringLiteral("wb-constant"));
    constantEntry.insert(QStringLiteral("title"), QStringLiteral("Ship Law"));
    constantEntry.insert(QStringLiteral("entry_type"), QStringLiteral("constant"));
    constantEntry.insert(QStringLiteral("content"), QStringLiteral("Astra never ignores jump safety."));
    constantEntry.insert(QStringLiteral("order"), 1);

    QJsonObject matchedEntry;
    matchedEntry.insert(QStringLiteral("id"), QStringLiteral("wb-aster-gate"));
    matchedEntry.insert(QStringLiteral("title"), QStringLiteral("Aster Gate"));
    matchedEntry.insert(QStringLiteral("trigger"), QStringLiteral("Aster Gate|safe jump"));
    matchedEntry.insert(QStringLiteral("secondary_trigger"), QStringLiteral("bridge"));
    matchedEntry.insert(QStringLiteral("content"), QStringLiteral("The Aster Gate requires silent orbit alignment."));
    matchedEntry.insert(QStringLiteral("order"), 5);

    QJsonObject skippedEntry;
    skippedEntry.insert(QStringLiteral("id"), QStringLiteral("wb-skip"));
    skippedEntry.insert(QStringLiteral("title"), QStringLiteral("Skipped"));
    skippedEntry.insert(QStringLiteral("trigger"), QStringLiteral("Plot"));
    skippedEntry.insert(QStringLiteral("content"), QStringLiteral("SHOULD_NOT_APPEAR"));
    skippedEntry.insert(QStringLiteral("chance"), 0);
    skippedEntry.insert(QStringLiteral("order"), 2);

    QJsonObject overflowEntry;
    overflowEntry.insert(QStringLiteral("id"), QStringLiteral("wb-overflow"));
    overflowEntry.insert(QStringLiteral("title"), QStringLiteral("Overflow"));
    overflowEntry.insert(QStringLiteral("trigger"), QStringLiteral("Plot"));
    overflowEntry.insert(QStringLiteral("content"), QStringLiteral("MAX_HITS_EXCLUDED"));
    overflowEntry.insert(QStringLiteral("order"), 99);

    QJsonObject worldbook;
    worldbook.insert(QStringLiteral("settings"), worldbookSettings);
    worldbook.insert(QStringLiteral("entries"), QJsonArray{ constantEntry, matchedEntry, skippedEntry, overflowEntry });
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/worldbook.json")), QJsonDocument(worldbook))) {
        return fail(QStringLiteral("failed to write worldbook fixture")) ? 0 : 1;
    }

    if (!root.mkpath(QStringLiteral("data/card_runtime/cards/card-astra"))) {
        return fail(QStringLiteral("failed to create memory runtime fixture")) ? 0 : 1;
    }
    const QDir memoryDir(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/card-astra")));

    QJsonObject activeMemory;
    activeMemory.insert(QStringLiteral("id"), QStringLiteral("memory-active"));
    activeMemory.insert(QStringLiteral("title"), QStringLiteral("Gate Promise"));
    activeMemory.insert(QStringLiteral("content"), QStringLiteral("Pilot asked Astra to double-check every Aster Gate jump."));
    activeMemory.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("jump"), QStringLiteral("trust") });
    activeMemory.insert(QStringLiteral("notes"), QStringLiteral("Keep the tone careful and collaborative."));
    activeMemory.insert(QStringLiteral("memory_status"), QStringLiteral("active"));

    QJsonObject archivedMemory;
    archivedMemory.insert(QStringLiteral("id"), QStringLiteral("memory-archived"));
    archivedMemory.insert(QStringLiteral("title"), QStringLiteral("Archived Secret"));
    archivedMemory.insert(QStringLiteral("content"), QStringLiteral("ARCHIVED_MEMORY_SHOULD_NOT_APPEAR"));
    archivedMemory.insert(QStringLiteral("memory_status"), QStringLiteral("archived"));

    if (!writeJson(memoryDir.absoluteFilePath(QStringLiteral("memories.json")), QJsonDocument(QJsonArray{ activeMemory, archivedMemory }))) {
        return fail(QStringLiteral("failed to write memories fixture")) ? 0 : 1;
    }

    QJsonObject mergedMemory;
    mergedMemory.insert(QStringLiteral("id"), QStringLiteral("merged-1"));
    mergedMemory.insert(QStringLiteral("title"), QStringLiteral("Route Ritual"));
    mergedMemory.insert(QStringLiteral("content"), QStringLiteral("Astra and Pilot call the safety checklist the blue ritual."));
    mergedMemory.insert(QStringLiteral("tags"), QJsonArray{ QStringLiteral("ritual") });
    if (!writeJson(memoryDir.absoluteFilePath(QStringLiteral("merged_memories.json")), QJsonDocument(QJsonArray{ mergedMemory }))) {
        return fail(QStringLiteral("failed to write merged memories fixture")) ? 0 : 1;
    }

    QJsonObject outlineItem;
    outlineItem.insert(QStringLiteral("id"), QStringLiteral("outline-1"));
    outlineItem.insert(QStringLiteral("title"), QStringLiteral("Bridge Chapter"));
    outlineItem.insert(QStringLiteral("summary"), QStringLiteral("The bridge crew prepares a quiet Aster Gate jump."));
    outlineItem.insert(QStringLiteral("location"), QStringLiteral("Observation bridge"));
    outlineItem.insert(QStringLiteral("key_events"), QJsonArray{ QStringLiteral("Pilot trusts Astra's navigation call.") });
    outlineItem.insert(QStringLiteral("participate_recall"), true);
    if (!writeJson(memoryDir.absoluteFilePath(QStringLiteral("memory_outline.json")), QJsonDocument(QJsonArray{ outlineItem }))) {
        return fail(QStringLiteral("failed to write memory outline fixture")) ? 0 : 1;
    }

    QJsonObject oldMessage;
    oldMessage.insert(QStringLiteral("role"), QStringLiteral("assistant"));
    oldMessage.insert(QStringLiteral("content"), QStringLiteral("old assistant line"));
    oldMessage.insert(QStringLiteral("unknown_meta"), QStringLiteral("meta-stays"));
    if (!writeJson(root.absoluteFilePath(QStringLiteral("data/conversations.json")), QJsonDocument(QJsonArray{ oldMessage }))) {
        return fail(QStringLiteral("failed to write conversation fixture")) ? 0 : 1;
    }

    qunsetenv("LLM_BASE_URL");
    qunsetenv("LLM_API_KEY");
    qunsetenv("LLM_MODEL");
    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));

    FantarealBridge bridge;
    const QVariantMap result = bridge.sendChatMessageWithReply(QStringLiteral("Plot a safe jump near the Aster Gate from the bridge."));
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("sendChatMessageWithReply failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (!responded || mainRequestBodies.size() != 1 || splitterRequestBodies.size() != 1 || requestCount != 2) {
        return fail(QStringLiteral("fake chat server did not receive a request")) ? 0 : 1;
    }
    if (!capturedRequest.startsWith("POST /v1/chat/completions ")
        || !capturedRequest.contains("Authorization: Bearer route-key")) {
        return fail(QStringLiteral("chat generation should use route provider endpoint and key")) ? 0 : 1;
    }

    const QJsonObject requestPayload = QJsonDocument::fromJson(mainRequestBodies.first()).object();
    const QJsonArray requestMessages = requestPayload.value("messages").toArray();
    const QString systemPrompt = requestMessages.first().toObject().value("content").toString();
    if (requestPayload.value("model").toString() != QStringLiteral("route-model")
        || requestPayload.value("temperature").toDouble() != 0.4
        || requestMessages.size() < 2
        || !systemPrompt.contains(QStringLiteral("Astra"))
        || requestMessages.last().toObject().value("content").toString() != QStringLiteral("Plot a safe jump near the Aster Gate from the bridge.")) {
        return fail(QStringLiteral("chat generation payload did not include expected model or prompt context")) ? 0 : 1;
    }
    if (!systemPrompt.contains(QStringLiteral("[Worldbook]"))
        || !systemPrompt.contains(QStringLiteral("Astra never ignores jump safety."))
        || !systemPrompt.contains(QStringLiteral("The Aster Gate requires silent orbit alignment."))
        || systemPrompt.contains(QStringLiteral("SHOULD_NOT_APPEAR"))
        || systemPrompt.contains(QStringLiteral("MAX_HITS_EXCLUDED"))) {
        return fail(QStringLiteral("chat generation payload should include matched worldbook notes only")) ? 0 : 1;
    }
    if (!systemPrompt.contains(QStringLiteral("[Memory]"))
        || !systemPrompt.contains(QStringLiteral("Pilot asked Astra to double-check every Aster Gate jump."))
        || !systemPrompt.contains(QStringLiteral("the blue ritual"))
        || !systemPrompt.contains(QStringLiteral("The bridge crew prepares a quiet Aster Gate jump."))
        || systemPrompt.contains(QStringLiteral("ARCHIVED_MEMORY_SHOULD_NOT_APPEAR"))) {
        return fail(QStringLiteral("chat generation payload should include active memory context and exclude archived memories")) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("conversation backup was not created")) ? 0 : 1;
    }

    const QJsonArray saved = readJsonArray(root.absoluteFilePath(QStringLiteral("data/conversations.json")));
    if (saved.size() != 3
        || saved.first().toObject().value("unknown_meta").toString() != QStringLiteral("meta-stays")
        || saved.at(1).toObject().value("role").toString() != QStringLiteral("user")
        || saved.at(1).toObject().value("source").toString() != QStringLiteral("huskarui")
        || saved.at(2).toObject().value("role").toString() != QStringLiteral("assistant")
        || saved.at(2).toObject().value("content").toString() != QStringLiteral("assistant route reply 1")
        || saved.at(2).toObject().value("source").toString() != QStringLiteral("huskarui-llm")) {
        return fail(QStringLiteral("conversation should preserve old metadata and append user plus assistant messages")) ? 0 : 1;
    }
    if (saved.at(2).toObject().value(QStringLiteral("display_parts")).toArray().size() != 1
        || saved.at(2).toObject().value(QStringLiteral("display_parts")).toArray().first().toString() != QStringLiteral("assistant route reply 1")) {
        return fail(QStringLiteral("generated assistant message should store output-split display parts")) ? 0 : 1;
    }

    if (bridge.chatMessages().size() != 3) {
        return fail(QStringLiteral("chatMessages should refresh after generated reply")) ? 0 : 1;
    }

    const QString firstAssistantMessageId = saved.at(2).toObject().value(QStringLiteral("message_id")).toString();
    const QVariantMap retryResult = bridge.regenerateLastChatReply();
    if (!retryResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("regenerateLastChatReply failed: %1").arg(retryResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (mainRequestBodies.size() != 2 || splitterRequestBodies.size() != 2 || requestCount != 4) {
        return fail(QStringLiteral("retry should call the fake chat server once for generation and once for output splitting")) ? 0 : 1;
    }

    const QString retryBackupPath = retryResult.value(QStringLiteral("backupPath")).toString();
    if (retryBackupPath.isEmpty() || !QFileInfo::exists(retryBackupPath)) {
        return fail(QStringLiteral("retry backup was not created")) ? 0 : 1;
    }

    const QJsonArray retried = readJsonArray(root.absoluteFilePath(QStringLiteral("data/conversations.json")));
    if (retried.size() != 3
        || retried.first().toObject().value("unknown_meta").toString() != QStringLiteral("meta-stays")
        || retried.at(1).toObject().value("content").toString() != QStringLiteral("Plot a safe jump near the Aster Gate from the bridge.")
        || retried.at(2).toObject().value("role").toString() != QStringLiteral("assistant")
        || retried.at(2).toObject().value("content").toString() != QStringLiteral("assistant route reply 2")
        || retried.at(2).toObject().value("source").toString() != QStringLiteral("huskarui-llm")) {
        return fail(QStringLiteral("retry should replace the last assistant reply without duplicating user messages")) ? 0 : 1;
    }
    if (retried.at(2).toObject().value(QStringLiteral("display_parts")).toArray().size() != 1
        || retried.at(2).toObject().value(QStringLiteral("display_parts")).toArray().first().toString() != QStringLiteral("assistant route reply 2")) {
        return fail(QStringLiteral("retry assistant message should store refreshed output-split display parts")) ? 0 : 1;
    }
    if (retried.at(2).toObject().value(QStringLiteral("message_id")).toString() == firstAssistantMessageId) {
        return fail(QStringLiteral("retry should write a fresh assistant message id")) ? 0 : 1;
    }
    if (bridge.chatMessages().size() != 3) {
        return fail(QStringLiteral("chatMessages should refresh after retry")) ? 0 : 1;
    }

    return 0;
}
