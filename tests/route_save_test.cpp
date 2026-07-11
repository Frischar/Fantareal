#include "fantarealbridge.h"

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

QJsonObject readJsonObject(const QString& path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QJsonDocument::fromJson(file.readAll()).object();
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

    QJsonObject routeConfig;
    routeConfig.insert(QStringLiteral("enabled"), false);
    routeConfig.insert(QStringLiteral("hook_all_posts"), true);
    routeConfig.insert(QStringLiteral("failover_enabled"), true);
    routeConfig.insert(QStringLiteral("rotate_keys"), true);
    routeConfig.insert(QStringLiteral("retry_attempts"), 3);
    routeConfig.insert(QStringLiteral("strategy"), QStringLiteral("priority"));
    routeConfig.insert(QStringLiteral("unknown_store_field"), QStringLiteral("must-stay"));
    routeConfig.insert(QStringLiteral("providers"), QJsonArray{
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("p1") },
            { QStringLiteral("name"), QStringLiteral("P1") },
            { QStringLiteral("base_url"), QStringLiteral("https://p1.example/v1") },
            { QStringLiteral("model"), QStringLiteral("model-a") },
            { QStringLiteral("enabled"), true },
            { QStringLiteral("priority"), 2 },
            { QStringLiteral("weight"), 7 },
            { QStringLiteral("keys"), QJsonArray{ QStringLiteral("secret-a"), QStringLiteral("secret-b") } },
            { QStringLiteral("unknown_provider_field"), QStringLiteral("provider-stays") },
        },
        QJsonObject{
            { QStringLiteral("id"), QStringLiteral("legacy") },
            { QStringLiteral("name"), QStringLiteral("Legacy") },
            { QStringLiteral("api_key"), QStringLiteral("legacy-secret") },
            { QStringLiteral("enabled"), false },
        },
    });

    const QString routePath = root.absoluteFilePath(QStringLiteral("data/route_forwarding.json"));
    if (!writeJson(routePath, QJsonDocument(routeConfig))) {
        return fail(QStringLiteral("failed to write fixture route_forwarding.json")) ? 0 : 1;
    }

    qputenv("FANTAREAL_ROOT", QFile::encodeName(root.absolutePath()));
    FantarealBridge bridge;
    const QVariantMap initialDraft = bridge.routeDraft();
    if (initialDraft.value(QStringLiteral("providerCount")).toInt() != 2) {
        return fail(QStringLiteral("routeDraft should expose provider count")) ? 0 : 1;
    }
    const QVariantList providers = initialDraft.value(QStringLiteral("providers")).toList();
    if (providers.size() != 2) {
        return fail(QStringLiteral("routeDraft should expose provider summaries")) ? 0 : 1;
    }
    const QVariantMap firstProvider = providers.first().toMap();
    if (firstProvider.contains(QStringLiteral("keys")) || firstProvider.contains(QStringLiteral("api_key"))) {
        return fail(QStringLiteral("routeDraft must not expose provider secrets")) ? 0 : 1;
    }
    if (firstProvider.value(QStringLiteral("keyCount")).toInt() != 2) {
        return fail(QStringLiteral("routeDraft should expose only key count")) ? 0 : 1;
    }

    QVariantMap draft;
    draft.insert(QStringLiteral("enabled"), true);
    draft.insert(QStringLiteral("hook_all_posts"), false);
    draft.insert(QStringLiteral("failover_enabled"), false);
    draft.insert(QStringLiteral("rotate_keys"), false);
    draft.insert(QStringLiteral("retry_attempts"), 99);
    draft.insert(QStringLiteral("strategy"), QStringLiteral("bad-strategy"));

    const QVariantMap result = bridge.saveRouteDraft(draft);
    if (!result.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveRouteDraft failed: %1").arg(result.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QString backupPath = result.value(QStringLiteral("backupPath")).toString();
    if (backupPath.isEmpty() || !QFileInfo::exists(backupPath)) {
        return fail(QStringLiteral("route backup was not created")) ? 0 : 1;
    }

    const QJsonObject saved = readJsonObject(routePath);
    if (!saved.value("enabled").toBool(false)
        || saved.value("hook_all_posts").toBool(true)
        || saved.value("failover_enabled").toBool(true)
        || saved.value("rotate_keys").toBool(true)) {
        return fail(QStringLiteral("route boolean fields were not saved")) ? 0 : 1;
    }
    if (saved.value("retry_attempts").toInt() != 10) {
        return fail(QStringLiteral("retry_attempts should clamp to 10")) ? 0 : 1;
    }
    if (saved.value("strategy").toString() != QStringLiteral("priority")) {
        return fail(QStringLiteral("invalid strategy should normalize to priority")) ? 0 : 1;
    }
    if (saved.value("unknown_store_field").toString() != QStringLiteral("must-stay")) {
        return fail(QStringLiteral("unknown route field was not preserved")) ? 0 : 1;
    }

    const QJsonArray savedProviders = saved.value("providers").toArray();
    if (savedProviders.size() != 2) {
        return fail(QStringLiteral("providers should be preserved")) ? 0 : 1;
    }
    const QJsonObject savedFirstProvider = savedProviders.first().toObject();
    if (savedFirstProvider.value("keys").toArray().at(0).toString() != QStringLiteral("secret-a")
        || savedFirstProvider.value("unknown_provider_field").toString() != QStringLiteral("provider-stays")) {
        return fail(QStringLiteral("provider keys/unknown fields should be preserved")) ? 0 : 1;
    }
    if (savedProviders.at(1).toObject().value("api_key").toString() != QStringLiteral("legacy-secret")) {
        return fail(QStringLiteral("legacy provider api_key should be preserved")) ? 0 : 1;
    }

    const QVariantMap refreshedDraft = bridge.routeDraft();
    if (!refreshedDraft.value(QStringLiteral("enabled")).toBool()
        || refreshedDraft.value(QStringLiteral("retry_attempts")).toInt() != 10
        || refreshedDraft.value(QStringLiteral("strategy")).toString() != QStringLiteral("priority")) {
        return fail(QStringLiteral("routeDraft should refresh after save")) ? 0 : 1;
    }

    QVariantMap roundRobinDraft;
    roundRobinDraft.insert(QStringLiteral("strategy"), QStringLiteral("round_robin"));
    roundRobinDraft.insert(QStringLiteral("retry_attempts"), -5);
    const QVariantMap secondResult = bridge.saveRouteDraft(roundRobinDraft);
    if (!secondResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("second saveRouteDraft failed")) ? 0 : 1;
    }
    const QJsonObject secondSaved = readJsonObject(routePath);
    if (secondSaved.value("strategy").toString() != QStringLiteral("round_robin")
        || secondSaved.value("retry_attempts").toInt() != 1) {
        return fail(QStringLiteral("round_robin strategy or min clamp failed")) ? 0 : 1;
    }

    const QVariantMap emptyKeyResult = bridge.saveRouteProviderKey(0, QStringLiteral("   "));
    if (!emptyKeyResult.value(QStringLiteral("ok")).toBool()
        || !emptyKeyResult.value(QStringLiteral("backupPath")).toString().isEmpty()) {
        return fail(QStringLiteral("blank provider key save should be a no-op success without backup")) ? 0 : 1;
    }
    const QJsonObject afterBlankKey = readJsonObject(routePath);
    if (afterBlankKey.value("providers").toArray().first().toObject().value("keys").toArray().at(0).toString() != QStringLiteral("secret-a")) {
        return fail(QStringLiteral("blank provider key save must preserve existing keys")) ? 0 : 1;
    }

    const QVariantMap keyResult = bridge.saveRouteProviderKey(1, QStringLiteral("  new-legacy-key  "));
    if (!keyResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("saveRouteProviderKey failed: %1").arg(keyResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    const QString keyBackupPath = keyResult.value(QStringLiteral("backupPath")).toString();
    if (keyBackupPath.isEmpty() || !QFileInfo::exists(keyBackupPath)) {
        return fail(QStringLiteral("provider key backup was not created")) ? 0 : 1;
    }

    const QJsonObject afterKeySave = readJsonObject(routePath);
    const QJsonArray afterKeyProviders = afterKeySave.value("providers").toArray();
    const QJsonObject updatedLegacyProvider = afterKeyProviders.at(1).toObject();
    if (updatedLegacyProvider.value("keys").toArray().size() != 1
        || updatedLegacyProvider.value("keys").toArray().first().toString() != QStringLiteral("new-legacy-key")
        || updatedLegacyProvider.contains(QStringLiteral("api_key"))
        || updatedLegacyProvider.value("name").toString() != QStringLiteral("Legacy")
        || updatedLegacyProvider.value("enabled").toBool(true)) {
        return fail(QStringLiteral("provider key update should replace secrets while preserving safe provider fields")) ? 0 : 1;
    }

    const QVariantList providerDraftAfterKey = bridge.routeDraft().value(QStringLiteral("providers")).toList();
    const QVariantMap legacyProviderDraft = providerDraftAfterKey.at(1).toMap();
    if (legacyProviderDraft.contains(QStringLiteral("keys"))
        || legacyProviderDraft.contains(QStringLiteral("api_key"))
        || legacyProviderDraft.value(QStringLiteral("keyCount")).toInt() != 1) {
        return fail(QStringLiteral("routeDraft should remain secret-free after provider key update")) ? 0 : 1;
    }

    QVariantMap providerDraft;
    providerDraft.insert(QStringLiteral("id"), QStringLiteral("p1-renamed"));
    providerDraft.insert(QStringLiteral("name"), QStringLiteral("P1 Renamed"));
    providerDraft.insert(QStringLiteral("base_url"), QStringLiteral("https://p1-new.example/v1"));
    providerDraft.insert(QStringLiteral("model"), QStringLiteral("model-renamed"));
    providerDraft.insert(QStringLiteral("enabled"), true);
    providerDraft.insert(QStringLiteral("priority"), -5);
    providerDraft.insert(QStringLiteral("weight"), 1000);
    const QVariantMap providerResult = bridge.saveRouteProviderDraft(0, providerDraft);
    if (!providerResult.value(QStringLiteral("ok")).toBool()
        || providerResult.value(QStringLiteral("providerIndex")).toInt() != 0) {
        return fail(QStringLiteral("saveRouteProviderDraft update failed: %1").arg(providerResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (providerResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(providerResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("provider metadata update backup was not created")) ? 0 : 1;
    }

    const QJsonArray afterProviderEdit = readJsonObject(routePath).value("providers").toArray();
    const QJsonObject editedProvider = afterProviderEdit.first().toObject();
    if (editedProvider.value("id").toString() != QStringLiteral("p1-renamed")
        || editedProvider.value("name").toString() != QStringLiteral("P1 Renamed")
        || editedProvider.value("base_url").toString() != QStringLiteral("https://p1-new.example/v1")
        || editedProvider.value("model").toString() != QStringLiteral("model-renamed")
        || editedProvider.value("priority").toInt() != 1
        || editedProvider.value("weight").toInt() != 999) {
        return fail(QStringLiteral("provider safe metadata fields were not saved or clamped")) ? 0 : 1;
    }
    if (editedProvider.value("keys").toArray().first().toString() != QStringLiteral("secret-a")
        || editedProvider.value("unknown_provider_field").toString() != QStringLiteral("provider-stays")) {
        return fail(QStringLiteral("provider metadata edit should preserve secrets and unknown fields")) ? 0 : 1;
    }

    const QVariantMap duplicateIdResult = bridge.saveRouteProviderDraft(0, QVariantMap{
        { QStringLiteral("id"), QStringLiteral("legacy") },
        { QStringLiteral("name"), QStringLiteral("Duplicate") },
        { QStringLiteral("base_url"), QStringLiteral("https://dup.example/v1") },
        { QStringLiteral("model"), QStringLiteral("dup-model") },
        { QStringLiteral("enabled"), true },
    });
    if (duplicateIdResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("duplicate provider id should be rejected")) ? 0 : 1;
    }

    const QVariantMap invalidProviderResult = bridge.saveRouteProviderDraft(-1, QVariantMap{
        { QStringLiteral("name"), QStringLiteral("Broken Enabled") },
        { QStringLiteral("enabled"), true },
    });
    if (invalidProviderResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("enabled provider without endpoint/model should be rejected")) ? 0 : 1;
    }

    QVariantMap newProviderDraft;
    newProviderDraft.insert(QStringLiteral("id"), QStringLiteral("extra"));
    newProviderDraft.insert(QStringLiteral("name"), QStringLiteral("Extra Provider"));
    newProviderDraft.insert(QStringLiteral("base_url"), QStringLiteral("https://extra.example/v1"));
    newProviderDraft.insert(QStringLiteral("model"), QStringLiteral("extra-model"));
    newProviderDraft.insert(QStringLiteral("enabled"), true);
    newProviderDraft.insert(QStringLiteral("priority"), 5);
    newProviderDraft.insert(QStringLiteral("weight"), 2);
    const QVariantMap addProviderResult = bridge.saveRouteProviderDraft(-1, newProviderDraft);
    if (!addProviderResult.value(QStringLiteral("ok")).toBool()
        || addProviderResult.value(QStringLiteral("providerIndex")).toInt() != 2) {
        return fail(QStringLiteral("saveRouteProviderDraft add failed: %1").arg(addProviderResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }

    const QJsonArray afterProviderAdd = readJsonObject(routePath).value("providers").toArray();
    if (afterProviderAdd.size() != 3) {
        return fail(QStringLiteral("provider add should append one provider")) ? 0 : 1;
    }
    const QJsonObject addedProvider = afterProviderAdd.at(2).toObject();
    if (addedProvider.value("id").toString() != QStringLiteral("extra")
        || addedProvider.value("name").toString() != QStringLiteral("Extra Provider")
        || addedProvider.contains(QStringLiteral("keys"))
        || addedProvider.contains(QStringLiteral("api_key"))) {
        return fail(QStringLiteral("new provider should save safe fields without secrets")) ? 0 : 1;
    }

    const QVariantList providerDraftAfterAdd = bridge.routeDraft().value(QStringLiteral("providers")).toList();
    if (providerDraftAfterAdd.size() != 3
        || providerDraftAfterAdd.at(2).toMap().contains(QStringLiteral("keys"))
        || providerDraftAfterAdd.at(2).toMap().contains(QStringLiteral("api_key"))) {
        return fail(QStringLiteral("routeDraft should stay secret-free after provider add")) ? 0 : 1;
    }

    const QVariantMap deleteProviderResult = bridge.deleteRouteProvider(2);
    if (!deleteProviderResult.value(QStringLiteral("ok")).toBool()
        || deleteProviderResult.value(QStringLiteral("providerCount")).toInt() != 2) {
        return fail(QStringLiteral("deleteRouteProvider failed: %1").arg(deleteProviderResult.value(QStringLiteral("message")).toString())) ? 0 : 1;
    }
    if (deleteProviderResult.value(QStringLiteral("backupPath")).toString().isEmpty()
        || !QFileInfo::exists(deleteProviderResult.value(QStringLiteral("backupPath")).toString())) {
        return fail(QStringLiteral("provider delete backup was not created")) ? 0 : 1;
    }
    if (readJsonObject(routePath).value("providers").toArray().size() != 2) {
        return fail(QStringLiteral("provider delete should remove exactly one provider")) ? 0 : 1;
    }

    const QVariantMap invalidDeleteResult = bridge.deleteRouteProvider(99);
    if (invalidDeleteResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("invalid provider delete should be rejected")) ? 0 : 1;
    }

    const QVariantMap invalidKeyResult = bridge.saveRouteProviderKey(42, QStringLiteral("new-key"));
    if (invalidKeyResult.value(QStringLiteral("ok")).toBool()) {
        return fail(QStringLiteral("invalid provider index should be rejected")) ? 0 : 1;
    }

    return 0;
}
