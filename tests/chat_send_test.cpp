#include "fantarealbridge.h"

#include <QByteArray>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHash>
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

bool writeJson(const QString& path, const QJsonDocument& document) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    return file.write(document.toJson(QJsonDocument::Indented)) > 0;
}

bool writeBytes(const QString& path, const QByteArray& payload) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }
    return file.write(payload) == payload.size();
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
        { QStringLiteral("data/persona.json"), QJsonObject{ { QStringLiteral("name"), QStringLiteral("Mira") } } },
        { QStringLiteral("data/user_profile.json"), QJsonObject{} },
        { QStringLiteral("data/auto_saga/state.json"), QJsonObject{} },
        { QStringLiteral("cards/template_single_role_card.json"), QJsonObject{} },
        { QStringLiteral("cards/template_multi_role_card.json"), QJsonObject{} },
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

    QJsonArray initialConversation;
    initialConversation.append(QJsonObject{
        { QStringLiteral("role"), QStringLiteral("assistant") },
        { QStringLiteral("content"), QStringLiteral("旧消息") },
        { QStringLiteral("created_at"), QStringLiteral("2026-01-01 00:00:00") },
        { QStringLiteral("unknown_meta"), QStringLiteral("must-stay") },
    });
    initialConversation.append(QJsonObject{
        { QStringLiteral("role"), QStringLiteral("bogus") },
        { QStringLiteral("content"), QStringLiteral("UI 模型应忽略，但写回时保留") },
    });

    const QString conversationPath = root.absoluteFilePath(QStringLiteral("data/conversations.json"));
    if (!writeJson(conversationPath, QJsonDocument(initialConversation))) {
        return fail(QStringLiteral("failed to write fixture conversations.json")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    if (bridge.chatMessages().size() != 1) {
        return fail(QStringLiteral("chatMessages should expose only valid role/content items")) ? 0 : 1;
    }

    const QVariantMap emptyResult = bridge.sendChatMessage(QStringLiteral("   \n  "));
    if (emptyResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("blank chat message should be rejected")) ? 0 : 1;
    }

    const QVariantMap result = bridge.sendChatMessage(QStringLiteral("  你好，HuskarUI。\r\n\r\n请记录这条消息。  "));
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("sendChatMessage failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("conversation backup was not created")) ? 0 : 1;
    }

    const QJsonArray saved = readJsonArray(conversationPath);
    if (saved.size() != 3) {
        return fail(QStringLiteral("conversation should preserve old entries and append one new message")) ? 0 : 1;
    }
    if (saved.at(0).toObject().value("unknown_meta").toString() != QStringLiteral("must-stay")) {
        return fail(QStringLiteral("unknown metadata on existing messages was not preserved")) ? 0 : 1;
    }

    const QJsonObject appended = saved.last().toObject();
    if (appended.value("role").toString() != QStringLiteral("user")) {
        return fail(QStringLiteral("appended message role should be user")) ? 0 : 1;
    }
    if (appended.value("content").toString() != QStringLiteral("你好，HuskarUI。\n\n请记录这条消息。")) {
        return fail(QStringLiteral("appended message content was not sanitized as expected")) ? 0 : 1;
    }
    if (appended.value("created_at").toString().isEmpty()) {
        return fail(QStringLiteral("appended message missing created_at")) ? 0 : 1;
    }
    if (appended.value("message_id").toString().isEmpty()) {
        return fail(QStringLiteral("appended message missing message_id")) ? 0 : 1;
    }
    if (appended.value("source").toString() != QStringLiteral("huskarui")) {
        return fail(QStringLiteral("appended message source should be huskarui")) ? 0 : 1;
    }
    if (bridge.chatMessages().size() != 2) {
        return fail(QStringLiteral("chatMessages should refresh after send")) ? 0 : 1;
    }

    const QVariantMap demoResult = bridge.sendChatMessageDemoReply(QStringLiteral(" 演示一下 "));
    if (!demoResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("sendChatMessageDemoReply failed: %1").arg(demoResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QString demoBackupPath = demoResult.value(QStringLiteral("backupPath")).toString();
    if (demoBackupPath.isEmpty() || !QFileInfo::exists(demoBackupPath)) {
        return fail(QStringLiteral("demo reply backup was not created")) ? 0 : 1;
    }

    const QJsonArray savedWithDemo = readJsonArray(conversationPath);
    if (savedWithDemo.size() != 5) {
        return fail(QStringLiteral("demo reply should append user and assistant messages")) ? 0 : 1;
    }
    const QJsonObject demoUser = savedWithDemo.at(3).toObject();
    const QJsonObject demoAssistant = savedWithDemo.at(4).toObject();
    if (demoUser.value("role").toString() != QStringLiteral("user")
        || demoUser.value("content").toString() != QStringLiteral("演示一下")) {
        return fail(QStringLiteral("demo user message was not appended correctly")) ? 0 : 1;
    }
    if (demoAssistant.value("role").toString() != QStringLiteral("assistant")
        || demoAssistant.value("source").toString() != QStringLiteral("huskarui-demo")
        || !demoAssistant.value("content").toString().contains(QStringLiteral("演示模式"))
        || !demoAssistant.value("content").toString().contains(QStringLiteral("Mira"))) {
        return fail(QStringLiteral("demo assistant reply should be local and character-aware")) ? 0 : 1;
    }
    if (demoAssistant.value(QStringLiteral("display_parts")).toArray().size() != 1
        || demoAssistant.value(QStringLiteral("display_parts")).toArray().first().toString() != demoAssistant.value("content").toString()) {
        return fail(QStringLiteral("demo assistant reply should expose fallback display parts")) ? 0 : 1;
    }
    if (bridge.chatMessages().size() != 4) {
        return fail(QStringLiteral("chatMessages should refresh after demo reply")) ? 0 : 1;
    }

    QTemporaryDir blankTempDir;
    if (!blankTempDir.isValid()) {
        return fail(QStringLiteral("failed to create blank JSON temporary directory")) ? 0 : 1;
    }
    QDir blankRoot(blankTempDir.path());
    if (!makeRequiredFiles(blankRoot)) {
        return fail(QStringLiteral("failed to create blank JSON Fantareal fixture")) ? 0 : 1;
    }
    const QString blankConversationPath = blankRoot.absoluteFilePath(QStringLiteral("data/conversations.json"));
    if (!writeBytes(blankConversationPath, QByteArray::fromHex("efbbbf"))) {
        return fail(QStringLiteral("failed to write BOM-only conversations fixture")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(blankRoot.absolutePath()));
    FantarealBridge blankBridge;
    if (!blankBridge.chatMessages().isEmpty()) {
        return fail(QStringLiteral("BOM-only conversations.json should load as empty history")) ? 0 : 1;
    }
    const QVariantMap blankResult = blankBridge.sendChatMessage(QStringLiteral("First after blank"));
    if (!blankResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("sendChatMessage should recover BOM-only conversations.json: %1").arg(blankResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QJsonArray blankSaved = readJsonArray(blankConversationPath);
    if (blankSaved.size() != 1
        || blankSaved.first().toObject().value(QStringLiteral("role")).toString() != QStringLiteral("user")) {
        return fail(QStringLiteral("BOM-only conversations.json should be replaced by one saved user message")) ? 0 : 1;
    }

    return 0;
}
