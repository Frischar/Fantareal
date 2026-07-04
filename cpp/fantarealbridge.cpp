#include "fantarealbridge.h"

#include <algorithm>
#include <utility>

#include <QByteArray>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QDirIterator>
#include <QEventLoop>
#include <QFile>
#include <QFileInfo>
#include <QFileInfoList>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QPair>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStringList>
#include <QTimer>
#include <QUrl>
#include <QUuid>
#include <QVariantList>
#include <QVariantMap>

namespace {
constexpr auto kFirstLaunchDisclaimerVersion = "2026-07-v1";

QString firstLaunchConfirmationTextLiteral() {
    return QStringLiteral("我已阅读并理解上述声明，将自行承担本地部署、第三方 API 配置和使用行为的责任。");
}

QString normalizedConfirmationText(QString text) {
    text.remove(QRegularExpression(QStringLiteral("[\\s,，、.。．]+")));
    return text;
}

QByteArray normalizedJsonPayload(QByteArray data) {
    if (data.size() >= 3
        && static_cast<unsigned char>(data.at(0)) == 0xEF
        && static_cast<unsigned char>(data.at(1)) == 0xBB
        && static_cast<unsigned char>(data.at(2)) == 0xBF) {
        data.remove(0, 3);
    }
    return data;
}

bool parseJsonArrayPayload(
    QByteArray data,
    QJsonArray* array,
    QString* errorMessage,
    bool blankAsEmpty = true) {
    data = normalizedJsonPayload(std::move(data));
    if (blankAsEmpty && data.trimmed().isEmpty()) {
        if (array) {
            *array = QJsonArray{};
        }
        return true;
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(data, &error);
    if (error.error != QJsonParseError::NoError || !document.isArray()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("JSON 无效：%1").arg(error.errorString());
        }
        return false;
    }
    if (array) {
        *array = document.array();
    }
    return true;
}

QString displayText(const QString& value, const QString& fallback = QStringLiteral("未配置")) {
    const QString trimmed = value.trimmed();
    return trimmed.isEmpty() ? fallback : trimmed;
}

QString clippedText(const QString& value, int maxLength = 96, const QString& fallback = QStringLiteral("无内容")) {
    const QString trimmed = value.simplified();
    if (trimmed.isEmpty()) {
        return fallback;
    }
    if (trimmed.size() <= maxLength) {
        return trimmed;
    }
    return trimmed.left(maxLength - 1) + QStringLiteral("…");
}

QString enabledText(bool value) {
    return value ? QStringLiteral("已启用") : QStringLiteral("未启用");
}

QString secretStatus(const QString& value) {
    return value.trimmed().isEmpty() ? QStringLiteral("未配置") : QStringLiteral("已配置（已脱敏）");
}

QString rowText(const QString& label, const QString& value) {
    return label + QStringLiteral("：") + value;
}

QString rowText(const QString& label, int value) {
    return rowText(label, QString::number(value));
}

QString rowText(const QString& label, double value) {
    return rowText(label, QString::number(value, 'f', 2));
}

QJsonObject readJsonObject(const QDir& root, const QString& relativePath, QString* status) {
    QFile file(root.absoluteFilePath(relativePath));
    if (!file.exists()) {
        if (status) {
            *status = QStringLiteral("%1 缺失").arg(relativePath);
        }
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (status) {
            *status = QStringLiteral("%1 无法读取：%2").arg(relativePath, file.errorString());
        }
        return {};
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (status) {
            *status = QStringLiteral("%1 JSON 无效：%2").arg(relativePath, error.errorString());
        }
        return {};
    }

    if (status) {
        *status = QStringLiteral("%1 已读取").arg(relativePath);
    }
    return document.object();
}

QJsonArray readJsonArray(const QDir& root, const QString& relativePath, QString* status) {
    QFile file(root.absoluteFilePath(relativePath));
    if (!file.exists()) {
        if (status) {
            *status = QStringLiteral("%1 缺失").arg(relativePath);
        }
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (status) {
            *status = QStringLiteral("%1 无法读取：%2").arg(relativePath, file.errorString());
        }
        return {};
    }

    QJsonArray result;
    QString parseError;
    if (!parseJsonArrayPayload(file.readAll(), &result, &parseError)) {
        if (status) {
            *status = QStringLiteral("%1 %2").arg(relativePath, parseError);
        }
        return {};
    }

    if (status) {
        *status = QStringLiteral("%1 已读取").arg(relativePath);
    }
    return result;
}

bool isReadableJson(const QDir& root, const QString& relativePath, QString* errorMessage) {
    QFile file(root.absoluteFilePath(relativePath));
    if (!file.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("缺失");
        }
        return false;
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法读取：%1").arg(file.errorString());
        }
        return false;
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || document.isNull()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("JSON 无效：%1").arg(error.errorString());
        }
        return false;
    }
    return true;
}

int countFilesRecursively(const QDir& dir, const QStringList& nameFilters) {
    if (!dir.exists()) {
        return 0;
    }

    int count = 0;
    QDirIterator it(
        dir.absolutePath(),
        nameFilters,
        QDir::Files | QDir::NoSymLinks,
        QDirIterator::Subdirectories);
    while (it.hasNext()) {
        it.next();
        ++count;
    }
    return count;
}

int countEnabledFlags(const QJsonObject& object) {
    int count = 0;
    for (auto it = object.constBegin(); it != object.constEnd(); ++it) {
        if (it.value().toBool(false)) {
            ++count;
        }
    }
    return count;
}

double draftNumber(
    const QVariantMap& draft,
    const QString& key,
    double currentValue,
    double minValue,
    double maxValue) {
    if (!draft.contains(key)) {
        return currentValue;
    }

    bool ok = false;
    double value = draft.value(key).toDouble(&ok);
    if (!ok) {
        value = currentValue;
    }
    return qBound(minValue, value, maxValue);
}

int draftInt(
    const QVariantMap& draft,
    const QString& key,
    int currentValue,
    int minValue,
    int maxValue) {
    return static_cast<int>(qRound(draftNumber(draft, key, currentValue, minValue, maxValue)));
}

QString draftString(
    const QVariantMap& draft,
    const QString& key,
    const QString& currentValue,
    int maxLength = 4096) {
    if (!draft.contains(key)) {
        return currentValue;
    }

    QString value = draft.value(key).toString().trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength);
    }
    return value;
}

QString tagsTextFromArray(const QJsonArray& tags) {
    QStringList result;
    for (const QJsonValue& value : tags) {
        const QString tag = value.toString().trimmed();
        if (!tag.isEmpty()) {
            result.append(tag);
        }
    }
    return result.join(QStringLiteral(", "));
}

QJsonArray cardTagsFromDraft(const QVariantMap& draft, const QJsonArray& currentTags) {
    const QString source = draft.contains(QStringLiteral("tagsText"))
        ? draft.value(QStringLiteral("tagsText")).toString()
        : tagsTextFromArray(currentTags);
    const QStringList parts = source.split(QRegularExpression(QStringLiteral("[,，;；|/\\r\\n]+")), Qt::SkipEmptyParts);

    QStringList uniqueTags;
    for (QString tag : parts) {
        tag = tag.simplified();
        if (tag.size() > 80) {
            tag = tag.left(80).trimmed();
        }
        if (!tag.isEmpty() && !uniqueTags.contains(tag)) {
            uniqueTags.append(tag);
        }
        if (uniqueTags.size() >= 24) {
            break;
        }
    }

    QJsonArray result;
    for (const QString& tag : uniqueTags) {
        result.append(tag);
    }
    return result;
}

QString normalizedTheme(const QVariantMap& draft, const QJsonObject& settings) {
    const QString value = draftString(
        draft,
        QStringLiteral("theme"),
        settings.value("theme").toString(),
        64).toLower();
    return value == QStringLiteral("dark") ? QStringLiteral("dark") : QStringLiteral("light");
}

QString normalizedBackgroundPath(const QVariantMap& draft, const QJsonObject& settings) {
    QString value = draftString(
        draft,
        QStringLiteral("background_image_path"),
        settings.value("background_image_path").toString(),
        4096).trimmed();
    const QUrl url(value);
    if (url.isLocalFile()) {
        value = url.toLocalFile();
    }
    return QDir::fromNativeSeparators(value);
}

QString backgroundImageUrl(const QDir& root, const QString& path) {
    const QString trimmed = path.trimmed();
    if (trimmed.isEmpty()) {
        return {};
    }

    QFileInfo fileInfo(trimmed);
    if (fileInfo.isRelative()) {
        fileInfo.setFile(root.absoluteFilePath(trimmed));
    }
    if (!fileInfo.exists() || !fileInfo.isFile()) {
        return {};
    }
    return QUrl::fromLocalFile(fileInfo.absoluteFilePath()).toString();
}

QString normalizedSummaryLength(const QVariantMap& draft, const QJsonObject& settings) {
    const QString value = draftString(
        draft,
        QStringLiteral("memory_summary_length"),
        settings.value("memory_summary_length").toString(),
        64).toLower();
    if (value == QStringLiteral("short")
        || value == QStringLiteral("medium")
        || value == QStringLiteral("long")
        || value == QStringLiteral("custom")) {
        return value;
    }
    return QStringLiteral("medium");
}

QString normalizedRouteStrategy(const QVariantMap& draft, const QJsonObject& routes) {
    const QString value = draftString(
        draft,
        QStringLiteral("strategy"),
        routes.value("strategy").toString(),
        32).toLower();
    return value == QStringLiteral("round_robin") ? QStringLiteral("round_robin") : QStringLiteral("priority");
}

QString normalizedWorldbookMatchMode(
    const QVariantMap& draft,
    const QString& key,
    const QJsonObject& settings,
    const QString& defaultValue) {
    const QString currentValue = settings.value(key).toString(defaultValue);
    const QString value = (draft.contains(key)
            ? draftString(draft, key, currentValue, 32)
            : currentValue).toLower();
    return (value == QStringLiteral("any") || value == QStringLiteral("all")) ? value : defaultValue;
}

QString normalizedWorldbookEntryType(const QVariantMap& draft, const QJsonObject& settings) {
    const QString currentValue = settings.value(QStringLiteral("default_entry_type")).toString(QStringLiteral("keyword"));
    const QString value = (draft.contains(QStringLiteral("default_entry_type"))
            ? draftString(draft, QStringLiteral("default_entry_type"), currentValue, 32)
            : currentValue).toLower();
    if (value == QStringLiteral("keyword")
        || value == QStringLiteral("constant")
        || value == QStringLiteral("external_tag")) {
        return value;
    }
    return QStringLiteral("keyword");
}

QString normalizedWorldbookEntryTypeValue(const QString& value, const QString& defaultValue = QStringLiteral("keyword")) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("keyword")
        || normalized == QStringLiteral("constant")
        || normalized == QStringLiteral("external_tag")) {
        return normalized;
    }
    return defaultValue;
}

QString normalizedWorldbookMatchModeValue(const QString& value, const QString& defaultValue) {
    const QString normalized = value.trimmed().toLower();
    return (normalized == QStringLiteral("any") || normalized == QStringLiteral("all")) ? normalized : defaultValue;
}

QString normalizedWorldbookGroupOperator(const QVariantMap& draft, const QJsonObject& settings) {
    const QString currentValue = settings.value(QStringLiteral("default_group_operator")).toString(QStringLiteral("and"));
    const QString value = (draft.contains(QStringLiteral("default_group_operator"))
            ? draftString(draft, QStringLiteral("default_group_operator"), currentValue, 32)
            : currentValue).toLower();
    if (value == QStringLiteral("or") || value == QStringLiteral("any")) {
        return QStringLiteral("or");
    }
    return QStringLiteral("and");
}

QString normalizedWorldbookGroupOperatorValue(const QString& value, const QString& defaultValue = QStringLiteral("and")) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("or") || normalized == QStringLiteral("any")) {
        return QStringLiteral("or");
    }
    if (normalized == QStringLiteral("and") || normalized == QStringLiteral("all")) {
        return QStringLiteral("and");
    }
    return defaultValue;
}

QString normalizedWorldbookInsertionPosition(const QVariantMap& draft, const QJsonObject& settings) {
    const QString currentValue = settings.value(QStringLiteral("default_insertion_position")).toString(QStringLiteral("after_char_defs"));
    QString value = (draft.contains(QStringLiteral("default_insertion_position"))
            ? draftString(draft, QStringLiteral("default_insertion_position"), currentValue, 64)
            : currentValue).toLower();

    if (value == QStringLiteral("0")
        || value == QStringLiteral("before_character")
        || value == QStringLiteral("before_char")
        || value == QStringLiteral("character_before")) {
        value = QStringLiteral("before_char_defs");
    } else if (value == QStringLiteral("1")
        || value == QStringLiteral("after_character")
        || value == QStringLiteral("after_char")
        || value == QStringLiteral("character_after")) {
        value = QStringLiteral("after_char_defs");
    } else if (value == QStringLiteral("4")
        || value == QStringLiteral("depth")
        || value == QStringLiteral("at_depth")
        || value == QStringLiteral("in-chat")
        || value == QStringLiteral("inchat")) {
        value = QStringLiteral("in_chat");
    } else if (value == QStringLiteral("d_system")
        || value == QStringLiteral("depth_system")
        || value == QStringLiteral("at_depth_sys")) {
        value = QStringLiteral("at_depth_system");
    } else if (value == QStringLiteral("d_user") || value == QStringLiteral("depth_user")) {
        value = QStringLiteral("at_depth_user");
    } else if (value == QStringLiteral("d_ai")
        || value == QStringLiteral("d_assistant")
        || value == QStringLiteral("depth_ai")
        || value == QStringLiteral("depth_assistant")
        || value == QStringLiteral("assistant")
        || value == QStringLiteral("ai")) {
        value = QStringLiteral("at_depth_assistant");
    }

    const QStringList allowed = {
        QStringLiteral("before_char_defs"),
        QStringLiteral("after_char_defs"),
        QStringLiteral("in_chat"),
        QStringLiteral("at_depth_system"),
        QStringLiteral("at_depth_user"),
        QStringLiteral("at_depth_assistant"),
    };
    return allowed.contains(value) ? value : QStringLiteral("after_char_defs");
}

QString normalizedWorldbookInsertionPositionValue(const QString& value, const QString& defaultValue = QStringLiteral("after_char_defs")) {
    QVariantMap draft;
    draft.insert(QStringLiteral("default_insertion_position"), value);
    QJsonObject settings;
    settings.insert(QStringLiteral("default_insertion_position"), defaultValue);
    return normalizedWorldbookInsertionPosition(draft, settings);
}

QString normalizedWorldbookInjectionRole(const QVariantMap& draft, const QJsonObject& settings) {
    const QString currentValue = settings.value(QStringLiteral("default_injection_role")).toString(QStringLiteral("system"));
    QString value = (draft.contains(QStringLiteral("default_injection_role"))
            ? draftString(draft, QStringLiteral("default_injection_role"), currentValue, 32)
            : currentValue).toLower();
    if (value == QStringLiteral("0")) {
        value = QStringLiteral("system");
    } else if (value == QStringLiteral("1")) {
        value = QStringLiteral("user");
    } else if (value == QStringLiteral("2") || value == QStringLiteral("ai") || value == QStringLiteral("model")) {
        value = QStringLiteral("assistant");
    }
    if (value == QStringLiteral("system") || value == QStringLiteral("user") || value == QStringLiteral("assistant")) {
        return value;
    }
    return QStringLiteral("system");
}

QString normalizedWorldbookInjectionRoleValue(const QString& value, const QString& defaultValue = QStringLiteral("system")) {
    QVariantMap draft;
    draft.insert(QStringLiteral("default_injection_role"), value);
    QJsonObject settings;
    settings.insert(QStringLiteral("default_injection_role"), defaultValue);
    return normalizedWorldbookInjectionRole(draft, settings);
}

QString normalizedWorldbookPromptLayer(const QVariantMap& draft, const QJsonObject& settings) {
    const QString currentValue = settings.value(QStringLiteral("default_prompt_layer")).toString(QStringLiteral("follow_position"));
    const QString value = (draft.contains(QStringLiteral("default_prompt_layer"))
            ? draftString(draft, QStringLiteral("default_prompt_layer"), currentValue, 64)
            : currentValue).toLower();
    const QStringList allowed = {
        QStringLiteral("follow_position"),
        QStringLiteral("stable"),
        QStringLiteral("current_state"),
        QStringLiteral("dynamic"),
        QStringLiteral("output_guard"),
    };
    return allowed.contains(value) ? value : QStringLiteral("follow_position");
}

QString normalizedWorldbookPromptLayerValue(const QString& value, const QString& defaultValue = QStringLiteral("follow_position")) {
    QVariantMap draft;
    draft.insert(QStringLiteral("default_prompt_layer"), value);
    QJsonObject settings;
    settings.insert(QStringLiteral("default_prompt_layer"), defaultValue);
    return normalizedWorldbookPromptLayer(draft, settings);
}

QVariantMap worldbookEntryToVariant(const QJsonObject& entry, int index, const QJsonObject& settings) {
    const QString defaultEntryType = normalizedWorldbookEntryType(QVariantMap{}, settings);
    const QString defaultMatchMode = settings.value(QStringLiteral("default_match_mode")).toString(QStringLiteral("any"));
    const QString defaultSecondaryMode = settings.value(QStringLiteral("default_secondary_mode")).toString(QStringLiteral("all"));
    const QString defaultGroupOperator = normalizedWorldbookGroupOperator(QVariantMap{}, settings);
    const QString defaultInsertionPosition = normalizedWorldbookInsertionPosition(QVariantMap{}, settings);
    const QString defaultInjectionRole = normalizedWorldbookInjectionRole(QVariantMap{}, settings);
    const QString defaultPromptLayer = normalizedWorldbookPromptLayer(QVariantMap{}, settings);

    QVariantMap item;
    item.insert(QStringLiteral("index"), index);
    item.insert(QStringLiteral("id"), entry.value(QStringLiteral("id")).toString());
    item.insert(QStringLiteral("title"), displayText(entry.value(QStringLiteral("title")).toString(), QStringLiteral("词条 %1").arg(index + 1)));
    item.insert(QStringLiteral("trigger"), entry.value(QStringLiteral("trigger")).toString());
    item.insert(QStringLiteral("secondary_trigger"), entry.value(QStringLiteral("secondary_trigger")).toString());
    item.insert(QStringLiteral("entry_type"), normalizedWorldbookEntryTypeValue(entry.value(QStringLiteral("entry_type")).toString(defaultEntryType), defaultEntryType));
    item.insert(QStringLiteral("group_operator"), normalizedWorldbookGroupOperatorValue(entry.value(QStringLiteral("group_operator")).toString(defaultGroupOperator), defaultGroupOperator));
    item.insert(QStringLiteral("match_mode"), normalizedWorldbookMatchModeValue(entry.value(QStringLiteral("match_mode")).toString(defaultMatchMode), defaultMatchMode));
    item.insert(QStringLiteral("secondary_mode"), normalizedWorldbookMatchModeValue(entry.value(QStringLiteral("secondary_mode")).toString(defaultSecondaryMode), defaultSecondaryMode));
    item.insert(QStringLiteral("content"), entry.value(QStringLiteral("content")).toString());
    item.insert(QStringLiteral("group"), entry.value(QStringLiteral("group")).toString());
    item.insert(QStringLiteral("chance"), qBound(0, entry.value(QStringLiteral("chance")).toInt(settings.value(QStringLiteral("default_chance")).toInt(100)), 100));
    item.insert(QStringLiteral("sticky_turns"), qBound(0, entry.value(QStringLiteral("sticky_turns")).toInt(settings.value(QStringLiteral("default_sticky_turns")).toInt(0)), 999));
    item.insert(QStringLiteral("cooldown_turns"), qBound(0, entry.value(QStringLiteral("cooldown_turns")).toInt(settings.value(QStringLiteral("default_cooldown_turns")).toInt(0)), 999));
    item.insert(QStringLiteral("order"), qBound(0, entry.value(QStringLiteral("order")).toInt(entry.value(QStringLiteral("priority")).toInt(100)), 999999));
    item.insert(QStringLiteral("insertion_position"), normalizedWorldbookInsertionPositionValue(entry.value(QStringLiteral("insertion_position")).toString(defaultInsertionPosition), defaultInsertionPosition));
    item.insert(QStringLiteral("injection_depth"), qBound(0, entry.value(QStringLiteral("injection_depth")).toInt(settings.value(QStringLiteral("default_injection_depth")).toInt(0)), 999));
    item.insert(QStringLiteral("injection_role"), normalizedWorldbookInjectionRoleValue(entry.value(QStringLiteral("injection_role")).toString(defaultInjectionRole), defaultInjectionRole));
    item.insert(QStringLiteral("injection_order"), qBound(0, entry.value(QStringLiteral("injection_order")).toInt(entry.value(QStringLiteral("order")).toInt(settings.value(QStringLiteral("default_injection_order")).toInt(100))), 999999));
    item.insert(QStringLiteral("prompt_layer"), normalizedWorldbookPromptLayerValue(entry.value(QStringLiteral("prompt_layer")).toString(defaultPromptLayer), defaultPromptLayer));
    item.insert(QStringLiteral("recursive_enabled"), entry.value(QStringLiteral("recursive_enabled")).toBool(true));
    item.insert(QStringLiteral("prevent_further_recursion"), entry.value(QStringLiteral("prevent_further_recursion")).toBool(false));
    item.insert(QStringLiteral("enabled"), entry.value(QStringLiteral("enabled")).toBool(true));
    item.insert(QStringLiteral("case_sensitive"), entry.value(QStringLiteral("case_sensitive")).toBool(settings.value(QStringLiteral("default_case_sensitive")).toBool(false)));
    item.insert(QStringLiteral("whole_word"), entry.value(QStringLiteral("whole_word")).toBool(settings.value(QStringLiteral("default_whole_word")).toBool(false)));
    item.insert(QStringLiteral("comment"), entry.value(QStringLiteral("comment")).toString());
    item.insert(QStringLiteral("preview"), clippedText(entry.value(QStringLiteral("content")).toString(), 180));
    return item;
}

QVariantList worldbookEntriesToVariant(const QJsonArray& entries, const QJsonObject& settings) {
    QVariantList result;
    for (int i = 0; i < entries.size(); ++i) {
        const QJsonObject entry = entries.at(i).toObject();
        if (!entry.isEmpty()) {
            result.append(worldbookEntryToVariant(entry, i, settings));
        }
    }
    return result;
}

QString worldbookEntryDraftString(
    const QVariantMap& draft,
    const QString& key,
    const QJsonObject& current,
    const QString& defaultValue,
    int maxLength) {
    QString value = draft.contains(key) ? draft.value(key).toString().trimmed() : current.value(key).toString(defaultValue).trimmed();
    value.replace(QLatin1Char('\r'), QLatin1Char('\n'));
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QJsonObject sanitizedWorldbookEntryFromDraft(
    const QVariantMap& draft,
    const QJsonObject& current,
    const QJsonObject& settings,
    int index,
    bool isNewEntry,
    QString* errorMessage) {
    QJsonObject entry = current;
    const QString defaultEntryType = normalizedWorldbookEntryType(QVariantMap{}, settings);
    const QString defaultMatchMode = settings.value(QStringLiteral("default_match_mode")).toString(QStringLiteral("any"));
    const QString defaultSecondaryMode = settings.value(QStringLiteral("default_secondary_mode")).toString(QStringLiteral("all"));
    const QString defaultGroupOperator = normalizedWorldbookGroupOperator(QVariantMap{}, settings);
    const QString defaultInsertionPosition = normalizedWorldbookInsertionPosition(QVariantMap{}, settings);
    const QString defaultInjectionRole = normalizedWorldbookInjectionRole(QVariantMap{}, settings);
    const QString defaultPromptLayer = normalizedWorldbookPromptLayer(QVariantMap{}, settings);

    if (isNewEntry || !entry.contains(QStringLiteral("id"))) {
        entry.insert(QStringLiteral("id"), QStringLiteral("worldbook-huskarui-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces)));
    }

    const QString title = displayText(
        worldbookEntryDraftString(draft, QStringLiteral("title"), entry, QStringLiteral("词条 %1").arg(index + 1), 80),
        QStringLiteral("词条 %1").arg(index + 1));
    const QString content = worldbookEntryDraftString(draft, QStringLiteral("content"), entry, QString(), 12000);
    const QString trigger = worldbookEntryDraftString(draft, QStringLiteral("trigger"), entry, QString(), 1200);
    const QString secondaryTrigger = worldbookEntryDraftString(draft, QStringLiteral("secondary_trigger"), entry, QString(), 1200);
    const QString entryType = normalizedWorldbookEntryTypeValue(
        worldbookEntryDraftString(draft, QStringLiteral("entry_type"), entry, defaultEntryType, 32),
        defaultEntryType);

    if (content.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("世界书词条内容不能为空");
        }
        return {};
    }
    if (entryType == QStringLiteral("keyword") && trigger.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("keyword 世界书词条必须填写主触发词");
        }
        return {};
    }

    const QString insertionPosition = normalizedWorldbookInsertionPositionValue(
        worldbookEntryDraftString(draft, QStringLiteral("insertion_position"), entry, defaultInsertionPosition, 64),
        defaultInsertionPosition);
    QString injectionRole = normalizedWorldbookInjectionRoleValue(
        worldbookEntryDraftString(draft, QStringLiteral("injection_role"), entry, defaultInjectionRole, 32),
        defaultInjectionRole);
    if (insertionPosition == QStringLiteral("at_depth_system")) {
        injectionRole = QStringLiteral("system");
    } else if (insertionPosition == QStringLiteral("at_depth_user")) {
        injectionRole = QStringLiteral("user");
    } else if (insertionPosition == QStringLiteral("at_depth_assistant")) {
        injectionRole = QStringLiteral("assistant");
    }

    const int currentOrder = entry.value(QStringLiteral("order")).toInt(entry.value(QStringLiteral("priority")).toInt(100));
    const int order = draftInt(draft, QStringLiteral("order"), currentOrder, 0, 999999);
    entry.insert(QStringLiteral("title"), title);
    entry.insert(QStringLiteral("trigger"), trigger);
    entry.insert(QStringLiteral("secondary_trigger"), secondaryTrigger);
    entry.insert(QStringLiteral("entry_type"), entryType);
    entry.insert(QStringLiteral("group_operator"), normalizedWorldbookGroupOperatorValue(
        worldbookEntryDraftString(draft, QStringLiteral("group_operator"), entry, defaultGroupOperator, 32),
        defaultGroupOperator));
    entry.insert(QStringLiteral("match_mode"), normalizedWorldbookMatchModeValue(
        worldbookEntryDraftString(draft, QStringLiteral("match_mode"), entry, defaultMatchMode, 32),
        defaultMatchMode));
    entry.insert(QStringLiteral("secondary_mode"), normalizedWorldbookMatchModeValue(
        worldbookEntryDraftString(draft, QStringLiteral("secondary_mode"), entry, defaultSecondaryMode, 32),
        defaultSecondaryMode));
    entry.insert(QStringLiteral("content"), content);
    entry.insert(QStringLiteral("group"), worldbookEntryDraftString(draft, QStringLiteral("group"), entry, QString(), 80));
    entry.insert(QStringLiteral("chance"),
        draftInt(draft, QStringLiteral("chance"), entry.value(QStringLiteral("chance")).toInt(settings.value(QStringLiteral("default_chance")).toInt(100)), 0, 100));
    entry.insert(QStringLiteral("sticky_turns"),
        draftInt(draft, QStringLiteral("sticky_turns"), entry.value(QStringLiteral("sticky_turns")).toInt(settings.value(QStringLiteral("default_sticky_turns")).toInt(0)), 0, 999));
    entry.insert(QStringLiteral("cooldown_turns"),
        draftInt(draft, QStringLiteral("cooldown_turns"), entry.value(QStringLiteral("cooldown_turns")).toInt(settings.value(QStringLiteral("default_cooldown_turns")).toInt(0)), 0, 999));
    entry.insert(QStringLiteral("order"), order);
    entry.insert(QStringLiteral("priority"), order);
    entry.insert(QStringLiteral("insertion_position"), insertionPosition);
    entry.insert(QStringLiteral("injection_depth"),
        draftInt(draft, QStringLiteral("injection_depth"), entry.value(QStringLiteral("injection_depth")).toInt(settings.value(QStringLiteral("default_injection_depth")).toInt(0)), 0, 999));
    entry.insert(QStringLiteral("injection_role"), injectionRole);
    entry.insert(QStringLiteral("injection_order"),
        draftInt(draft, QStringLiteral("injection_order"), entry.value(QStringLiteral("injection_order")).toInt(order), 0, 999999));
    entry.insert(QStringLiteral("prompt_layer"), normalizedWorldbookPromptLayerValue(
        worldbookEntryDraftString(draft, QStringLiteral("prompt_layer"), entry, defaultPromptLayer, 64),
        defaultPromptLayer));
    entry.insert(QStringLiteral("recursive_enabled"),
        draft.value(QStringLiteral("recursive_enabled"), entry.value(QStringLiteral("recursive_enabled")).toBool(true)).toBool());
    entry.insert(QStringLiteral("prevent_further_recursion"),
        draft.value(QStringLiteral("prevent_further_recursion"), entry.value(QStringLiteral("prevent_further_recursion")).toBool(false)).toBool());
    entry.insert(QStringLiteral("enabled"),
        draft.value(QStringLiteral("enabled"), entry.value(QStringLiteral("enabled")).toBool(true)).toBool());
    entry.insert(QStringLiteral("case_sensitive"),
        draft.value(QStringLiteral("case_sensitive"), entry.value(QStringLiteral("case_sensitive")).toBool(settings.value(QStringLiteral("default_case_sensitive")).toBool(false))).toBool());
    entry.insert(QStringLiteral("whole_word"),
        draft.value(QStringLiteral("whole_word"), entry.value(QStringLiteral("whole_word")).toBool(settings.value(QStringLiteral("default_whole_word")).toBool(false))).toBool());
    entry.insert(QStringLiteral("comment"), worldbookEntryDraftString(draft, QStringLiteral("comment"), entry, QString(), 240));
    return entry;
}

QJsonObject defaultWorldbookSettings() {
    QJsonObject settings;
    settings.insert(QStringLiteral("enabled"), true);
    settings.insert(QStringLiteral("debug_enabled"), false);
    settings.insert(QStringLiteral("max_hits"), 3);
    settings.insert(QStringLiteral("default_case_sensitive"), false);
    settings.insert(QStringLiteral("default_whole_word"), false);
    settings.insert(QStringLiteral("default_match_mode"), QStringLiteral("any"));
    settings.insert(QStringLiteral("default_secondary_mode"), QStringLiteral("all"));
    settings.insert(QStringLiteral("default_entry_type"), QStringLiteral("keyword"));
    settings.insert(QStringLiteral("default_group_operator"), QStringLiteral("and"));
    settings.insert(QStringLiteral("default_chance"), 100);
    settings.insert(QStringLiteral("default_sticky_turns"), 0);
    settings.insert(QStringLiteral("default_cooldown_turns"), 0);
    settings.insert(QStringLiteral("default_insertion_position"), QStringLiteral("after_char_defs"));
    settings.insert(QStringLiteral("default_injection_depth"), 0);
    settings.insert(QStringLiteral("default_injection_role"), QStringLiteral("system"));
    settings.insert(QStringLiteral("default_injection_order"), 100);
    settings.insert(QStringLiteral("default_prompt_layer"), QStringLiteral("follow_position"));
    settings.insert(QStringLiteral("recursive_scan_enabled"), false);
    settings.insert(QStringLiteral("recursion_max_depth"), 2);
    return settings;
}

QJsonArray worldbookEntriesFromImportValue(const QJsonValue& value, const QJsonObject& settings) {
    QJsonArray rawEntries;
    if (value.isArray()) {
        rawEntries = value.toArray();
    } else if (value.isObject()) {
        const QJsonObject map = value.toObject();
        for (auto it = map.constBegin(); it != map.constEnd(); ++it) {
            if (it.value().isObject()) {
                QJsonObject entry = it.value().toObject();
                if (entry.value(QStringLiteral("title")).toString().trimmed().isEmpty()) {
                    entry.insert(QStringLiteral("title"), it.key());
                }
                if (entry.value(QStringLiteral("trigger")).toString().trimmed().isEmpty()) {
                    entry.insert(QStringLiteral("trigger"), it.key());
                }
                rawEntries.append(entry);
            } else {
                rawEntries.append(QJsonObject{
                    { QStringLiteral("title"), it.key() },
                    { QStringLiteral("trigger"), it.key() },
                    { QStringLiteral("content"), it.value().toString() },
                    { QStringLiteral("entry_type"), QStringLiteral("keyword") },
                });
            }
        }
    }

    QJsonArray result;
    for (int i = 0; i < rawEntries.size(); ++i) {
        if (!rawEntries.at(i).isObject()) {
            continue;
        }
        QJsonObject rawEntry = rawEntries.at(i).toObject();
        if (rawEntry.value(QStringLiteral("content")).toString().trimmed().isEmpty()) {
            continue;
        }
        if (rawEntry.value(QStringLiteral("title")).toString().trimmed().isEmpty()) {
            rawEntry.insert(QStringLiteral("title"), QStringLiteral("词条 %1").arg(result.size() + 1));
        }
        if (rawEntry.value(QStringLiteral("trigger")).toString().trimmed().isEmpty()
            && rawEntry.value(QStringLiteral("entry_type")).toString().trimmed().isEmpty()) {
            rawEntry.insert(QStringLiteral("entry_type"), QStringLiteral("constant"));
        }

        QString error;
        const QJsonObject sanitized = sanitizedWorldbookEntryFromDraft(
            rawEntry.toVariantMap(),
            QJsonObject{},
            settings,
            result.size(),
            true,
            &error);
        if (!sanitized.isEmpty()) {
            result.append(sanitized);
        }
    }
    return result;
}

QJsonObject importedWorldbookStore(
    const QJsonDocument& document,
    const QJsonObject& currentStore,
    QString* errorMessage) {
    if (!document.isObject() && !document.isArray()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("世界书导入文件必须是 JSON 对象或数组");
        }
        return {};
    }

    QJsonValue rawStore = document.isArray() ? QJsonValue(document.array()) : QJsonValue(document.object());
    if (rawStore.isObject()) {
        const QJsonObject object = rawStore.toObject();
        if (object.value(QStringLiteral("worldbook")).isObject()) {
            rawStore = object.value(QStringLiteral("worldbook"));
        }
    }

    const QJsonObject currentSettings = currentStore.value(QStringLiteral("settings")).toObject(defaultWorldbookSettings());
    QJsonObject settings = currentSettings.isEmpty() ? defaultWorldbookSettings() : currentSettings;
    QJsonValue entrySource;
    if (rawStore.isArray()) {
        entrySource = rawStore;
    } else if (rawStore.isObject()) {
        const QJsonObject object = rawStore.toObject();
        if (object.value(QStringLiteral("settings")).isObject()) {
            settings = object.value(QStringLiteral("settings")).toObject();
        }
        if (object.contains(QStringLiteral("entries"))) {
            entrySource = object.value(QStringLiteral("entries"));
        } else if (object.contains(QStringLiteral("items"))) {
            entrySource = object.value(QStringLiteral("items"));
        } else {
            entrySource = object;
        }
    }

    if (settings.isEmpty()) {
        settings = defaultWorldbookSettings();
    }
    const QJsonArray entries = worldbookEntriesFromImportValue(entrySource, settings);
    if (entries.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("未找到有效世界书词条");
        }
        return {};
    }

    QJsonObject result = currentStore;
    result.insert(QStringLiteral("settings"), settings);
    result.insert(QStringLiteral("entries"), entries);
    return result;
}

QVariantList routeProvidersToVariant(const QJsonArray& providers) {
    QVariantList result;
    for (int i = 0; i < providers.size(); ++i) {
        const QJsonObject provider = providers.at(i).toObject();
        if (provider.isEmpty()) {
            continue;
        }

        const QJsonArray keys = provider.value(QStringLiteral("keys")).toArray();
        int keyCount = 0;
        for (const QJsonValue& key : keys) {
            if (!key.toString().trimmed().isEmpty()) {
                ++keyCount;
            }
        }
        if (!provider.value(QStringLiteral("api_key")).toString().trimmed().isEmpty()) {
            ++keyCount;
        }

        QVariantMap item;
        item.insert(QStringLiteral("index"), i);
        item.insert(QStringLiteral("id"), provider.value(QStringLiteral("id")).toString(QStringLiteral("provider-%1").arg(i + 1)));
        item.insert(QStringLiteral("name"), displayText(provider.value(QStringLiteral("name")).toString(), QStringLiteral("Provider %1").arg(i + 1)));
        item.insert(QStringLiteral("base_url"), provider.value(QStringLiteral("base_url")).toString());
        item.insert(QStringLiteral("model"), provider.value(QStringLiteral("model")).toString());
        item.insert(QStringLiteral("enabled"), provider.value(QStringLiteral("enabled")).toBool(true));
        item.insert(QStringLiteral("priority"), provider.value(QStringLiteral("priority")).toInt(i + 1));
        item.insert(QStringLiteral("weight"), provider.value(QStringLiteral("weight")).toInt(1));
        item.insert(QStringLiteral("keyCount"), keyCount);
        item.insert(QStringLiteral("keyStatus"), keyCount > 0 ? QStringLiteral("已配置 %1 个 Key（已脱敏）").arg(keyCount) : QStringLiteral("未配置 Key"));
        result.append(item);
    }
    return result;
}

QString routeProviderDraftString(
    const QVariantMap& draft,
    const QString& key,
    const QJsonObject& current,
    const QString& defaultValue,
    int maxLength) {
    QString value = draft.contains(key) ? draft.value(key).toString().trimmed() : current.value(key).toString(defaultValue).trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QString normalizedRouteProviderId(QString value) {
    value = value.trimmed().toLower();
    value.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("-"));
    value.replace(QRegularExpression(QStringLiteral("[^a-z0-9_\\-]+")), QString());
    value.replace(QRegularExpression(QStringLiteral("[_\\-]{2,}")), QStringLiteral("-"));
    while (value.startsWith(QLatin1Char('_')) || value.startsWith(QLatin1Char('-'))) {
        value.remove(0, 1);
    }
    while (value.endsWith(QLatin1Char('_')) || value.endsWith(QLatin1Char('-'))) {
        value.chop(1);
    }
    return value;
}

QJsonObject sanitizedRouteProviderFromDraft(
    const QVariantMap& draft,
    const QJsonObject& current,
    int index,
    bool isNewProvider,
    QString* errorMessage) {
    QJsonObject provider = current;
    QString id = normalizedRouteProviderId(routeProviderDraftString(draft, QStringLiteral("id"), provider, QString(), 80));
    if (id.isEmpty()) {
        id = isNewProvider || !provider.contains(QStringLiteral("id"))
            ? QStringLiteral("provider-huskarui-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces))
            : normalizedRouteProviderId(provider.value(QStringLiteral("id")).toString());
    }
    if (id.isEmpty()) {
        id = QStringLiteral("provider-%1").arg(index + 1);
    }

    const QString name = displayText(
        routeProviderDraftString(draft, QStringLiteral("name"), provider, QStringLiteral("Provider %1").arg(index + 1), 120),
        QStringLiteral("Provider %1").arg(index + 1));
    const QString baseUrl = routeProviderDraftString(draft, QStringLiteral("base_url"), provider, QString(), 2048);
    const QString model = routeProviderDraftString(draft, QStringLiteral("model"), provider, QString(), 240);
    const bool enabled = draft.value(QStringLiteral("enabled"), provider.value(QStringLiteral("enabled")).toBool(true)).toBool();
    if (enabled && baseUrl.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("启用的 Provider 必须填写 Base URL");
        }
        return {};
    }
    if (enabled && model.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("启用的 Provider 必须填写模型名");
        }
        return {};
    }

    provider.insert(QStringLiteral("id"), id);
    provider.insert(QStringLiteral("name"), name);
    provider.insert(QStringLiteral("base_url"), baseUrl);
    provider.insert(QStringLiteral("model"), model);
    provider.insert(QStringLiteral("enabled"), enabled);
    provider.insert(QStringLiteral("priority"),
        draftInt(draft, QStringLiteral("priority"), provider.value(QStringLiteral("priority")).toInt(index + 1), 1, 999));
    provider.insert(QStringLiteral("weight"),
        draftInt(draft, QStringLiteral("weight"), provider.value(QStringLiteral("weight")).toInt(1), 1, 999));
    return provider;
}

void setSecretIfProvided(QJsonObject* settings, const QVariantMap& draft, const QString& key) {
    if (!settings || !draft.contains(key)) {
        return;
    }

    const QString value = draft.value(key).toString().trimmed();
    if (!value.isEmpty()) {
        settings->insert(key, value);
    }
}

struct PresetModuleMeta {
    const char* key;
    const char* label;
    const char* description;
    bool defaultEnabled;
    bool runtimeOnly;
};

const QList<PresetModuleMeta>& presetModuleMetas() {
    static const QList<PresetModuleMeta> metas = {
        { "no_user_speaking", "防抢话", "禁止替用户补写动作、台词、心理和决定。", true, false },
        { "short_paragraph", "短段落模式", "每个自然段尽量控制在 1-2 句，对白单独成段。", false, false },
        { "long_paragraph", "长段落模式", "回复更充实，保留动作、观察、情绪和环境细节。", false, false },
        { "second_person", "第二人称", "涉及用户时使用“你”。", false, false },
        { "third_person", "第三人称", "涉及用户时改用第三人称描述。", false, false },
        { "anti_repeat", "抗重复", "减少重复桥段、句式、修辞和收尾方式。", true, false },
        { "no_closing_feel", "避免强收尾感", "结尾停在仍可继续互动的位置。", true, false },
        { "emotion_detail", "情绪细节", "通过眼神、停顿、呼吸、动作和语气承接情绪。", true, false },
        { "multi_character_boundary", "多角色边界", "多角色同场时保持独立性格、语气和立场。", true, false },
        { "scene_continuation", "场景延续", "承接上一轮动作、情绪和空间位置，不突然重开场。", true, false },
        { "anti_horny", "抗发情", "用信任门控和行为审查约束高风险亲密推进。", false, false },
        { "anti_deification", "抗神化", "维持世界自主性、NPC 动机和有限视角。", false, false },
        { "v4f_output_guard", "V4F 稳定器", "运行时近端约束，用于稳定格式、防抢话和弱收尾。", false, true },
    };
    return metas;
}

bool isKnownPresetModule(const QString& key) {
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        if (key == QLatin1String(meta.key)) {
            return true;
        }
    }
    return false;
}

bool presetModuleDefault(const QString& key) {
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        if (key == QLatin1String(meta.key)) {
            return meta.defaultEnabled;
        }
    }
    return false;
}

void applyPresetModuleMutex(QJsonObject* modules) {
    if (!modules) {
        return;
    }

    if (modules->value(QStringLiteral("short_paragraph")).toBool(false)) {
        modules->insert(QStringLiteral("long_paragraph"), false);
    }
    if (modules->value(QStringLiteral("long_paragraph")).toBool(false)) {
        modules->insert(QStringLiteral("short_paragraph"), false);
    }
    if (modules->value(QStringLiteral("second_person")).toBool(false)) {
        modules->insert(QStringLiteral("third_person"), false);
    }
    if (modules->value(QStringLiteral("third_person")).toBool(false)) {
        modules->insert(QStringLiteral("second_person"), false);
    }
}

QVariantMap presetModulesToVariant(const QJsonObject& modules) {
    QVariantMap result;
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        const QString key = QLatin1String(meta.key);
        result.insert(key, modules.value(key).toBool(meta.defaultEnabled));
    }
    return result;
}

QVariantList presetModuleItemsToVariant(const QJsonObject& modules) {
    QVariantList result;
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        const QString key = QLatin1String(meta.key);
        QVariantMap item;
        item.insert(QStringLiteral("key"), key);
        item.insert(QStringLiteral("label"), QString::fromUtf8(meta.label));
        item.insert(QStringLiteral("description"), QString::fromUtf8(meta.description));
        item.insert(QStringLiteral("enabled"), modules.value(key).toBool(meta.defaultEnabled));
        item.insert(QStringLiteral("runtimeOnly"), meta.runtimeOnly);
        result.append(item);
    }
    return result;
}

int findActivePresetIndex(const QJsonArray& presets, const QString& activePresetId) {
    for (int i = 0; i < presets.size(); ++i) {
        if (presets.at(i).toObject().value(QStringLiteral("id")).toString() == activePresetId) {
            return i;
        }
    }
    return presets.isEmpty() ? -1 : 0;
}

QVariantMap resultMap(bool ok, const QString& message, const QString& backupPath = {}) {
    QVariantMap result;
    result.insert(QStringLiteral("ok"), ok);
    result.insert(QStringLiteral("message"), message);
    result.insert(QStringLiteral("backupPath"), backupPath);
    return result;
}

QString normalizedOutputPart(QString text) {
    text.replace(QLatin1Char('\r'), QLatin1Char('\n'));
    text = text.trimmed();
    while (text.contains(QStringLiteral("\n\n\n"))) {
        text.replace(QStringLiteral("\n\n\n"), QStringLiteral("\n\n"));
    }
    return text;
}

QStringList fallbackOutputParts(const QString& rawOutput) {
    const QString text = normalizedOutputPart(rawOutput);
    return text.isEmpty() ? QStringList{} : QStringList{ text };
}

bool isOutputSentenceTerminator(QChar ch) {
    const ushort code = ch.unicode();
    return ch == QLatin1Char('.')
        || ch == QLatin1Char('!')
        || ch == QLatin1Char('?')
        || ch == QLatin1Char(';')
        || code == 0x3002
        || code == 0xff01
        || code == 0xff1f
        || code == 0xff1b;
}

bool isOutputSoftBreak(QChar ch) {
    const ushort code = ch.unicode();
    return ch == QLatin1Char(',')
        || ch == QLatin1Char(' ')
        || code == 0x3001
        || code == 0xff0c;
}

bool isOutputClosingQuote(QChar ch) {
    const ushort code = ch.unicode();
    return ch == QLatin1Char('"')
        || ch == QLatin1Char('\'')
        || ch == QLatin1Char(')')
        || ch == QLatin1Char(']')
        || code == 0x201d
        || code == 0x2019
        || code == 0x300d
        || code == 0x300f;
}

bool looksLikeOutputStatusLine(const QString& text) {
    const QString trimmed = text.trimmed();
    if (trimmed.size() < 3) {
        return false;
    }

    const bool wrapped = (trimmed.startsWith(QLatin1Char('{')) && trimmed.endsWith(QLatin1Char('}')))
        || (trimmed.startsWith(QLatin1Char('[')) && trimmed.endsWith(QLatin1Char(']')));
    return wrapped && (trimmed.contains(QLatin1Char(':')) || trimmed.contains(QChar(0xff1a)));
}

void appendClampedOutputPart(QStringList* result, QString text) {
    text = normalizedOutputPart(text);
    if (text.isEmpty() || looksLikeOutputStatusLine(text)) {
        return;
    }

    constexpr qsizetype kMaxBubbleChars = 260;
    constexpr qsizetype kMinSoftBreakChars = 90;
    while (text.size() > kMaxBubbleChars) {
        qsizetype cut = -1;
        const qsizetype limit = qMin(kMaxBubbleChars, text.size());
        for (qsizetype i = limit - 1; i >= kMinSoftBreakChars; --i) {
            if (isOutputSoftBreak(text.at(i))) {
                cut = i;
                break;
            }
        }
        if (cut < 0) {
            cut = limit;
        }

        const QString head = normalizedOutputPart(text.left(cut + 1));
        if (!head.isEmpty()) {
            result->append(head);
        }
        text = normalizedOutputPart(text.mid(cut + 1));
    }

    if (!text.isEmpty()) {
        result->append(text);
    }
}

void appendLocalOutputBubbleParts(QStringList* result, const QString& source) {
    const QStringList lines = normalizedOutputPart(source).split(QRegularExpression(QStringLiteral("\\n+")), Qt::SkipEmptyParts);
    for (QString line : lines) {
        line = normalizedOutputPart(line);
        if (line.isEmpty() || looksLikeOutputStatusLine(line)) {
            continue;
        }

        QString sentence;
        for (qsizetype i = 0; i < line.size(); ++i) {
            const QChar ch = line.at(i);
            sentence.append(ch);
            if (isOutputSentenceTerminator(ch)) {
                while (i + 1 < line.size() && isOutputClosingQuote(line.at(i + 1))) {
                    ++i;
                    sentence.append(line.at(i));
                }
                appendClampedOutputPart(result, sentence);
                sentence.clear();
            }
        }
        appendClampedOutputPart(result, sentence);
    }
}

QStringList localOutputBubbleParts(const QString& rawOutput) {
    const QString text = normalizedOutputPart(rawOutput);
    if (text.isEmpty()) {
        return {};
    }

    QStringList result;
    const QStringList blocks = text.split(QRegularExpression(QStringLiteral("\\n\\s*\\n+")), Qt::SkipEmptyParts);
    for (const QString& block : blocks) {
        appendLocalOutputBubbleParts(&result, block);
    }

    if (result.isEmpty()) {
        return fallbackOutputParts(rawOutput);
    }
    return result;
}

QStringList refinedOutputBubbleParts(const QStringList& parts) {
    QStringList result;
    for (const QString& part : parts) {
        const QString text = normalizedOutputPart(part);
        if (text.isEmpty()) {
            continue;
        }

        const QStringList localParts = localOutputBubbleParts(text);
        if (localParts.size() > 1) {
            result.append(localParts);
        } else if (!localParts.isEmpty()) {
            result.append(localParts.first());
        }
    }
    return result;
}

QJsonArray outputPartsToJsonArray(const QStringList& parts) {
    QJsonArray result;
    for (const QString& part : parts) {
        const QString text = normalizedOutputPart(part);
        if (!text.isEmpty()) {
            result.append(text);
        }
    }
    return result;
}

QStringList outputPartsFromJsonArray(const QJsonArray& array) {
    QStringList result;
    for (const QJsonValue& value : array) {
        if (value.isString()) {
            const QString text = normalizedOutputPart(value.toString());
            if (!text.isEmpty()) {
                result.append(text);
            }
        }
    }
    return result;
}

QString stripJsonCodeFence(QString text) {
    text = text.trimmed();
    if (!text.startsWith(QStringLiteral("```"))) {
        return text;
    }

    const int firstLineEnd = text.indexOf(QLatin1Char('\n'));
    const int lastFence = text.lastIndexOf(QStringLiteral("```"));
    if (firstLineEnd >= 0 && lastFence > firstLineEnd) {
        return text.mid(firstLineEnd + 1, lastFence - firstLineEnd - 1).trimmed();
    }
    return text;
}

QStringList parseOutputSplitterJson(const QString& rawJson, QString* errorMessage = nullptr) {
    const QString stripped = stripJsonCodeFence(rawJson);
    QStringList candidates{ stripped };
    const int arrayStart = stripped.indexOf(QLatin1Char('['));
    const int arrayEnd = stripped.lastIndexOf(QLatin1Char(']'));
    if (arrayStart >= 0 && arrayEnd > arrayStart) {
        const QString extracted = stripped.mid(arrayStart, arrayEnd - arrayStart + 1).trimmed();
        if (extracted != stripped) {
            candidates.append(extracted);
        }
    }

    QString lastError;
    for (const QString& candidate : candidates) {
        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(candidate.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError) {
            lastError = parseError.errorString();
            continue;
        }

        QJsonArray array;
        if (document.isArray()) {
            array = document.array();
        } else if (document.isObject()) {
            const QJsonObject object = document.object();
            array = object.value(QStringLiteral("parts")).toArray();
            if (array.isEmpty()) {
                array = object.value(QStringLiteral("bubbles")).toArray();
            }
        }

        QStringList parts = outputPartsFromJsonArray(array);
        if (!parts.isEmpty()) {
            return parts;
        }
        lastError = QStringLiteral("JSON 不是非空字符串数组");
    }

    if (errorMessage) {
        *errorMessage = lastError.isEmpty() ? QStringLiteral("子代理输出不是合法 JSON 数组") : lastError;
    }
    return {};
}

bool outputPartsPreserveRawText(const QString& rawOutput, const QStringList& parts) {
    const QString raw = rawOutput.trimmed();
    qsizetype searchFrom = 0;
    for (const QString& part : parts) {
        const QString text = normalizedOutputPart(part);
        if (text.isEmpty()) {
            continue;
        }
        const qsizetype foundAt = raw.indexOf(text, searchFrom);
        if (foundAt < 0) {
            return false;
        }
        searchFrom = foundAt + text.size();
    }
    return true;
}

QVariantList outputPartsToVariantList(const QStringList& parts) {
    QVariantList result;
    for (const QString& part : parts) {
        result.append(part);
    }
    return result;
}

bool isTransientChatStatusMessage(const QJsonObject& message) {
    return message.value(QStringLiteral("transient_status")).toBool(false)
        || message.value(QStringLiteral("source")).toString() == QStringLiteral("huskarui-memory");
}

QStringList displayPartsFromMessage(const QJsonObject& message, bool outputSplittingEnabled) {
    QStringList parts = outputPartsFromJsonArray(message.value(QStringLiteral("display_parts")).toArray());
    if (message.value(QStringLiteral("role")).toString() == QStringLiteral("assistant")
        && isTransientChatStatusMessage(message)) {
        return parts.isEmpty() ? fallbackOutputParts(message.value(QStringLiteral("content")).toString()) : parts;
    }
    if (outputSplittingEnabled && message.value(QStringLiteral("role")).toString() == QStringLiteral("assistant")) {
        if (!parts.isEmpty()) {
            parts = refinedOutputBubbleParts(parts);
            if (!parts.isEmpty()) {
                return parts;
            }
        }
        return localOutputBubbleParts(message.value(QStringLiteral("content")).toString());
    }
    if (parts.isEmpty()) {
        parts = fallbackOutputParts(message.value(QStringLiteral("content")).toString());
    }
    return parts;
}

QVariantMap chatMessageToVariant(const QJsonObject& message, int index, bool outputSplittingEnabled) {
    const QString role = message.value("role").toString();
    const QString rawContent = message.value("content").toString();
    const QStringList parts = displayPartsFromMessage(message, outputSplittingEnabled);
    const bool useDisplayContent = outputSplittingEnabled
        && role == QStringLiteral("assistant")
        && !isTransientChatStatusMessage(message)
        && !parts.isEmpty();
    const QString content = useDisplayContent ? parts.join(QStringLiteral("\n\n")) : rawContent;
    QVariantMap item;
    item.insert(QStringLiteral("index"), index);
    item.insert(QStringLiteral("role"), role);
    item.insert(QStringLiteral("content"), content);
    item.insert(QStringLiteral("parts"), outputPartsToVariantList(parts));
    item.insert(QStringLiteral("created_at"), message.value("created_at").toString());
    item.insert(QStringLiteral("timestamp"), message.value("timestamp").toString());
    item.insert(QStringLiteral("message_id"), message.value("message_id").toString());
    item.insert(QStringLiteral("source"), message.value("source").toString());
    item.insert(QStringLiteral("isUser"), role == QStringLiteral("user"));
    item.insert(QStringLiteral("isAssistant"), role == QStringLiteral("assistant"));
    item.insert(QStringLiteral("isSystem"), role == QStringLiteral("system"));
    item.insert(QStringLiteral("isTransientStatus"), isTransientChatStatusMessage(message));
    item.insert(QStringLiteral("preview"), clippedText(content, 180));
    return item;
}

QString sanitizedChatMessage(const QString& message) {
    QString text = message.trimmed();
    text.replace(QLatin1Char('\r'), QLatin1Char('\n'));
    while (text.contains(QStringLiteral("\n\n\n"))) {
        text.replace(QStringLiteral("\n\n\n"), QStringLiteral("\n\n"));
    }
    if (text.size() > 12000) {
        text = text.left(12000);
    }
    return text;
}

struct ChatRuntimeConfig {
    QString baseUrl;
    QString apiKey;
    QString model;
    double temperature{};
    int historyLimit{};
    int requestTimeout{};
    bool demoMode{};
    bool outputSplittingEnabled{ true };
    QString source;
};

QString normalizedBaseUrl(const QString& baseUrl) {
    QString result = baseUrl.trimmed();
    while (result.endsWith(QLatin1Char('/'))) {
        result.chop(1);
    }
    return result;
}

QString buildApiUrl(const QString& baseUrl, const QString& endpoint) {
    const QString cleanBase = normalizedBaseUrl(baseUrl);
    const QString cleanEndpoint = QString(endpoint).remove(QRegularExpression(QStringLiteral("^/+|/+$")));
    if (cleanBase.isEmpty()) {
        return {};
    }
    if (cleanBase.endsWith(QStringLiteral("/") + cleanEndpoint) || cleanBase.endsWith(cleanEndpoint)) {
        return cleanBase;
    }
    const QString loweredBase = cleanBase.toLower();
    if (!loweredBase.endsWith(QStringLiteral("/v1")) && !loweredBase.contains(QStringLiteral("/v1/"))) {
        return cleanBase + QStringLiteral("/v1/") + cleanEndpoint;
    }
    return cleanBase + QLatin1Char('/') + cleanEndpoint;
}

QString apiModelName(const QString& model) {
    QString result = model.trimmed();
    if (result.isEmpty()) {
        return {};
    }
    result.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("-"));
    return result.toLower();
}

QString responseErrorMessage(const QByteArray& body, int limit = 300) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(body, &error);
    if (error.error == QJsonParseError::NoError && document.isObject()) {
        const QJsonObject root = document.object();
        const QJsonValue errorValue = root.value(QStringLiteral("error"));
        if (errorValue.isObject()) {
            const QString message = errorValue.toObject().value(QStringLiteral("message")).toString().trimmed();
            if (!message.isEmpty()) {
                return message.left(limit);
            }
        } else if (errorValue.isString()) {
            const QString message = errorValue.toString().trimmed();
            if (!message.isEmpty()) {
                return message.left(limit);
            }
        }
        const QString message = root.value(QStringLiteral("message")).toString().trimmed();
        if (!message.isEmpty()) {
            return message.left(limit);
        }
    }
    return QString::fromUtf8(body).left(limit).simplified();
}

QString resolvedValue(const QString& storedValue, const QString& envKey) {
    const QString value = storedValue.trimmed();
    if (!value.isEmpty()) {
        return value;
    }
    return qEnvironmentVariable(envKey.toUtf8().constData()).trimmed();
}

QString firstProviderKey(const QJsonObject& provider) {
    const QJsonArray keys = provider.value(QStringLiteral("keys")).toArray();
    for (const QJsonValue& value : keys) {
        const QString key = value.toString().trimmed();
        if (!key.isEmpty()) {
            return key;
        }
    }
    return provider.value(QStringLiteral("api_key")).toString().trimmed();
}

ChatRuntimeConfig chatRuntimeConfig(const QDir& root) {
    const QJsonObject settings = readJsonObject(root, QStringLiteral("data/settings.json"), nullptr);
    const QJsonObject routes = readJsonObject(root, QStringLiteral("data/route_forwarding.json"), nullptr);

    QString routeBaseUrl;
    QString routeApiKey;
    QString routeModel;
    if (routes.value(QStringLiteral("enabled")).toBool(false)) {
        QList<QJsonObject> providers;
        const QJsonArray providerArray = routes.value(QStringLiteral("providers")).toArray();
        for (const QJsonValue& value : providerArray) {
            const QJsonObject provider = value.toObject();
            if (provider.value(QStringLiteral("enabled")).toBool(true)
                && !provider.value(QStringLiteral("base_url")).toString().trimmed().isEmpty()) {
                providers.append(provider);
            }
        }
        std::sort(providers.begin(), providers.end(), [](const QJsonObject& left, const QJsonObject& right) {
            const int leftPriority = qBound(1, left.value(QStringLiteral("priority")).toInt(999), 999);
            const int rightPriority = qBound(1, right.value(QStringLiteral("priority")).toInt(999), 999);
            if (leftPriority != rightPriority) {
                return leftPriority < rightPriority;
            }
            return left.value(QStringLiteral("name")).toString() < right.value(QStringLiteral("name")).toString();
        });
        if (!providers.isEmpty()) {
            const QJsonObject provider = providers.first();
            routeBaseUrl = provider.value(QStringLiteral("base_url")).toString().trimmed();
            routeApiKey = firstProviderKey(provider);
            routeModel = provider.value(QStringLiteral("model")).toString().trimmed();
        }
    }

    const QString settingsBaseUrl = resolvedValue(settings.value(QStringLiteral("llm_base_url")).toString(), QStringLiteral("LLM_BASE_URL"));
    const QString settingsApiKey = resolvedValue(settings.value(QStringLiteral("llm_api_key")).toString(), QStringLiteral("LLM_API_KEY"));
    const QString settingsModel = resolvedValue(settings.value(QStringLiteral("llm_model")).toString(), QStringLiteral("LLM_MODEL"));

    ChatRuntimeConfig config;
    config.baseUrl = settingsBaseUrl.isEmpty() ? routeBaseUrl : settingsBaseUrl;
    config.apiKey = settingsApiKey.isEmpty() ? routeApiKey : settingsApiKey;
    config.model = apiModelName(settingsModel.isEmpty() ? routeModel : settingsModel);
    config.temperature = qBound(0.0, settings.value(QStringLiteral("temperature")).toDouble(0.85), 2.0);
    config.historyLimit = qBound(1, settings.value(QStringLiteral("history_limit")).toInt(20), 100);
    config.requestTimeout = qBound(10, settings.value(QStringLiteral("request_timeout")).toInt(120), 600);
    config.demoMode = settings.value(QStringLiteral("demo_mode")).toBool(false);
    config.outputSplittingEnabled = settings.value(QStringLiteral("output_splitting_enabled")).toBool(true);
    config.source = settingsBaseUrl.isEmpty() && !routeBaseUrl.isEmpty() ? QStringLiteral("route_forwarding") : QStringLiteral("settings");
    return config;
}

QJsonObject chatHistoryMessage(
    const QString& role,
    const QString& content,
    const QString& source,
    const QJsonArray& displayParts = {}) {
    QJsonObject message;
    message.insert(QStringLiteral("role"), role);
    message.insert(QStringLiteral("content"), content);
    message.insert(QStringLiteral("created_at"), QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm:ss")));
    message.insert(QStringLiteral("message_id"), QUuid::createUuid().toString(QUuid::WithoutBraces));
    message.insert(QStringLiteral("source"), source);
    if (role == QStringLiteral("assistant") && !displayParts.isEmpty()) {
        message.insert(QStringLiteral("display_parts"), displayParts);
        message.insert(QStringLiteral("display_processor"), QStringLiteral("output-splitting-subagent"));
    }
    return message;
}

QString promptField(const QJsonObject& object, const QString& key, int maxLength = 2400) {
    QString value = object.value(key).toString().trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

void appendPromptLine(QStringList* lines, const QString& label, const QString& value) {
    if (!lines || value.trimmed().isEmpty()) {
        return;
    }
    lines->append(QStringLiteral("%1: %2").arg(label, value.trimmed()));
}

QJsonObject activePresetFromStore(const QJsonObject& store) {
    const QJsonArray presets = store.value(QStringLiteral("presets")).toArray();
    if (presets.isEmpty()) {
        return {};
    }

    const QString activePresetId = store.value(QStringLiteral("active_preset_id")).toString();
    for (const QJsonValue& value : presets) {
        const QJsonObject preset = value.toObject();
        if (preset.value(QStringLiteral("id")).toString() == activePresetId) {
            return preset;
        }
    }
    return presets.first().toObject();
}

QString buildPresetPrompt(const QDir& root) {
    const QJsonObject presetStore = readJsonObject(root, QStringLiteral("data/preset.json"), nullptr);
    const QJsonObject preset = activePresetFromStore(presetStore);
    if (preset.isEmpty() || !preset.value(QStringLiteral("enabled")).toBool(true)) {
        return {};
    }

    QStringList blocks;
    const QString basePrompt = promptField(preset, QStringLiteral("base_system_prompt"), 12000);
    if (!basePrompt.isEmpty()) {
        blocks.append(basePrompt);
    }

    const QJsonObject modules = preset.value(QStringLiteral("modules")).toObject();
    QStringList moduleLines;
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        const QString key = QLatin1String(meta.key);
        if (modules.value(key).toBool(meta.defaultEnabled)) {
            moduleLines.append(QStringLiteral("- %1：%2").arg(QString::fromUtf8(meta.label), QString::fromUtf8(meta.description)));
        }
    }
    if (!moduleLines.isEmpty()) {
        blocks.append(QStringLiteral("Preset Modules:\n%1").arg(moduleLines.join(QStringLiteral("\n"))));
    }

    const auto appendPromptArray = [&blocks](const QJsonArray& items) {
        for (const QJsonValue& value : items) {
            const QJsonObject item = value.toObject();
            if (item.isEmpty() || !item.value(QStringLiteral("enabled")).toBool(true)) {
                continue;
            }
            const QString content = promptField(item, QStringLiteral("content"), 12000);
            if (content.isEmpty()) {
                continue;
            }
            const QString name = displayText(item.value(QStringLiteral("name")).toString(), QStringLiteral("Sub Preset"));
            blocks.append(QStringLiteral("[%1]\n%2").arg(name, content));
        }
    };

    appendPromptArray(preset.value(QStringLiteral("extra_prompts")).toArray());
    appendPromptArray(preset.value(QStringLiteral("prompt_groups")).toArray());
    return blocks.join(QStringLiteral("\n\n")).trimmed();
}

QJsonObject modelMessage(const QString& role, const QString& content) {
    QJsonObject message;
    message.insert(QStringLiteral("role"), role);
    message.insert(QStringLiteral("content"), content);
    return message;
}

struct WorldbookHit {
    QString title;
    QString trigger;
    QString secondaryTrigger;
    QString matched;
    QString content;
    QString comment;
    QString source;
    QString group;
    int order = 100;
};

struct MemoryContextItem {
    QString title;
    QString content;
    QString notes;
    QString sourceLabel;
    QStringList tags;
    int score = 0;
    int order = 0;
};

int worldbookInt(const QJsonObject& object, const QString& key, int defaultValue, int minValue, int maxValue) {
    return qBound(minValue, object.value(key).toInt(defaultValue), maxValue);
}

QString worldbookString(const QJsonObject& object, const QString& key, int maxLength = 4000) {
    QString value = object.value(key).toString().trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QString worldbookSettingString(const QJsonObject& settings, const QString& key, const QString& defaultValue) {
    const QString value = settings.value(key).toString(defaultValue).trimmed().toLower();
    return value.isEmpty() ? defaultValue : value;
}

QStringList splitWorldbookAliases(const QString& trigger) {
    const QString normalized = trigger.normalized(QString::NormalizationForm_KC);
    const QStringList parts = normalized.split(QRegularExpression(QStringLiteral("[|,，、/\\r\\n]+")), Qt::SkipEmptyParts);
    QStringList aliases;
    for (QString alias : parts) {
        alias = alias.trimmed();
        if (!alias.isEmpty()) {
            aliases.append(alias);
        }
    }
    if (aliases.isEmpty() && !normalized.trimmed().isEmpty()) {
        aliases.append(normalized.trimmed());
    }
    return aliases;
}

bool keywordMatchesQuery(const QString& queryText, const QString& keyword, bool caseSensitive, bool wholeWord) {
    QString query = queryText.normalized(QString::NormalizationForm_KC);
    QString target = keyword.normalized(QString::NormalizationForm_KC).trimmed();
    if (query.isEmpty() || target.isEmpty()) {
        return false;
    }

    if (!caseSensitive) {
        query = query.toLower();
        target = target.toLower();
    }
    if (!wholeWord) {
        return query.contains(target);
    }
    if (QRegularExpression(QStringLiteral("[\\x{4e00}-\\x{9fff}]")).match(target).hasMatch()) {
        return query.contains(target);
    }

    const QString pattern = QStringLiteral("(?<![0-9A-Za-z_])%1(?![0-9A-Za-z_])")
        .arg(QRegularExpression::escape(target));
    return QRegularExpression(pattern).match(query).hasMatch();
}

bool worldbookAliasesMatch(
    const QString& queryText,
    const QStringList& aliases,
    const QString& mode,
    bool caseSensitive,
    bool wholeWord,
    QStringList* matchedAliases) {
    if (matchedAliases) {
        matchedAliases->clear();
    }
    if (aliases.isEmpty()) {
        return false;
    }

    QStringList matches;
    for (const QString& alias : aliases) {
        if (keywordMatchesQuery(queryText, alias, caseSensitive, wholeWord)) {
            matches.append(alias);
        }
    }
    if (matchedAliases) {
        *matchedAliases = matches;
    }
    return mode == QStringLiteral("all") ? matches.size() == aliases.size() : !matches.isEmpty();
}

QString worldbookQueryText(const QJsonArray& conversations, const ChatRuntimeConfig& config) {
    QStringList parts;
    const int maxRecentMessages = qBound(2, config.historyLimit * 2, 200);
    const int startIndex = qMax(0, conversations.size() - maxRecentMessages);
    for (int i = startIndex; i < conversations.size(); ++i) {
        const QJsonObject item = conversations.at(i).toObject();
        const QString role = item.value(QStringLiteral("role")).toString();
        QString content = item.value(QStringLiteral("content")).toString().trimmed();
        if ((role == QStringLiteral("user") || role == QStringLiteral("assistant") || role == QStringLiteral("system"))
            && !content.isEmpty()) {
            if (content.size() > 2000) {
                content = content.left(2000).trimmed();
            }
            parts.append(content);
        }
    }
    return parts.join(QStringLiteral("\n"));
}

QList<WorldbookHit> matchWorldbookHits(const QDir& root, const QJsonArray& conversations, const ChatRuntimeConfig& config) {
    const QJsonObject store = readJsonObject(root, QStringLiteral("data/worldbook.json"), nullptr);
    const QJsonObject settings = store.value(QStringLiteral("settings")).toObject();
    if (!settings.value(QStringLiteral("enabled")).toBool(true)) {
        return {};
    }

    const QString queryText = worldbookQueryText(conversations, config);
    if (queryText.trimmed().isEmpty()) {
        return {};
    }

    const QJsonArray entries = store.value(QStringLiteral("entries")).toArray();
    const int maxHits = qBound(1, settings.value(QStringLiteral("max_hits")).toInt(3), 20);
    const QString defaultEntryType = worldbookSettingString(settings, QStringLiteral("default_entry_type"), QStringLiteral("keyword"));
    const QString defaultMatchMode = worldbookSettingString(settings, QStringLiteral("default_match_mode"), QStringLiteral("any"));
    const QString defaultSecondaryMode = worldbookSettingString(settings, QStringLiteral("default_secondary_mode"), QStringLiteral("all"));
    const QString defaultGroupOperator = worldbookSettingString(settings, QStringLiteral("default_group_operator"), QStringLiteral("and"));
    const bool defaultCaseSensitive = settings.value(QStringLiteral("default_case_sensitive")).toBool(false);
    const bool defaultWholeWord = settings.value(QStringLiteral("default_whole_word")).toBool(false);
    const int defaultChance = qBound(0, settings.value(QStringLiteral("default_chance")).toInt(100), 100);

    QList<WorldbookHit> hits;
    for (int i = 0; i < entries.size(); ++i) {
        const QJsonObject entry = entries.at(i).toObject();
        if (!entry.value(QStringLiteral("enabled")).toBool(true)) {
            continue;
        }

        const QString content = worldbookString(entry, QStringLiteral("content"));
        if (content.isEmpty()) {
            continue;
        }

        const int chance = worldbookInt(entry, QStringLiteral("chance"), defaultChance, 0, 100);
        if (chance <= 0) {
            continue;
        }

        QString entryType = entry.value(QStringLiteral("entry_type")).toString(defaultEntryType).trimmed().toLower();
        if (entryType != QStringLiteral("constant") && entryType != QStringLiteral("keyword")) {
            continue;
        }

        QString matchedText;
        QString source = entryType;
        if (entryType == QStringLiteral("keyword")) {
            const QString trigger = worldbookString(entry, QStringLiteral("trigger"), 1200);
            if (trigger.isEmpty()) {
                continue;
            }

            const bool caseSensitive = entry.value(QStringLiteral("case_sensitive")).toBool(defaultCaseSensitive);
            const bool wholeWord = entry.value(QStringLiteral("whole_word")).toBool(defaultWholeWord);
            const QString primaryMode = entry.value(QStringLiteral("match_mode")).toString(defaultMatchMode).trimmed().toLower() == QStringLiteral("all")
                ? QStringLiteral("all")
                : QStringLiteral("any");
            const QString secondaryMode = entry.value(QStringLiteral("secondary_mode")).toString(defaultSecondaryMode).trimmed().toLower() == QStringLiteral("any")
                ? QStringLiteral("any")
                : QStringLiteral("all");
            const QString groupOperator = entry.value(QStringLiteral("group_operator")).toString(defaultGroupOperator).trimmed().toLower() == QStringLiteral("or")
                ? QStringLiteral("or")
                : QStringLiteral("and");

            QStringList primaryMatches;
            QStringList secondaryMatches;
            const bool primaryOk = worldbookAliasesMatch(
                queryText,
                splitWorldbookAliases(trigger),
                primaryMode,
                caseSensitive,
                wholeWord,
                &primaryMatches);
            const QString secondaryTrigger = worldbookString(entry, QStringLiteral("secondary_trigger"), 1200);
            const QStringList secondaryAliases = splitWorldbookAliases(secondaryTrigger);
            const bool secondaryOk = secondaryAliases.isEmpty()
                ? false
                : worldbookAliasesMatch(queryText, secondaryAliases, secondaryMode, caseSensitive, wholeWord, &secondaryMatches);
            const bool matched = secondaryAliases.isEmpty()
                ? primaryOk
                : (groupOperator == QStringLiteral("or") ? (primaryOk || secondaryOk) : (primaryOk && secondaryOk));
            if (!matched) {
                continue;
            }
            matchedText = (primaryMatches + secondaryMatches).join(QStringLiteral(" / "));
        } else {
            matchedText = QStringLiteral("常驻");
            source = QStringLiteral("constant");
        }

        WorldbookHit hit;
        hit.title = worldbookString(entry, QStringLiteral("title"), 200);
        hit.trigger = worldbookString(entry, QStringLiteral("trigger"), 600);
        hit.secondaryTrigger = worldbookString(entry, QStringLiteral("secondary_trigger"), 600);
        hit.matched = matchedText;
        hit.content = content;
        hit.comment = worldbookString(entry, QStringLiteral("comment"), 240);
        hit.source = source;
        hit.group = worldbookString(entry, QStringLiteral("group"), 120);
        hit.order = qBound(0, entry.value(QStringLiteral("order")).toInt(entry.value(QStringLiteral("priority")).toInt(100)), 999999);
        hits.append(hit);
    }

    std::sort(hits.begin(), hits.end(), [](const WorldbookHit& left, const WorldbookHit& right) {
        if (left.order != right.order) {
            return left.order < right.order;
        }
        const int leftSourceRank = left.source == QStringLiteral("constant") ? 0 : 3;
        const int rightSourceRank = right.source == QStringLiteral("constant") ? 0 : 3;
        if (leftSourceRank != rightSourceRank) {
            return leftSourceRank < rightSourceRank;
        }
        return left.title < right.title;
    });
    while (hits.size() > maxHits) {
        hits.removeLast();
    }
    return hits;
}

QString buildWorldbookPrompt(const QList<WorldbookHit>& hits) {
    if (hits.isEmpty()) {
        return {};
    }

    QStringList blocks;
    blocks.append(QStringLiteral("The following are the worldbook notes matched in this turn."));
    blocks.append(QStringLiteral("These are high-priority factual backdrops for the current conversation."));
    blocks.append(QStringLiteral("If the user is asking about any of these items directly, answer from these notes first."));
    blocks.append(QStringLiteral("Do not mention that you saw the worldbook notes in your answer."));
    for (int i = 0; i < hits.size(); ++i) {
        const WorldbookHit& hit = hits.at(i);
        QStringList lines;
        lines.append(QStringLiteral("%1. Title: %2").arg(i + 1).arg(displayText(hit.title, displayText(hit.trigger, QStringLiteral("Worldbook note")))));
        lines.append(QStringLiteral("Source: %1").arg(hit.source));
        if (!hit.group.isEmpty()) {
            lines.append(QStringLiteral("Group: %1").arg(hit.group));
        }
        if (!hit.trigger.isEmpty()) {
            lines.append(QStringLiteral("Trigger: %1").arg(hit.trigger));
        }
        if (!hit.matched.isEmpty()) {
            lines.append(QStringLiteral("Matched: %1").arg(hit.matched));
        }
        if (!hit.secondaryTrigger.isEmpty()) {
            lines.append(QStringLiteral("Secondary trigger: %1").arg(hit.secondaryTrigger));
        }
        lines.append(QStringLiteral("Content: %1").arg(hit.content));
        if (!hit.comment.isEmpty()) {
            lines.append(QStringLiteral("Comment: %1").arg(hit.comment));
        }
        blocks.append(lines.join(QStringLiteral("\n")));
    }
    return blocks.join(QStringLiteral("\n\n"));
}

QString normalizedCardRuntimeKey(const QString& value, const QString& fallback = QStringLiteral("global")) {
    QString text = value.trimmed().isEmpty() ? fallback : value.trimmed().toLower();
    text.replace(QRegularExpression(QStringLiteral("\\s+")), QStringLiteral("_"));
    text.replace(QRegularExpression(QStringLiteral("[^a-z0-9_\\-]+")), QString());
    text.replace(QRegularExpression(QStringLiteral("[_\\-]{2,}")), QStringLiteral("_"));
    text = text.trimmed();
    while (text.startsWith(QLatin1Char('_')) || text.startsWith(QLatin1Char('-'))) {
        text.remove(0, 1);
    }
    while (text.endsWith(QLatin1Char('_')) || text.endsWith(QLatin1Char('-'))) {
        text.chop(1);
    }
    return text.isEmpty() ? fallback : text;
}

QJsonArray readJsonArrayFile(const QString& path) {
    QFile file(path);
    if (!file.exists() || !file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    QJsonArray result;
    if (!parseJsonArrayPayload(file.readAll(), &result, nullptr)) {
        return {};
    }
    return result;
}

QJsonObject readJsonObjectFile(const QString& path, QString* errorMessage = nullptr) {
    QFile file(path);
    if (!file.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("文件不存在");
        }
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法读取：%1").arg(file.errorString());
        }
        return {};
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("JSON 无效：%1").arg(error.errorString());
        }
        return {};
    }
    return document.object();
}

QJsonDocument readJsonDocumentFile(const QString& path, QString* errorMessage = nullptr) {
    QFile file(path);
    if (!file.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("文件不存在");
        }
        return {};
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法读取：%1").arg(file.errorString());
        }
        return {};
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || document.isNull()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("JSON 无效：%1").arg(error.errorString());
        }
        return {};
    }
    return document;
}

QString localFilePathFromInput(QString sourcePath) {
    sourcePath = sourcePath.trimmed();
    const QUrl url(sourcePath);
    if (url.isLocalFile()) {
        sourcePath = url.toLocalFile();
    }
    return QDir::fromNativeSeparators(sourcePath);
}

QString safeImportFileName(QString fileName, const QString& fallbackBaseName) {
    fileName = QFileInfo(fileName).fileName().trimmed();
    if (fileName.isEmpty()) {
        fileName = fallbackBaseName.trimmed();
    }
    if (fileName.isEmpty()) {
        fileName = QStringLiteral("imported");
    }
    fileName.replace(QRegularExpression(QStringLiteral("[\\\\/:*?\"<>|]+")), QStringLiteral("_"));
    if (!fileName.endsWith(QStringLiteral(".json"), Qt::CaseInsensitive)) {
        fileName += QStringLiteral(".json");
    }
    return fileName;
}

QString uniqueFilePathInDir(const QDir& dir, const QString& fileName) {
    const QFileInfo info(fileName);
    const QString baseName = info.completeBaseName().isEmpty() ? QStringLiteral("imported") : info.completeBaseName();
    const QString suffix = info.suffix().isEmpty() ? QStringLiteral("json") : info.suffix();
    QString candidate = dir.absoluteFilePath(baseName + QLatin1Char('.') + suffix);
    if (!QFileInfo::exists(candidate)) {
        return candidate;
    }

    for (int attempt = 1; attempt <= 100; ++attempt) {
        candidate = dir.absoluteFilePath(QStringLiteral("%1-%2.%3").arg(baseName).arg(attempt).arg(suffix));
        if (!QFileInfo::exists(candidate)) {
            return candidate;
        }
    }
    return dir.absoluteFilePath(QStringLiteral("%1-%2.%3")
        .arg(baseName, QUuid::createUuid().toString(QUuid::WithoutBraces), suffix));
}

bool writeJsonDocument(const QString& path, const QJsonDocument& document, QString* errorMessage = nullptr) {
    QSaveFile saveFile(path);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法写入：%1").arg(saveFile.errorString());
        }
        return false;
    }
    const QByteArray payload = document.toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("写入失败：%1").arg(saveFile.errorString());
        }
        return false;
    }
    if (!saveFile.commit()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("提交失败：%1").arg(saveFile.errorString());
        }
        return false;
    }
    return true;
}

bool looksLikePresetObject(const QJsonObject& preset) {
    return preset.contains(QStringLiteral("modules"))
        || preset.contains(QStringLiteral("extra_prompts"))
        || preset.contains(QStringLiteral("prompt_groups"))
        || preset.contains(QStringLiteral("base_system_prompt"));
}

QString generatedPresetId() {
    return QStringLiteral("preset-import-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces));
}

QJsonObject normalizedImportedPreset(QJsonObject preset, const QString& fallbackName) {
    QString id = preset.value(QStringLiteral("id")).toString().trimmed();
    if (id.isEmpty()) {
        id = generatedPresetId();
    }
    preset.insert(QStringLiteral("id"), id);

    QString name = preset.value(QStringLiteral("name")).toString().trimmed();
    if (name.isEmpty()) {
        name = fallbackName.trimmed().isEmpty() ? QStringLiteral("导入预设") : fallbackName.trimmed();
    }
    preset.insert(QStringLiteral("name"), name.left(64));
    preset.insert(QStringLiteral("enabled"), preset.value(QStringLiteral("enabled")).toBool(true));

    QJsonObject modules = preset.value(QStringLiteral("modules")).toObject();
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        const QString key = QLatin1String(meta.key);
        if (!modules.contains(key)) {
            modules.insert(key, meta.defaultEnabled);
        }
    }
    applyPresetModuleMutex(&modules);
    preset.insert(QStringLiteral("modules"), modules);

    if (!preset.value(QStringLiteral("extra_prompts")).isArray()) {
        preset.insert(QStringLiteral("extra_prompts"), QJsonArray{});
    }
    if (!preset.value(QStringLiteral("prompt_groups")).isArray()) {
        preset.insert(QStringLiteral("prompt_groups"), QJsonArray{});
    }
    return preset;
}

QJsonArray importedPresetArray(const QJsonDocument& document, const QString& fallbackName, QString* errorMessage) {
    if (!document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("预设导入文件必须是 JSON 对象");
        }
        return {};
    }

    const QJsonObject source = document.object();
    QJsonArray rawPresets = source.value(QStringLiteral("presets")).toArray();
    if (rawPresets.isEmpty() && looksLikePresetObject(source)) {
        rawPresets.append(source);
    }
    if (rawPresets.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("未找到可导入的预设内容");
        }
        return {};
    }

    QJsonArray result;
    for (const QJsonValue& value : rawPresets) {
        if (!value.isObject()) {
            continue;
        }
        result.append(normalizedImportedPreset(value.toObject(), fallbackName));
    }
    if (result.isEmpty() && errorMessage) {
        *errorMessage = QStringLiteral("未找到有效预设");
    }
    return result;
}

QString presetSubPresetKey(const QString& collection, int index, const QJsonObject& item) {
    const QString id = item.value(QStringLiteral("id")).toString().trimmed();
    return QStringLiteral("%1:%2").arg(collection, id.isEmpty() ? QString::number(index) : id);
}

QVariantList presetSubPresetItemsToVariant(const QJsonArray& extraPrompts, const QJsonArray& promptGroups) {
    QVariantList result;
    const auto appendItems = [&result](const QJsonArray& items, const QString& collection, const QString& typeLabel) {
        for (int i = 0; i < items.size(); ++i) {
            const QJsonObject itemObject = items.at(i).toObject();
            if (itemObject.isEmpty()) {
                continue;
            }
            QVariantMap item;
            item.insert(QStringLiteral("key"), presetSubPresetKey(collection, i, itemObject));
            item.insert(QStringLiteral("collection"), collection);
            item.insert(QStringLiteral("index"), i);
            item.insert(QStringLiteral("typeLabel"), typeLabel);
            item.insert(QStringLiteral("label"),
                displayText(itemObject.value(QStringLiteral("name")).toString(), QStringLiteral("子预设 %1").arg(i + 1)));
            item.insert(QStringLiteral("enabled"), itemObject.value(QStringLiteral("enabled")).toBool(true));
            item.insert(QStringLiteral("preview"), clippedText(itemObject.value(QStringLiteral("content")).toString(), 140, QStringLiteral("")));
            result.append(item);
        }
    };

    appendItems(extraPrompts, QStringLiteral("extra_prompts"), QStringLiteral("提示词"));
    appendItems(promptGroups, QStringLiteral("prompt_groups"), QStringLiteral("分组"));
    return result;
}

void applySubPresetDraft(QJsonObject* activePreset, const QVariantMap& draft) {
    if (!activePreset || !draft.contains(QStringLiteral("subPresets"))) {
        return;
    }

    const QVariantMap states = draft.value(QStringLiteral("subPresets")).toMap();
    auto updateArray = [&states](QJsonArray items, const QString& collection) {
        for (int i = 0; i < items.size(); ++i) {
            QJsonObject item = items.at(i).toObject();
            if (item.isEmpty()) {
                continue;
            }
            const QString key = presetSubPresetKey(collection, i, item);
            if (states.contains(key)) {
                item.insert(QStringLiteral("enabled"), states.value(key).toBool());
                items.replace(i, item);
            }
        }
        return items;
    };

    activePreset->insert(
        QStringLiteral("extra_prompts"),
        updateArray(activePreset->value(QStringLiteral("extra_prompts")).toArray(), QStringLiteral("extra_prompts")));
    activePreset->insert(
        QStringLiteral("prompt_groups"),
        updateArray(activePreset->value(QStringLiteral("prompt_groups")).toArray(), QStringLiteral("prompt_groups")));
}

QStringList memoryTags(const QJsonObject& item) {
    QStringList tags;
    const QJsonValue value = item.value(QStringLiteral("tags"));
    if (value.isArray()) {
        for (const QJsonValue& tagValue : value.toArray()) {
            const QString tag = tagValue.toString().trimmed();
            if (!tag.isEmpty() && !tags.contains(tag)) {
                tags.append(tag);
            }
        }
    } else if (value.isString()) {
        const QStringList parts = value.toString().split(QRegularExpression(QStringLiteral("[,，、;；|/\\r\\n]+")), Qt::SkipEmptyParts);
        for (QString tag : parts) {
            tag = tag.trimmed();
            if (!tag.isEmpty() && !tags.contains(tag)) {
                tags.append(tag);
            }
        }
    }
    while (tags.size() > 8) {
        tags.removeLast();
    }
    return tags;
}

QString memoryField(const QJsonObject& item, const QString& key, int maxLength = 1200) {
    QString value = item.value(key).toString().trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QString normalizedMemoryStatus(const QString& value, const QString& defaultValue = QStringLiteral("active")) {
    const QString normalized = value.trimmed().toLower();
    if (normalized == QStringLiteral("archived")) {
        return QStringLiteral("archived");
    }
    if (normalized == QStringLiteral("active")) {
        return QStringLiteral("active");
    }
    return defaultValue == QStringLiteral("archived") ? QStringLiteral("archived") : QStringLiteral("active");
}

QString memoryEntryDraftString(
    const QVariantMap& draft,
    const QString& key,
    const QJsonObject& current,
    const QString& defaultValue,
    int maxLength) {
    QString value = draft.contains(key) ? draft.value(key).toString().trimmed() : current.value(key).toString(defaultValue).trimmed();
    value.replace(QLatin1Char('\r'), QLatin1Char('\n'));
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QJsonArray memoryTagsFromDraft(const QVariantMap& draft, const QJsonObject& current) {
    QString source;
    if (draft.contains(QStringLiteral("tagsText"))) {
        source = draft.value(QStringLiteral("tagsText")).toString();
    } else if (current.value(QStringLiteral("tags")).isArray()) {
        source = tagsTextFromArray(current.value(QStringLiteral("tags")).toArray());
    } else {
        source = current.value(QStringLiteral("tags")).toString();
    }

    const QStringList parts = source.split(QRegularExpression(QStringLiteral("[,，、;；|/\\r\\n]+")), Qt::SkipEmptyParts);
    QStringList uniqueTags;
    for (QString tag : parts) {
        tag = tag.simplified();
        if (tag.size() > 80) {
            tag = tag.left(80).trimmed();
        }
        if (!tag.isEmpty() && !uniqueTags.contains(tag)) {
            uniqueTags.append(tag);
        }
        if (uniqueTags.size() >= 24) {
            break;
        }
    }

    QJsonArray result;
    for (const QString& tag : uniqueTags) {
        result.append(tag);
    }
    return result;
}

QVariantMap memoryEntryToVariant(const QJsonObject& entry, int index, const QString& relativePath) {
    const QString status = normalizedMemoryStatus(
        entry.value(QStringLiteral("memory_status")).toString(entry.value(QStringLiteral("status")).toString(QStringLiteral("active"))));
    const QString content = displayText(
        entry.value(QStringLiteral("content")).toString(),
        entry.value(QStringLiteral("summary")).toString());

    QVariantMap item;
    item.insert(QStringLiteral("index"), index);
    item.insert(QStringLiteral("id"), entry.value(QStringLiteral("id")).toString());
    item.insert(QStringLiteral("title"), displayText(entry.value(QStringLiteral("title")).toString(), QStringLiteral("记忆 %1").arg(index + 1)));
    item.insert(QStringLiteral("content"), content);
    item.insert(QStringLiteral("notes"), entry.value(QStringLiteral("notes")).toString());
    item.insert(QStringLiteral("tagsText"), memoryTags(entry).join(QStringLiteral(", ")));
    item.insert(QStringLiteral("memory_status"), status);
    item.insert(QStringLiteral("active"), status != QStringLiteral("archived"));
    item.insert(QStringLiteral("sourcePath"), relativePath);
    item.insert(QStringLiteral("preview"), clippedText(content, 180));
    return item;
}

QVariantList memoryEntriesToVariant(const QJsonArray& entries, const QString& relativePath) {
    QVariantList result;
    for (int i = 0; i < entries.size(); ++i) {
        const QJsonObject entry = entries.at(i).toObject();
        if (!entry.isEmpty()) {
            result.append(memoryEntryToVariant(entry, i, relativePath));
        }
    }
    return result;
}

bool currentMemoryRelativePath(const QDir& root, QString* relativePath, QString* errorMessage) {
    const QString cardRelativePath = QStringLiteral("data/current_role_card.json");
    const QString cardPath = root.absoluteFilePath(cardRelativePath);
    if (!QFileInfo::exists(cardPath)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("current_role_card.json 不存在，无法定位当前记忆文件");
        }
        return false;
    }

    QString readError;
    const QJsonObject card = readJsonObjectFile(cardPath, &readError);
    if (!readError.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("current_role_card.json %1").arg(readError);
        }
        return false;
    }

    const QString runtimeKey = normalizedCardRuntimeKey(card.value(QStringLiteral("card_uid")).toString());
    if (relativePath) {
        *relativePath = QStringLiteral("data/card_runtime/cards/%1/memories.json").arg(runtimeKey);
    }
    return true;
}

bool readJsonArrayFileStrict(const QString& path, QJsonArray* array, QString* errorMessage) {
    QFile file(path);
    if (!file.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("文件不存在");
        }
        return false;
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法读取：%1").arg(file.errorString());
        }
        return false;
    }

    QJsonArray result;
    if (!parseJsonArrayPayload(file.readAll(), &result, errorMessage)) {
        return false;
    }
    if (array) {
        *array = result;
    }
    return true;
}

QJsonObject sanitizedMemoryEntryFromDraft(
    const QVariantMap& draft,
    const QJsonObject& current,
    int index,
    bool isNewEntry,
    QString* errorMessage) {
    QJsonObject entry = current;
    if (isNewEntry || !entry.contains(QStringLiteral("id"))) {
        entry.insert(QStringLiteral("id"), QStringLiteral("memory-huskarui-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces)));
    }

    const QString title = displayText(
        memoryEntryDraftString(draft, QStringLiteral("title"), entry, QStringLiteral("记忆 %1").arg(index + 1), 160),
        QStringLiteral("记忆 %1").arg(index + 1));
    const QString content = memoryEntryDraftString(
        draft,
        QStringLiteral("content"),
        entry,
        entry.value(QStringLiteral("summary")).toString(),
        12000);
    if (content.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("记忆内容不能为空");
        }
        return {};
    }

    QString status = normalizedMemoryStatus(
        memoryEntryDraftString(
            draft,
            QStringLiteral("memory_status"),
            entry,
            entry.value(QStringLiteral("status")).toString(QStringLiteral("active")),
            32));
    if (draft.contains(QStringLiteral("active"))) {
        status = draft.value(QStringLiteral("active")).toBool() ? QStringLiteral("active") : QStringLiteral("archived");
    }

    entry.insert(QStringLiteral("title"), title);
    entry.insert(QStringLiteral("content"), content);
    entry.insert(QStringLiteral("notes"), memoryEntryDraftString(draft, QStringLiteral("notes"), entry, QString(), 2400));
    entry.insert(QStringLiteral("tags"), memoryTagsFromDraft(draft, entry));
    entry.insert(QStringLiteral("memory_status"), status);
    entry.insert(QStringLiteral("updated_at"), QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm:ss")));
    if (isNewEntry && !entry.contains(QStringLiteral("created_at"))) {
        entry.insert(QStringLiteral("created_at"), entry.value(QStringLiteral("updated_at")).toString());
    }
    return entry;
}

int memoryScore(const MemoryContextItem& item, const QString& queryText) {
    const QString query = queryText.toLower();
    if (query.isEmpty()) {
        return 0;
    }

    int score = 0;
    const QString haystack = QStringList{ item.title, item.content, item.notes, item.tags.join(QStringLiteral(" ")) }.join(QStringLiteral("\n")).toLower();
    const QStringList terms = query.split(QRegularExpression(QStringLiteral("[\\s,，。！？!?;；:：、/\\r\\n]+")), Qt::SkipEmptyParts);
    for (const QString& rawTerm : terms) {
        const QString term = rawTerm.trimmed();
        if (term.size() < 2) {
            continue;
        }
        if (haystack.contains(term)) {
            score += item.title.toLower().contains(term) ? 3 : 1;
        }
    }
    return score;
}

void appendMemoryItem(QList<MemoryContextItem>* items, const QJsonObject& object, const QString& sourceLabel, int order) {
    if (!items) {
        return;
    }

    const QString status = object.value(QStringLiteral("memory_status")).toString(
        object.value(QStringLiteral("status")).toString(QStringLiteral("active"))).trimmed().toLower();
    if (status == QStringLiteral("archived")) {
        return;
    }

    MemoryContextItem item;
    item.title = memoryField(object, QStringLiteral("title"), 200);
    item.content = memoryField(object, QStringLiteral("content"));
    if (item.content.isEmpty()) {
        item.content = memoryField(object, QStringLiteral("summary"));
    }
    item.notes = memoryField(object, QStringLiteral("notes"), 600);
    item.tags = memoryTags(object);
    item.sourceLabel = sourceLabel;
    item.order = order;
    if (item.title.isEmpty() && item.content.isEmpty() && item.notes.isEmpty()) {
        return;
    }
    items->append(item);
}

void appendMemoryOutlineItem(QList<MemoryContextItem>* items, const QJsonObject& object, int order) {
    if (!items || object.value(QStringLiteral("participate_recall")).toBool(true) == false) {
        return;
    }

    QStringList parts;
    const QList<QPair<QString, QString>> fields = {
        { QStringLiteral("summary"), QStringLiteral("Summary") },
        { QStringLiteral("story_time"), QStringLiteral("Story Time") },
        { QStringLiteral("chapter"), QStringLiteral("Chapter") },
        { QStringLiteral("location"), QStringLiteral("Location") },
        { QStringLiteral("characters"), QStringLiteral("Characters") },
        { QStringLiteral("relationship_progress"), QStringLiteral("Relationship") },
        { QStringLiteral("emotion_shift"), QStringLiteral("Emotion") },
        { QStringLiteral("conflicts"), QStringLiteral("Conflict") },
        { QStringLiteral("foreshadowing"), QStringLiteral("Foreshadowing") },
        { QStringLiteral("unresolved_items"), QStringLiteral("Unresolved") },
        { QStringLiteral("important_items"), QStringLiteral("Important Items") },
        { QStringLiteral("next_hooks"), QStringLiteral("Next Hooks") },
        { QStringLiteral("notes"), QStringLiteral("Notes") },
    };
    for (const auto& field : fields) {
        const QString value = memoryField(object, field.first, 600);
        if (!value.isEmpty()) {
            parts.append(QStringLiteral("%1: %2").arg(field.second, value));
        }
    }
    const QJsonArray keyEvents = object.value(QStringLiteral("key_events")).toArray();
    QStringList events;
    for (const QJsonValue& value : keyEvents) {
        const QString event = value.toString().trimmed();
        if (!event.isEmpty()) {
            events.append(event);
        }
        if (events.size() >= 6) {
            break;
        }
    }
    if (!events.isEmpty()) {
        parts.append(QStringLiteral("Key Events: %1").arg(events.join(QStringLiteral("; "))));
    }

    MemoryContextItem item;
    item.title = memoryField(object, QStringLiteral("title"), 200);
    item.content = parts.join(QStringLiteral("\n"));
    item.notes = memoryField(object, QStringLiteral("notes"), 600);
    item.sourceLabel = QStringLiteral("剧情档案");
    item.tags = QStringList{ QStringLiteral("memory-outline") };
    item.order = order;
    if (item.title.isEmpty() && item.content.isEmpty()) {
        return;
    }
    items->append(item);
}

QList<MemoryContextItem> collectMemoryContextItems(const QDir& root, const QJsonObject& card, const QJsonArray& conversations, const ChatRuntimeConfig& config) {
    const QString cardUid = normalizedCardRuntimeKey(card.value(QStringLiteral("card_uid")).toString());
    QStringList runtimeKeys;
    runtimeKeys.append(cardUid);
    if (cardUid != QStringLiteral("global")) {
        runtimeKeys.append(QStringLiteral("global"));
    }

    QList<MemoryContextItem> items;
    int order = 0;
    for (const QString& key : runtimeKeys) {
        const QDir runtimeDir(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards/%1").arg(key)));
        if (!runtimeDir.exists()) {
            continue;
        }

        const QJsonArray memories = readJsonArrayFile(runtimeDir.absoluteFilePath(QStringLiteral("memories.json")));
        for (const QJsonValue& value : memories) {
            appendMemoryItem(&items, value.toObject(), QStringLiteral("长期记忆"), order++);
        }
        const QJsonArray mergedMemories = readJsonArrayFile(runtimeDir.absoluteFilePath(QStringLiteral("merged_memories.json")));
        for (const QJsonValue& value : mergedMemories) {
            appendMemoryItem(&items, value.toObject(), QStringLiteral("合并记忆"), order++);
        }
        const QJsonArray outline = readJsonArrayFile(runtimeDir.absoluteFilePath(QStringLiteral("memory_outline.json")));
        for (const QJsonValue& value : outline) {
            appendMemoryOutlineItem(&items, value.toObject(), order++);
        }
    }

    const QString queryText = worldbookQueryText(conversations, config);
    for (MemoryContextItem& item : items) {
        item.score = memoryScore(item, queryText);
    }
    std::stable_sort(items.begin(), items.end(), [](const MemoryContextItem& left, const MemoryContextItem& right) {
        if (left.score != right.score) {
            return left.score > right.score;
        }
        return left.order > right.order;
    });
    const int limit = qBound(1, config.historyLimit / 2, 6);
    while (items.size() > limit) {
        items.removeLast();
    }
    return items;
}

QString buildMemoryPrompt(const QList<MemoryContextItem>& items) {
    if (items.isEmpty()) {
        return {};
    }

    QStringList blocks;
    blocks.append(QStringLiteral("The following are long-term memory materials relevant to this conversation."));
    blocks.append(QStringLiteral("Use them as supporting context, but do not hallucinate details that are not present."));
    for (int i = 0; i < items.size(); ++i) {
        const MemoryContextItem& item = items.at(i);
        QStringList lines;
        lines.append(QStringLiteral("%1. [%2] %3").arg(i + 1).arg(item.sourceLabel, displayText(item.title, QStringLiteral("Memory"))));
        if (!item.content.isEmpty()) {
            lines.append(QStringLiteral("Content: %1").arg(item.content));
        }
        if (!item.tags.isEmpty()) {
            lines.append(QStringLiteral("Tags: %1").arg(item.tags.join(QStringLiteral(", "))));
        }
        if (!item.notes.isEmpty()) {
            lines.append(QStringLiteral("Notes: %1").arg(item.notes));
        }
        blocks.append(lines.join(QStringLiteral("\n")));
    }
    return blocks.join(QStringLiteral("\n\n"));
}

QJsonArray buildChatCompletionMessages(const QDir& root, const QJsonArray& conversations, const ChatRuntimeConfig& config) {
    const QJsonObject card = readJsonObject(root, QStringLiteral("data/current_role_card.json"), nullptr);
    const QJsonObject rawCard = card.value(QStringLiteral("raw")).toObject();
    const QJsonObject persona = readJsonObject(root, QStringLiteral("data/persona.json"), nullptr);
    const QJsonObject userProfile = readJsonObject(root, QStringLiteral("data/user_profile.json"), nullptr);

    QStringList systemLines;
    systemLines.append(QStringLiteral("You are Fantareal's role-playing assistant. Stay in character, respond naturally, and continue the scene."));
    systemLines.append(QStringLiteral("Use the user's language unless the scene clearly asks otherwise."));
    appendPromptLine(&systemLines, QStringLiteral("Character name"), promptField(rawCard, QStringLiteral("name")).isEmpty()
        ? promptField(persona, QStringLiteral("name"))
        : promptField(rawCard, QStringLiteral("name")));
    appendPromptLine(&systemLines, QStringLiteral("Description"), promptField(rawCard, QStringLiteral("description")).isEmpty()
        ? promptField(persona, QStringLiteral("description"))
        : promptField(rawCard, QStringLiteral("description")));
    appendPromptLine(&systemLines, QStringLiteral("Personality"), promptField(rawCard, QStringLiteral("personality")).isEmpty()
        ? promptField(persona, QStringLiteral("personality"))
        : promptField(rawCard, QStringLiteral("personality")));
    appendPromptLine(&systemLines, QStringLiteral("Scenario"), promptField(rawCard, QStringLiteral("scenario")).isEmpty()
        ? promptField(persona, QStringLiteral("scenario"))
        : promptField(rawCard, QStringLiteral("scenario")));
    appendPromptLine(&systemLines, QStringLiteral("Creator notes"), promptField(rawCard, QStringLiteral("creator_notes")));
    appendPromptLine(&systemLines, QStringLiteral("User nickname"), promptField(userProfile, QStringLiteral("nickname"), 200));
    appendPromptLine(&systemLines, QStringLiteral("User profile"), promptField(userProfile, QStringLiteral("profile_text")));
    const QString presetPrompt = buildPresetPrompt(root);
    if (!presetPrompt.isEmpty()) {
        systemLines.append(QString());
        systemLines.append(QStringLiteral("[Preset]"));
        systemLines.append(presetPrompt);
    }
    const QString worldbookPrompt = buildWorldbookPrompt(matchWorldbookHits(root, conversations, config));
    if (!worldbookPrompt.isEmpty()) {
        systemLines.append(QString());
        systemLines.append(QStringLiteral("[Worldbook]"));
        systemLines.append(worldbookPrompt);
    }
    const QString memoryPrompt = buildMemoryPrompt(collectMemoryContextItems(root, card, conversations, config));
    if (!memoryPrompt.isEmpty()) {
        systemLines.append(QString());
        systemLines.append(QStringLiteral("[Memory]"));
        systemLines.append(memoryPrompt);
    }

    QJsonArray messages;
    messages.append(modelMessage(QStringLiteral("system"), systemLines.join(QStringLiteral("\n"))));

    const int maxRecentMessages = qBound(2, config.historyLimit * 2, 200);
    const int startIndex = qMax(0, conversations.size() - maxRecentMessages);
    for (int i = startIndex; i < conversations.size(); ++i) {
        const QJsonObject item = conversations.at(i).toObject();
        const QString role = item.value(QStringLiteral("role")).toString();
        QString content = item.value(QStringLiteral("content")).toString().trimmed();
        if (content.size() > 12000) {
            content = content.left(12000).trimmed();
        }
        if ((role == QStringLiteral("user") || role == QStringLiteral("assistant") || role == QStringLiteral("system"))
            && !content.isEmpty()) {
            messages.append(modelMessage(role == QStringLiteral("system") ? QStringLiteral("user") : role, content));
        }
    }
    return messages;
}

QString stringifyModelContent(const QJsonValue& value) {
    if (value.isString()) {
        return value.toString();
    }
    if (value.isArray()) {
        QStringList parts;
        const QJsonArray array = value.toArray();
        for (const QJsonValue& item : array) {
            if (item.isString()) {
                parts.append(item.toString());
            } else if (item.isObject()) {
                const QJsonObject object = item.toObject();
                const QString text = object.value(QStringLiteral("text")).toString();
                if (!text.isEmpty()) {
                    parts.append(text);
                }
            }
        }
        return parts.join(QString());
    }
    if (value.isObject()) {
        return value.toObject().value(QStringLiteral("text")).toString();
    }
    return {};
}

QString extractAssistantReply(const QByteArray& body, QString* errorMessage) {
    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(body, &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("模型响应 JSON 无效：%1").arg(parseError.errorString());
        }
        return {};
    }

    const QJsonObject root = document.object();
    const QJsonArray choices = root.value(QStringLiteral("choices")).toArray();
    if (choices.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("模型响应缺少 choices");
        }
        return {};
    }

    const QJsonObject firstChoice = choices.first().toObject();
    const QJsonObject message = firstChoice.value(QStringLiteral("message")).toObject();
    QString content = stringifyModelContent(message.value(QStringLiteral("content"))).trimmed();
    if (content.isEmpty()) {
        content = firstChoice.value(QStringLiteral("text")).toString().trimmed();
    }
    if (content.isEmpty() && errorMessage) {
        *errorMessage = QStringLiteral("模型响应缺少 message.content");
    }
    return content;
}

QString streamChoiceContent(const QJsonObject& choice) {
    const QJsonObject delta = choice.value(QStringLiteral("delta")).toObject();
    QString content = stringifyModelContent(delta.value(QStringLiteral("content")));
    if (content.isEmpty()) {
        content = stringifyModelContent(choice.value(QStringLiteral("message")).toObject().value(QStringLiteral("content")));
    }
    if (content.isEmpty()) {
        content = choice.value(QStringLiteral("text")).toString();
    }
    return content;
}

QString extractStreamingAssistantReply(const QByteArray& body, bool* sawStream, QString* errorMessage = nullptr) {
    bool sawDataLine = false;
    QStringList parts;
    const QStringList lines = QString::fromUtf8(body).split(QRegularExpression(QStringLiteral("[\\r\\n]+")), Qt::SkipEmptyParts);
    for (QString line : lines) {
        line = line.trimmed();
        if (line.isEmpty() || line.startsWith(QLatin1Char(':'))) {
            continue;
        }
        if (!line.startsWith(QStringLiteral("data:"))) {
            continue;
        }

        sawDataLine = true;
        const QString data = line.mid(5).trimmed();
        if (data == QStringLiteral("[DONE]")) {
            continue;
        }

        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(data.toUtf8(), &parseError);
        if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
            continue;
        }

        const QJsonArray choices = document.object().value(QStringLiteral("choices")).toArray();
        for (const QJsonValue& value : choices) {
            const QString content = streamChoiceContent(value.toObject());
            if (!content.isEmpty()) {
                parts.append(content);
            }
        }
    }

    if (sawStream) {
        *sawStream = sawDataLine;
    }
    if (sawDataLine && parts.isEmpty() && errorMessage) {
        *errorMessage = QStringLiteral("模型流式响应没有可用内容");
    }
    return parts.join(QString());
}

QJsonObject chatCompletionPayload(const ChatRuntimeConfig& config, const QJsonArray& messages, bool stream = false) {
    QJsonObject payload;
    payload.insert(QStringLiteral("model"), config.model);
    payload.insert(QStringLiteral("messages"), messages);
    payload.insert(QStringLiteral("temperature"), config.temperature);
    if (stream) {
        payload.insert(QStringLiteral("stream"), true);
    }
    return payload;
}

QString outputSplitterSystemPrompt() {
    return QStringLiteral(
        "你是一个聊天输出后处理器。\n"
        "你的任务是将输入文本整理成用于前端聊天气泡显示的 JSON 数组。\n"
        "规则：\n"
        "1. 不得改写原文内容。\n"
        "2. 不得新增剧情、补充描写或解释。\n"
        "3. 不得润色文本。\n"
        "4. 只移除明显不属于聊天正文的状态栏、系统栏、格式标签、空行和无意义分隔符。\n"
        "5. 保留有效的角色动作、旁白、对白和剧情正文。\n"
        "6. 按自然语义或句子切分为多个字符串。\n"
        "7. 每个字符串对应一个聊天气泡。\n"
        "8. 只输出合法 JSON 数组，不输出 Markdown，不输出解释。");
}

QJsonObject outputSplitterPayload(const ChatRuntimeConfig& config, const QString& rawOutput) {
    QJsonArray messages;
    messages.append(modelMessage(QStringLiteral("system"), outputSplitterSystemPrompt()));
    messages.append(modelMessage(QStringLiteral("user"), QStringLiteral("输入文本：\n%1").arg(rawOutput.trimmed())));

    QJsonObject payload;
    payload.insert(QStringLiteral("model"), config.model);
    payload.insert(QStringLiteral("messages"), messages);
    payload.insert(QStringLiteral("temperature"), 0.0);
    payload.insert(QStringLiteral("stream"), false);
    return payload;
}

QStringList requestOutputSplitterParts(
    const ChatRuntimeConfig& config,
    const QString& rawOutput,
    QString* errorMessage) {
    const QString url = buildApiUrl(config.baseUrl, QStringLiteral("chat/completions"));
    if (url.isEmpty() || config.model.trimmed().isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("输出切分子代理未配置");
        }
        return {};
    }

    QNetworkRequest request{ QUrl(url) };
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    if (!config.apiKey.trimmed().isEmpty()) {
        request.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.trimmed().toUtf8());
    }

    QNetworkAccessManager manager;
    QEventLoop loop;
    QTimer timer;
    timer.setSingleShot(true);
    QNetworkReply* reply = manager.post(request, QJsonDocument(outputSplitterPayload(config, rawOutput)).toJson(QJsonDocument::Compact));
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    QObject::connect(&timer, &QTimer::timeout, &loop, &QEventLoop::quit);
    timer.start(qBound(3, config.requestTimeout, 8) * 1000);
    loop.exec();

    if (!timer.isActive()) {
        reply->abort();
        reply->deleteLater();
        if (errorMessage) {
            *errorMessage = QStringLiteral("输出切分子代理超时");
        }
        return {};
    }
    timer.stop();

    const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QByteArray body = reply->readAll();
    const QNetworkReply::NetworkError networkError = reply->error();
    const QString networkErrorString = reply->errorString();
    reply->deleteLater();

    if (networkError != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("输出切分子代理请求失败：HTTP %1 / %2 %3")
                .arg(statusCode)
                .arg(networkErrorString, responseErrorMessage(body));
        }
        return {};
    }

    QString parseError;
    const QString content = extractAssistantReply(body, &parseError);
    if (content.trimmed().isEmpty()) {
        if (errorMessage) {
            *errorMessage = parseError.isEmpty() ? QStringLiteral("输出切分子代理返回空内容") : parseError;
        }
        return {};
    }

    QString splitError;
    const QStringList parts = parseOutputSplitterJson(content, &splitError);
    if (parts.isEmpty() && errorMessage) {
        *errorMessage = splitError;
    }
    return parts;
}

QJsonArray assistantDisplayParts(const ChatRuntimeConfig& config, const QString& rawOutput) {
    if (!config.outputSplittingEnabled) {
        return {};
    }

    const QStringList fallback = localOutputBubbleParts(rawOutput);
    if (fallback.isEmpty()) {
        return {};
    }

    QString splitError;
    const QStringList splitParts = requestOutputSplitterParts(config, rawOutput, &splitError);
    if (!splitParts.isEmpty() && outputPartsPreserveRawText(rawOutput, splitParts)) {
        const QStringList refinedParts = refinedOutputBubbleParts(splitParts);
        if (!refinedParts.isEmpty()) {
            return outputPartsToJsonArray(refinedParts);
        }
    }
    return outputPartsToJsonArray(fallback);
}

QString requestAssistantReply(
    const ChatRuntimeConfig& config,
    const QJsonArray& messages,
    QString* errorMessage) {
    const QString url = buildApiUrl(config.baseUrl, QStringLiteral("chat/completions"));
    if (url.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("聊天模型 API URL 未配置");
        }
        return {};
    }

    const QJsonObject payload = chatCompletionPayload(config, messages);

    QNetworkRequest request{ QUrl(url) };
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    if (!config.apiKey.trimmed().isEmpty()) {
        request.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.trimmed().toUtf8());
    }

    QNetworkAccessManager manager;
    QEventLoop loop;
    QTimer timer;
    timer.setSingleShot(true);
    QNetworkReply* reply = manager.post(request, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    QObject::connect(&timer, &QTimer::timeout, &loop, &QEventLoop::quit);
    timer.start(config.requestTimeout * 1000);
    loop.exec();

    if (!timer.isActive()) {
        reply->abort();
        reply->deleteLater();
        if (errorMessage) {
            *errorMessage = QStringLiteral("模型请求超时（%1 秒）").arg(config.requestTimeout);
        }
        return {};
    }
    timer.stop();

    const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
    const QByteArray body = reply->readAll();
    const QNetworkReply::NetworkError networkError = reply->error();
    const QString networkErrorString = reply->errorString();
    reply->deleteLater();

    if (networkError != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
        if (errorMessage) {
            const QString bodyPreview = responseErrorMessage(body);
            *errorMessage = QStringLiteral("模型请求失败：HTTP %1 / %2 %3")
                .arg(statusCode)
                .arg(networkErrorString, bodyPreview);
        }
        return {};
    }

    QString parseError;
    const QString content = extractAssistantReply(body, &parseError);
    if (content.isEmpty()) {
        if (errorMessage) {
            *errorMessage = parseError.isEmpty() ? QStringLiteral("模型返回空回复") : parseError;
        }
        return {};
    }
    return content;
}

QString conversationMemoryRoleLabel(const QString& role) {
    if (role == QStringLiteral("user")) {
        return QStringLiteral("用户");
    }
    if (role == QStringLiteral("assistant")) {
        return QStringLiteral("角色");
    }
    return QStringLiteral("系统");
}

QString conversationMemoryTranscript(const QJsonArray& conversations) {
    QStringList lines;
    int included = 0;
    for (const QJsonValue& value : conversations) {
        const QJsonObject message = value.toObject();
        const QString role = message.value(QStringLiteral("role")).toString();
        if (role != QStringLiteral("user") && role != QStringLiteral("assistant") && role != QStringLiteral("system")) {
            continue;
        }

        QString content = message.value(QStringLiteral("content")).toString().trimmed();
        if (content.isEmpty()) {
            continue;
        }
        if (content.size() > 6000) {
            content = content.left(6000).trimmed() + QStringLiteral("…");
        }
        lines.append(QStringLiteral("[%1] %2").arg(conversationMemoryRoleLabel(role), content));
        ++included;
        if (included >= 80) {
            break;
        }
    }

    QString transcript = lines.join(QStringLiteral("\n\n"));
    if (transcript.size() > 48000) {
        transcript = transcript.right(48000).trimmed();
    }
    return transcript;
}

QString conversationMemorySystemPrompt() {
    return QStringLiteral(
        "你是 Fantareal 的长期记忆整理器。\n"
        "请把一次聊天结束时的对话整理为一个长期记忆词条。\n"
        "要求：\n"
        "1. 只记录对未来角色扮演有帮助的事实、关系变化、承诺、偏好、冲突、情绪走向和重要事件。\n"
        "2. 不要逐字复述整段聊天，不要加入对话中没有的信息。\n"
        "3. content 使用中文自然段，保留角色名和用户称呼。\n"
        "4. tags 最多 6 个短标签。\n"
        "5. 只输出合法 JSON 对象，不输出 Markdown，不输出解释。\n"
        "JSON 字段：title, content, tags, notes。");
}

QJsonArray conversationMemoryMessages(const QDir& root, const QJsonArray& conversations) {
    const QJsonObject card = readJsonObject(root, QStringLiteral("data/current_role_card.json"), nullptr);
    const QJsonObject rawCard = card.value(QStringLiteral("raw")).toObject();
    const QJsonObject userProfile = readJsonObject(root, QStringLiteral("data/user_profile.json"), nullptr);

    QStringList userLines;
    appendPromptLine(&userLines, QStringLiteral("当前角色"), promptField(rawCard, QStringLiteral("name"), 200));
    appendPromptLine(&userLines, QStringLiteral("用户昵称"), promptField(userProfile, QStringLiteral("nickname"), 200));
    userLines.append(QStringLiteral("请总结以下对话为一个长期记忆词条："));
    userLines.append(conversationMemoryTranscript(conversations));

    QJsonArray messages;
    messages.append(modelMessage(QStringLiteral("system"), conversationMemorySystemPrompt()));
    messages.append(modelMessage(QStringLiteral("user"), userLines.join(QStringLiteral("\n\n"))));
    return messages;
}

QJsonArray tagsFromMemorySummary(const QJsonValue& value) {
    QJsonArray result;
    QStringList tags;
    if (value.isArray()) {
        for (const QJsonValue& item : value.toArray()) {
            const QString tag = item.toString().trimmed();
            if (!tag.isEmpty()) {
                tags.append(tag.left(32));
            }
        }
    } else {
        const QStringList parts = value.toString().split(QRegularExpression(QStringLiteral("[,，、;；\\s]+")), Qt::SkipEmptyParts);
        for (const QString& part : parts) {
            const QString tag = part.trimmed();
            if (!tag.isEmpty()) {
                tags.append(tag.left(32));
            }
        }
    }

    tags.removeDuplicates();
    for (const QString& tag : tags) {
        result.append(tag);
        if (result.size() >= 6) {
            break;
        }
    }
    if (result.isEmpty()) {
        result.append(QStringLiteral("对话总结"));
    }
    return result;
}

QJsonObject parseConversationMemorySummary(const QString& rawSummary) {
    const QString stripped = stripJsonCodeFence(rawSummary);
    QStringList candidates{ stripped };
    const int objectStart = stripped.indexOf(QLatin1Char('{'));
    const int objectEnd = stripped.lastIndexOf(QLatin1Char('}'));
    if (objectStart >= 0 && objectEnd > objectStart) {
        const QString extracted = stripped.mid(objectStart, objectEnd - objectStart + 1).trimmed();
        if (extracted != stripped) {
            candidates.append(extracted);
        }
    }

    for (const QString& candidate : candidates) {
        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(candidate.toUtf8(), &parseError);
        if (parseError.error == QJsonParseError::NoError && document.isObject()) {
            return document.object();
        }
    }
    return {};
}

QVariantMap memoryDraftFromSummary(const QString& rawSummary, const QString& transcript) {
    const QJsonObject summary = parseConversationMemorySummary(rawSummary);
    const QString fallbackTitle = QStringLiteral("对话总结 %1").arg(QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm")));
    QString title = summary.value(QStringLiteral("title")).toString().trimmed();
    QString content = summary.value(QStringLiteral("content")).toString().trimmed();
    QString notes = summary.value(QStringLiteral("notes")).toString().trimmed();
    QJsonArray tags = tagsFromMemorySummary(summary.value(QStringLiteral("tags")));

    if (title.isEmpty()) {
        title = fallbackTitle;
    }
    if (content.isEmpty()) {
        content = rawSummary.trimmed();
    }
    if (content.isEmpty()) {
        content = QStringLiteral("本次对话摘要：\n%1").arg(clippedText(transcript, 2000, QStringLiteral("无内容")));
    }
    if (notes.isEmpty()) {
        notes = QStringLiteral("由结束对话功能从当前聊天上下文生成。");
    }

    QStringList tagList;
    for (const QJsonValue& tag : tags) {
        tagList.append(tag.toString());
    }

    QVariantMap draft;
    draft.insert(QStringLiteral("title"), title.left(160));
    draft.insert(QStringLiteral("content"), content.left(12000));
    draft.insert(QStringLiteral("notes"), notes.left(2400));
    draft.insert(QStringLiteral("tagsText"), tagList.join(QStringLiteral(", ")));
    draft.insert(QStringLiteral("memory_status"), QStringLiteral("active"));
    return draft;
}

QString demoAssistantReply(const QDir& root, const QString& userMessage) {
    const QJsonObject card = readJsonObject(root, QStringLiteral("data/current_role_card.json"), nullptr);
    const QString cardName = card.value(QStringLiteral("raw")).toObject().value(QStringLiteral("name")).toString().trimmed();
    const QJsonObject persona = readJsonObject(root, QStringLiteral("data/persona.json"), nullptr);
    const QString personaName = persona.value(QStringLiteral("name")).toString().trimmed();
    const QString name = displayText(cardName.isEmpty() ? personaName : cardName, QStringLiteral("Fantareal"));
    return QStringLiteral("（演示模式）%1 已收到你的消息：“%2”。请在设置页配置 LLM Base URL 和模型名后，我会切换到真实模型回复。")
        .arg(name, clippedText(userMessage, 120, QStringLiteral("")));
}

QString roleCardField(const QJsonObject& card, const QString& key, int maxLength = 12000) {
    QString value = card.value(key).toString().trimmed();
    if (value.size() > maxLength) {
        value = value.left(maxLength).trimmed();
    }
    return value;
}

QJsonObject roleCardRawObject(const QJsonObject& card) {
    const QJsonObject wrappedRaw = card.value(QStringLiteral("raw")).toObject();
    return wrappedRaw.isEmpty() ? card : wrappedRaw;
}

bool hasUsableRoleCardContent(const QJsonObject& raw) {
    if (raw.isEmpty()) {
        return false;
    }
    const QStringList textKeys = {
        QStringLiteral("name"),
        QStringLiteral("description"),
        QStringLiteral("personality"),
        QStringLiteral("scenario"),
        QStringLiteral("first_mes"),
        QStringLiteral("mes_example"),
        QStringLiteral("creator_notes"),
    };
    for (const QString& key : textKeys) {
        if (!roleCardField(raw, key, 12000).isEmpty()) {
            return true;
        }
    }
    return !raw.value(QStringLiteral("personas")).toObject().isEmpty()
        || !raw.value(QStringLiteral("stateJournal")).toObject().isEmpty();
}

QString normalizedLibraryRelativePath(QString relativePath) {
    relativePath = relativePath.trimmed();
    relativePath.replace(QLatin1Char('\\'), QLatin1Char('/'));
    return QDir::cleanPath(relativePath);
}

bool isAllowedCardLibraryPath(
    const QDir& root,
    const QString& relativePath,
    QString* normalizedPath,
    QString* errorMessage) {
    const QString cleaned = normalizedLibraryRelativePath(relativePath);
    if (cleaned.isEmpty()
        || QFileInfo(cleaned).isAbsolute()
        || cleaned == QStringLiteral(".")
        || cleaned.startsWith(QStringLiteral("../"))
        || cleaned.contains(QStringLiteral("/../"))
        || !cleaned.endsWith(QStringLiteral(".json"), Qt::CaseInsensitive)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("角色卡路径无效");
        }
        return false;
    }

    const QStringList allowedDirs = {
        QStringLiteral("cards"),
        QStringLiteral("assets/人设卡"),
    };
    bool allowedPrefix = false;
    for (const QString& allowedDir : allowedDirs) {
        if (cleaned == allowedDir || cleaned.startsWith(allowedDir + QLatin1Char('/'))) {
            allowedPrefix = true;
            break;
        }
    }
    if (!allowedPrefix) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("只能激活 cards/ 或 assets/人设卡/ 下的 JSON 角色卡");
        }
        return false;
    }

    const QFileInfo fileInfo(root.absoluteFilePath(cleaned));
    QString canonicalFile = fileInfo.canonicalFilePath();
    canonicalFile.replace(QLatin1Char('\\'), QLatin1Char('/'));
    if (!fileInfo.isFile() || canonicalFile.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("角色卡文件不存在");
        }
        return false;
    }

    bool insideAllowedDir = false;
    for (const QString& allowedDir : allowedDirs) {
        QString canonicalDir = QFileInfo(root.absoluteFilePath(allowedDir)).canonicalFilePath();
        canonicalDir.replace(QLatin1Char('\\'), QLatin1Char('/'));
        if (!canonicalDir.isEmpty()
            && (canonicalFile == canonicalDir
                || canonicalFile.startsWith(canonicalDir + QLatin1Char('/')))) {
            insideAllowedDir = true;
            break;
        }
    }
    if (!insideAllowedDir) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("角色卡路径越界，已拒绝");
        }
        return false;
    }

    if (normalizedPath) {
        *normalizedPath = cleaned;
    }
    return true;
}

QString relativePathFromRoot(const QDir& root, const QString& absolutePath) {
    QString relative = root.relativeFilePath(absolutePath);
    relative.replace(QLatin1Char('\\'), QLatin1Char('/'));
    return QDir::cleanPath(relative);
}

QJsonObject activatedRoleCardStore(const QJsonObject& source, const QString& relativePath) {
    QJsonObject raw = roleCardRawObject(source);
    QJsonObject result = source.value(QStringLiteral("raw")).isObject() ? source : QJsonObject{};
    result.insert(QStringLiteral("raw"), raw);
    result.insert(QStringLiteral("source_name"), QFileInfo(relativePath).fileName());
    result.insert(QStringLiteral("source_path"), relativePath);
    if (result.value(QStringLiteral("card_uid")).toString().trimmed().isEmpty()) {
        const QString sourceUid = source.value(QStringLiteral("card_uid")).toString(
            raw.value(QStringLiteral("card_uid")).toString(
                raw.value(QStringLiteral("uid")).toString(
                    raw.value(QStringLiteral("id")).toString())));
        result.insert(QStringLiteral("card_uid"), displayText(sourceUid, normalizedCardRuntimeKey(QFileInfo(relativePath).completeBaseName())));
    }
    return result;
}

void appendPersonaSection(QStringList* sections, const QString& title, const QString& body) {
    if (!sections || body.trimmed().isEmpty()) {
        return;
    }
    sections->append(QStringLiteral("%1: %2").arg(title, body.trimmed()));
}

QJsonObject personaFromRoleCard(const QJsonObject& rawCard) {
    QStringList sections;
    appendPersonaSection(&sections, QStringLiteral("Character Description"), roleCardField(rawCard, QStringLiteral("description")));
    appendPersonaSection(&sections, QStringLiteral("Personality"), roleCardField(rawCard, QStringLiteral("personality")));
    appendPersonaSection(&sections, QStringLiteral("Scenario"), roleCardField(rawCard, QStringLiteral("scenario")));
    appendPersonaSection(&sections, QStringLiteral("Creator Notes"), roleCardField(rawCard, QStringLiteral("creator_notes")));
    appendPersonaSection(&sections, QStringLiteral("Dialogue Example"), roleCardField(rawCard, QStringLiteral("mes_example")));

    const QJsonObject personas = rawCard.value(QStringLiteral("personas")).toObject();
    QStringList personaLines;
    QStringList personaNames;
    for (auto it = personas.constBegin(); it != personas.constEnd(); ++it) {
        if (!it.value().isObject()) {
            continue;
        }

        const QJsonObject persona = it.value().toObject();
        const QString fallbackName = QStringLiteral("Persona %1").arg(it.key());
        const QString name = displayText(roleCardField(persona, QStringLiteral("name"), 160), fallbackName);
        personaNames.append(name);

        const QStringList details = {
            roleCardField(persona, QStringLiteral("description")),
            roleCardField(persona, QStringLiteral("personality")),
            roleCardField(persona, QStringLiteral("scenario")),
        };
        QStringList cleanDetails;
        for (const QString& detail : details) {
            if (!detail.isEmpty()) {
                cleanDetails.append(detail);
            }
        }
        if (!cleanDetails.isEmpty()) {
            personaLines.append(QStringLiteral("%1: %2").arg(name, cleanDetails.join(QStringLiteral("; "))));
        }
    }

    if (!personaLines.isEmpty()) {
        if (personaNames.size() >= 3) {
            sections.append(QStringLiteral(
                "Multi-Character Cast Rules:\n"
                "This role card contains multiple active characters.\n"
                "Every assistant turn must include all of these characters speaking: %1.\n"
                "Do not omit any of them.\n"
                "Do not merge different characters into one voice.\n"
                "Write each speaker in a separate paragraph.\n"
                "Use the exact format `Name: dialogue` for every paragraph.\n"
                "Keep the speaking order stable across turns unless the user clearly asks for a different order.\n"
                "Do not say that only one or two characters are present unless the user explicitly removes the others from the scene.")
                    .arg(personaNames.join(QStringLiteral(", "))));
        } else {
            sections.append(QStringLiteral(
                "Multi-Character Cast Rules:\n"
                "This role card contains multiple active characters.\n"
                "When the scene fits, any of them may appear and speak in the same conversation.\n"
                "Keep each character's name exactly as listed.\n"
                "Do not merge different characters into one voice.\n"
                "Write each speaker in separate paragraphs."));
        }
        sections.append(QStringLiteral("Character Cast:\n%1").arg(personaLines.join(QStringLiteral("\n"))));
    }

    QJsonObject persona;
    persona.insert(QStringLiteral("name"), displayText(roleCardField(rawCard, QStringLiteral("name"), 160), QStringLiteral("Unnamed Character")));
    persona.insert(QStringLiteral("greeting"), displayText(roleCardField(rawCard, QStringLiteral("first_mes")), QStringLiteral("Hello, let's start chatting.")));
    persona.insert(QStringLiteral("system_prompt"), sections.join(QStringLiteral("\n\n")).trimmed());
    return persona;
}

QString backupJsonFile(const QDir& root, const QString& relativePath, const QString& prefix, QString* errorMessage) {
    const QString sourcePath = root.absoluteFilePath(relativePath);
    QDir backupDir(root.absoluteFilePath(QStringLiteral("data/backups")));
    if (!backupDir.exists() && !backupDir.mkpath(QStringLiteral("."))) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法创建备份目录：%1").arg(backupDir.absolutePath());
        }
        return {};
    }

    const QString backupName = QStringLiteral("%1.%2.json.bak")
        .arg(prefix, QDateTime::currentDateTime().toString(QStringLiteral("yyyyMMdd-HHmmss-zzz")));
    const QString backupPath = backupDir.absoluteFilePath(backupName);
    if (!QFile::copy(sourcePath, backupPath)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("无法创建 %1 备份").arg(relativePath);
        }
        return {};
    }
    return backupPath;
}

QString saveChatConversationsWithBackup(
    const QDir& root,
    const QString& relativePath,
    const QJsonArray& conversations,
    QString* errorMessage) {
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("conversations"), errorMessage);
    if (backupPath.isEmpty()) {
        return {};
    }

    QSaveFile saveFile(root.absoluteFilePath(relativePath));
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString());
        }
        return {};
    }

    const QByteArray payload = QJsonDocument(conversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString());
        }
        return {};
    }
    if (!saveFile.commit()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString());
        }
        return {};
    }

    return backupPath;
}
}

FantarealBridge::FantarealBridge(QObject* parent)
    : QObject(parent)
    , chatNetwork_(new QNetworkAccessManager(this))
    , chatTimer_(new QTimer(this)) {
    chatTimer_->setSingleShot(true);

    const QString envRoot = qEnvironmentVariable("FANTAREAL_ROOT");
    if (!envRoot.trimmed().isEmpty() && QFileInfo(envRoot).isDir()) {
        legacyRoot_ = QDir(envRoot).absolutePath();
    }

    if (legacyRoot_.isEmpty()) {
        const QDir appDir(QCoreApplication::applicationDirPath());
        QDir probe(appDir);
        for (int i = 0; i < 6; ++i) {
            const bool hasRuntimeData = probe.exists("data/settings.json");
            const bool hasRootMarker = probe.exists(".fantareal-root")
                || probe.exists("Fantareal PC.bat")
                || probe.exists("fantareal-pc-计划书.md");
            if (hasRuntimeData && hasRootMarker) {
                legacyRoot_ = probe.absolutePath();
                break;
            }
            probe.cdUp();
        }
    }

    if (legacyRoot_.isEmpty()) {
        legacyRoot_ = QDir::fromNativeSeparators(QStringLiteral(FANTAREAL_DEFAULT_ROOT));
    }
    refreshLegacyScan();
}

QString FantarealBridge::legacyRoot() const {
    return legacyRoot_;
}

int FantarealBridge::criticalFileCount() const {
    return criticalFileCount_;
}

int FantarealBridge::criticalFileFoundCount() const {
    return criticalFileFoundCount_;
}

int FantarealBridge::assetDirCount() const {
    return assetDirCount_;
}

int FantarealBridge::assetDirFoundCount() const {
    return assetDirFoundCount_;
}

int FantarealBridge::cardFileCount() const {
    return cardFileCount_;
}

int FantarealBridge::assetFileCount() const {
    return assetFileCount_;
}

int FantarealBridge::pluginManifestCount() const {
    return pluginManifestCount_;
}

double FantarealBridge::criticalFilePercent() const {
    return criticalFilePercent_;
}

double FantarealBridge::assetDirPercent() const {
    return assetDirPercent_;
}

QString FantarealBridge::scanSummary() const {
    return scanSummary_;
}

QStringList FantarealBridge::foundLegacyItems() const {
    return foundLegacyItems_;
}

QStringList FantarealBridge::missingLegacyItems() const {
    return missingLegacyItems_;
}

QVariantMap FantarealBridge::settingsDraft() const {
    return settingsDraft_;
}

double FantarealBridge::backgroundImagePreviewOpacity() const {
    return backgroundImagePreviewOpacity_;
}

QVariantMap FantarealBridge::routeDraft() const {
    return routeDraft_;
}

QVariantMap FantarealBridge::cardDraft() const {
    return cardDraft_;
}

QVariantMap FantarealBridge::presetDraft() const {
    return presetDraft_;
}

QVariantMap FantarealBridge::worldbookDraft() const {
    return worldbookDraft_;
}

QVariantList FantarealBridge::worldbookEntryDrafts() const {
    return worldbookEntryDrafts_;
}

QVariantList FantarealBridge::memoryDrafts() const {
    return memoryDrafts_;
}

QStringList FantarealBridge::settingsRows() const {
    return settingsRows_;
}

QStringList FantarealBridge::routeRows() const {
    return routeRows_;
}

QStringList FantarealBridge::cardRows() const {
    return cardRows_;
}

QStringList FantarealBridge::presetRows() const {
    return presetRows_;
}

QStringList FantarealBridge::worldbookRows() const {
    return worldbookRows_;
}

QVariantList FantarealBridge::chatMessages() const {
    return chatMessages_;
}

QStringList FantarealBridge::chatRows() const {
    return chatRows_;
}

QStringList FantarealBridge::memoryRows() const {
    return memoryRows_;
}

QString FantarealBridge::settingsStatus() const {
    return settingsStatus_;
}

QString FantarealBridge::routeStatus() const {
    return routeStatus_;
}

QString FantarealBridge::cardStatus() const {
    return cardStatus_;
}

QString FantarealBridge::presetStatus() const {
    return presetStatus_;
}

QString FantarealBridge::worldbookStatus() const {
    return worldbookStatus_;
}

QString FantarealBridge::chatStatus() const {
    return chatStatus_;
}

QString FantarealBridge::memoryStatus() const {
    return memoryStatus_;
}

bool FantarealBridge::chatGenerating() const {
    return chatGenerating_;
}

QString FantarealBridge::chatGenerationStatus() const {
    return chatGenerationStatus_;
}

QString FantarealBridge::chatStreamingPreview() const {
    return chatStreamingPreview_;
}

bool FantarealBridge::firstLaunchDisclaimerRequired() const {
    return !settingsDraft_.value(QStringLiteral("first_launch_disclaimer_accepted")).toBool()
        || settingsDraft_.value(QStringLiteral("disclaimer_version")).toString() != firstLaunchDisclaimerVersion();
}

QString FantarealBridge::firstLaunchDisclaimerVersion() const {
    return QString::fromLatin1(kFirstLaunchDisclaimerVersion);
}

QString FantarealBridge::firstLaunchConfirmationText() const {
    return firstLaunchConfirmationTextLiteral();
}

QString FantarealBridge::buildInfo() const {
    return QStringLiteral("Qt 6 + QML + HuskarUI.Basic");
}

void FantarealBridge::previewBackgroundImageOpacity(double opacity) {
    backgroundImagePreviewOpacity_ = qBound(0.0, opacity, 1.0);
    emit scanChanged();
}

QVariantMap FantarealBridge::acceptFirstLaunchDisclaimer(const QString& ageGroup, const QString& typedConfirmation) {
    const QString normalizedAgeGroup = ageGroup.trimmed();
    const bool validAgeGroup = normalizedAgeGroup == QStringLiteral("under_14")
        || normalizedAgeGroup == QStringLiteral("14_to_17")
        || normalizedAgeGroup == QStringLiteral("18_plus");
    if (!validAgeGroup) {
        return resultMap(false, QStringLiteral("请选择年龄段"));
    }
    if (normalizedConfirmationText(typedConfirmation) != normalizedConfirmationText(firstLaunchConfirmationTextLiteral())) {
        return resultMap(false, QStringLiteral("确认语不一致"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/settings.json");
    const QString settingsPath = root.absoluteFilePath(relativePath);
    QString readError;
    QJsonObject settings = readJsonObjectFile(settingsPath, &readError);
    if (settings.isEmpty()) {
        return resultMap(false, QStringLiteral("settings.json 无法读取：%1").arg(readError));
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("settings"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    const bool minorModeEnabled = normalizedAgeGroup != QStringLiteral("18_plus");
    const QByteArray confirmationHash = QCryptographicHash::hash(
        typedConfirmation.toUtf8(),
        QCryptographicHash::Sha256).toHex();
    settings.insert(QStringLiteral("first_launch_disclaimer_accepted"), true);
    settings.insert(QStringLiteral("accepted_at"), QDateTime::currentDateTime().toString(Qt::ISODate));
    settings.insert(QStringLiteral("disclaimer_version"), firstLaunchDisclaimerVersion());
    settings.insert(QStringLiteral("age_group"), normalizedAgeGroup);
    settings.insert(QStringLiteral("minor_mode_enabled"), minorModeEnabled);
    settings.insert(QStringLiteral("typed_confirmation_hash"), QString::fromLatin1(confirmationHash));

    QString writeError;
    if (!writeJsonDocument(settingsPath, QJsonDocument(settings), &writeError)) {
        return resultMap(false, QStringLiteral("settings.json %1").arg(writeError), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("首次使用声明已确认"), backupPath);
    result.insert(QStringLiteral("minorModeEnabled"), minorModeEnabled);
    result.insert(QStringLiteral("ageGroup"), normalizedAgeGroup);
    return result;
}

QVariantMap FantarealBridge::saveSettingsDraft(const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/settings.json");
    const QString settingsPath = root.absoluteFilePath(relativePath);

    QFile file(settingsPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("settings.json 不存在，无法保存"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("settings.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("settings.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject settings = document.object();
    settings.insert(QStringLiteral("llm_base_url"),
        draftString(draft, QStringLiteral("llm_base_url"), settings.value("llm_base_url").toString(), 2048));
    settings.insert(QStringLiteral("llm_model"),
        draftString(draft, QStringLiteral("llm_model"), settings.value("llm_model").toString(), 256));
    settings.insert(QStringLiteral("theme"), normalizedTheme(draft, settings));
    settings.insert(QStringLiteral("background_image_path"), normalizedBackgroundPath(draft, settings));
    settings.insert(QStringLiteral("background_image_opacity"),
        draftNumber(draft, QStringLiteral("background_image_opacity"), settings.value("background_image_opacity").toDouble(0.42), 0.0, 1.0));
    settings.insert(QStringLiteral("temperature"),
        draftNumber(draft, QStringLiteral("temperature"), settings.value("temperature").toDouble(0.85), 0.0, 2.0));
    settings.insert(QStringLiteral("history_limit"),
        draftInt(draft, QStringLiteral("history_limit"), settings.value("history_limit").toInt(20), 1, 100));
    settings.insert(QStringLiteral("request_timeout"),
        draftInt(draft, QStringLiteral("request_timeout"), settings.value("request_timeout").toInt(120), 10, 600));
    settings.insert(QStringLiteral("demo_mode"),
        draft.value(QStringLiteral("demo_mode"), settings.value("demo_mode").toBool(false)).toBool());
    settings.insert(QStringLiteral("output_splitting_enabled"),
        draft.value(QStringLiteral("output_splitting_enabled"), settings.value("output_splitting_enabled").toBool(true)).toBool());
    settings.insert(QStringLiteral("embedding_base_url"),
        draftString(draft, QStringLiteral("embedding_base_url"), settings.value("embedding_base_url").toString(), 2048));
    settings.insert(QStringLiteral("embedding_model"),
        draftString(draft, QStringLiteral("embedding_model"), settings.value("embedding_model").toString(), 256));
    settings.insert(QStringLiteral("retrieval_top_k"),
        draftInt(draft, QStringLiteral("retrieval_top_k"), settings.value("retrieval_top_k").toInt(4), 1, 12));
    settings.insert(QStringLiteral("rerank_enabled"),
        draft.value(QStringLiteral("rerank_enabled"), settings.value("rerank_enabled").toBool()).toBool());
    settings.insert(QStringLiteral("rerank_base_url"),
        draftString(draft, QStringLiteral("rerank_base_url"), settings.value("rerank_base_url").toString(), 2048));
    settings.insert(QStringLiteral("rerank_model"),
        draftString(draft, QStringLiteral("rerank_model"), settings.value("rerank_model").toString(), 256));
    settings.insert(QStringLiteral("rerank_top_n"),
        draftInt(draft, QStringLiteral("rerank_top_n"), settings.value("rerank_top_n").toInt(3), 1, 12));
    settings.insert(QStringLiteral("memory_summary_length"), normalizedSummaryLength(draft, settings));
    settings.insert(QStringLiteral("memory_summary_max_chars"),
        draftInt(draft, QStringLiteral("memory_summary_max_chars"), settings.value("memory_summary_max_chars").toInt(520), 80, 2000));

    setSecretIfProvided(&settings, draft, QStringLiteral("llm_api_key"));
    setSecretIfProvided(&settings, draft, QStringLiteral("embedding_api_key"));
    setSecretIfProvided(&settings, draft, QStringLiteral("rerank_api_key"));

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("settings"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(settingsPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("settings.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(settings).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("settings.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("settings.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("设置已保存，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::saveRouteDraft(const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/route_forwarding.json");
    const QString routesPath = root.absoluteFilePath(relativePath);

    QFile file(routesPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 不存在，无法保存模型路由"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("route_forwarding.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject routes = document.object();
    routes.insert(QStringLiteral("enabled"),
        draft.value(QStringLiteral("enabled"), routes.value(QStringLiteral("enabled")).toBool(false)).toBool());
    routes.insert(QStringLiteral("hook_all_posts"),
        draft.value(QStringLiteral("hook_all_posts"), routes.value(QStringLiteral("hook_all_posts")).toBool(true)).toBool());
    routes.insert(QStringLiteral("failover_enabled"),
        draft.value(QStringLiteral("failover_enabled"), routes.value(QStringLiteral("failover_enabled")).toBool(true)).toBool());
    routes.insert(QStringLiteral("rotate_keys"),
        draft.value(QStringLiteral("rotate_keys"), routes.value(QStringLiteral("rotate_keys")).toBool(true)).toBool());
    routes.insert(QStringLiteral("retry_attempts"),
        draftInt(draft, QStringLiteral("retry_attempts"), routes.value(QStringLiteral("retry_attempts")).toInt(3), 1, 10));
    routes.insert(QStringLiteral("strategy"), normalizedRouteStrategy(draft, routes));

    if (!routes.value(QStringLiteral("providers")).isArray()) {
        routes.insert(QStringLiteral("providers"), QJsonArray{});
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("route_forwarding"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(routesPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(routes).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("模型路由已保存，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::saveRouteProviderDraft(int providerIndex, const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/route_forwarding.json");
    const QString routesPath = root.absoluteFilePath(relativePath);

    QString readError;
    QJsonObject routes = readJsonObjectFile(routesPath, &readError);
    if (!readError.isEmpty()) {
        return resultMap(false, QStringLiteral("route_forwarding.json %1").arg(readError));
    }

    QJsonArray providers = routes.value(QStringLiteral("providers")).toArray();
    const bool isNewProvider = providerIndex < 0;
    if (!isNewProvider && (providerIndex >= providers.size() || !providers.at(providerIndex).isObject())) {
        return resultMap(false, QStringLiteral("Provider 索引无效，无法保存"));
    }

    const int targetIndex = isNewProvider ? providers.size() : providerIndex;
    const QJsonObject current = isNewProvider ? QJsonObject{} : providers.at(providerIndex).toObject();
    QString providerError;
    const QJsonObject savedProvider = sanitizedRouteProviderFromDraft(draft, current, targetIndex, isNewProvider, &providerError);
    if (savedProvider.isEmpty()) {
        return resultMap(false, providerError.isEmpty() ? QStringLiteral("Provider 内容无效") : providerError);
    }

    const QString providerId = savedProvider.value(QStringLiteral("id")).toString();
    for (int i = 0; i < providers.size(); ++i) {
        if (i != providerIndex && providers.at(i).toObject().value(QStringLiteral("id")).toString() == providerId) {
            return resultMap(false, QStringLiteral("Provider ID 已存在，无法保存"));
        }
    }

    if (isNewProvider) {
        providers.append(savedProvider);
    } else {
        providers.replace(providerIndex, savedProvider);
    }
    routes.insert(QStringLiteral("providers"), providers);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("route_forwarding"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(routesPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(routes).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(
        true,
        isNewProvider ? QStringLiteral("Provider 已新增，旧路由已备份") : QStringLiteral("Provider 已保存，旧路由已备份"),
        backupPath);
    result.insert(QStringLiteral("providerIndex"), targetIndex);
    return result;
}

QVariantMap FantarealBridge::deleteRouteProvider(int providerIndex) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/route_forwarding.json");
    const QString routesPath = root.absoluteFilePath(relativePath);

    QString readError;
    QJsonObject routes = readJsonObjectFile(routesPath, &readError);
    if (!readError.isEmpty()) {
        return resultMap(false, QStringLiteral("route_forwarding.json %1").arg(readError));
    }

    QJsonArray providers = routes.value(QStringLiteral("providers")).toArray();
    if (providerIndex < 0 || providerIndex >= providers.size()) {
        return resultMap(false, QStringLiteral("Provider 索引无效，无法删除"));
    }
    providers.removeAt(providerIndex);
    routes.insert(QStringLiteral("providers"), providers);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("route_forwarding"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(routesPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(routes).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("Provider 已删除，旧路由已备份"), backupPath);
    result.insert(QStringLiteral("providerCount"), providers.size());
    return result;
}

QVariantMap FantarealBridge::saveRouteProviderKey(int providerIndex, const QString& newKey) {
    const QString key = newKey.trimmed();
    if (key.isEmpty()) {
        return resultMap(true, QStringLiteral("未输入新 Key，已保留现有 Provider 密钥"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/route_forwarding.json");
    const QString routesPath = root.absoluteFilePath(relativePath);

    QFile file(routesPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 不存在，无法保存 Provider Key"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("route_forwarding.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject routes = document.object();
    QJsonArray providers = routes.value(QStringLiteral("providers")).toArray();
    if (providerIndex < 0 || providerIndex >= providers.size()) {
        return resultMap(false, QStringLiteral("Provider 索引无效，无法保存 Key"));
    }

    QJsonObject provider = providers.at(providerIndex).toObject();
    if (provider.isEmpty()) {
        return resultMap(false, QStringLiteral("Provider 内容无效，无法保存 Key"));
    }

    provider.insert(QStringLiteral("keys"), QJsonArray{ key });
    provider.remove(QStringLiteral("api_key"));
    providers.replace(providerIndex, provider);
    routes.insert(QStringLiteral("providers"), providers);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("route_forwarding"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(routesPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("route_forwarding.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(routes).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("route_forwarding.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("Provider Key 已安全更新，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::saveCardDraft(const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/current_role_card.json");
    const QString cardPath = root.absoluteFilePath(relativePath);

    QFile file(cardPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("current_role_card.json 不存在，无法保存角色卡"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("current_role_card.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("current_role_card.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject card = document.object();
    QJsonObject raw = card.value(QStringLiteral("raw")).toObject();
    raw.insert(QStringLiteral("name"),
        draftString(draft, QStringLiteral("name"), raw.value(QStringLiteral("name")).toString(), 160));
    raw.insert(QStringLiteral("description"),
        draftString(draft, QStringLiteral("description"), raw.value(QStringLiteral("description")).toString(), 12000));
    raw.insert(QStringLiteral("personality"),
        draftString(draft, QStringLiteral("personality"), raw.value(QStringLiteral("personality")).toString(), 12000));
    raw.insert(QStringLiteral("scenario"),
        draftString(draft, QStringLiteral("scenario"), raw.value(QStringLiteral("scenario")).toString(), 12000));
    raw.insert(QStringLiteral("first_mes"),
        draftString(draft, QStringLiteral("first_mes"), raw.value(QStringLiteral("first_mes")).toString(), 12000));
    raw.insert(QStringLiteral("mes_example"),
        draftString(draft, QStringLiteral("mes_example"), raw.value(QStringLiteral("mes_example")).toString(), 12000));
    raw.insert(QStringLiteral("creator_notes"),
        draftString(draft, QStringLiteral("creator_notes"), raw.value(QStringLiteral("creator_notes")).toString(), 12000));
    raw.insert(QStringLiteral("creator_comment"),
        draftString(draft, QStringLiteral("creator_comment"), raw.value(QStringLiteral("creator_comment")).toString(), 12000));
    raw.insert(QStringLiteral("tags"), cardTagsFromDraft(draft, raw.value(QStringLiteral("tags")).toArray()));

    QJsonObject stateJournal = raw.value(QStringLiteral("stateJournal")).toObject();
    if (draft.contains(QStringLiteral("stateJournalEnabled"))) {
        stateJournal.insert(QStringLiteral("enabled"), draft.value(QStringLiteral("stateJournalEnabled")).toBool());
    }
    if (!stateJournal.isEmpty()) {
        raw.insert(QStringLiteral("stateJournal"), stateJournal);
    }

    QJsonObject workshop = raw.value(QStringLiteral("creativeWorkshop")).toObject();
    if (draft.contains(QStringLiteral("creativeWorkshopEnabled"))) {
        workshop.insert(QStringLiteral("enabled"), draft.value(QStringLiteral("creativeWorkshopEnabled")).toBool());
    }
    QJsonObject opening = workshop.value(QStringLiteral("opening")).toObject();
    if (draft.contains(QStringLiteral("openingEnabled"))) {
        opening.insert(QStringLiteral("enabled"), draft.value(QStringLiteral("openingEnabled")).toBool());
    }
    if (!opening.isEmpty()) {
        workshop.insert(QStringLiteral("opening"), opening);
    }
    if (!workshop.isEmpty()) {
        raw.insert(QStringLiteral("creativeWorkshop"), workshop);
    }

    card.insert(QStringLiteral("raw"), raw);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("current_role_card"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(cardPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("current_role_card.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(card).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("current_role_card.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("current_role_card.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("角色卡已保存，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::activateRoleCard(const QString& relativePath) {
    const QDir root(legacyRoot_);
    QString normalizedPath;
    QString pathError;
    if (!isAllowedCardLibraryPath(root, relativePath, &normalizedPath, &pathError)) {
        return resultMap(false, pathError);
    }

    QString readError;
    const QJsonObject source = readJsonObjectFile(root.absoluteFilePath(normalizedPath), &readError);
    const QJsonObject raw = roleCardRawObject(source);
    if (source.isEmpty()) {
        return resultMap(false, QStringLiteral("角色卡无法读取：%1").arg(readError));
    }
    if (!hasUsableRoleCardContent(raw)) {
        return resultMap(false, QStringLiteral("角色卡内容为空，无法激活"));
    }

    const QString currentRelativePath = QStringLiteral("data/current_role_card.json");
    const QString currentPath = root.absoluteFilePath(currentRelativePath);
    if (!QFileInfo::exists(currentPath)) {
        return resultMap(false, QStringLiteral("current_role_card.json 不存在，无法激活角色卡"));
    }

    QJsonObject currentCheck = readJsonObjectFile(currentPath, &readError);
    if (currentCheck.isEmpty() && !readError.isEmpty()) {
        return resultMap(false, QStringLiteral("current_role_card.json 无法读取：%1").arg(readError));
    }

    QJsonObject activated = activatedRoleCardStore(source, normalizedPath);
    QString backupError;
    const QString backupPath = backupJsonFile(root, currentRelativePath, QStringLiteral("current_role_card"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(currentPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("current_role_card.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(activated).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("current_role_card.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("current_role_card.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("角色卡已激活，旧 current_role_card 已备份"), backupPath);
    result.insert(QStringLiteral("sourcePath"), normalizedPath);
    return result;
}

QVariantMap FantarealBridge::importRoleCardFile(const QString& sourcePath) {
    const QDir root(legacyRoot_);
    const QString localPath = localFilePathFromInput(sourcePath);
    const QFileInfo sourceInfo(localPath);
    if (!sourceInfo.exists() || !sourceInfo.isFile()) {
        return resultMap(false, QStringLiteral("角色卡导入文件不存在"));
    }

    QString readError;
    const QJsonObject source = readJsonObjectFile(sourceInfo.absoluteFilePath(), &readError);
    const QJsonObject raw = roleCardRawObject(source);
    if (source.isEmpty()) {
        return resultMap(false, QStringLiteral("角色卡无法读取：%1").arg(readError));
    }
    if (!hasUsableRoleCardContent(raw)) {
        return resultMap(false, QStringLiteral("角色卡内容为空，无法导入"));
    }

    QString relativePath;
    const QString existingRelativePath = relativePathFromRoot(root, sourceInfo.absoluteFilePath());
    QString pathError;
    if (isAllowedCardLibraryPath(root, existingRelativePath, &relativePath, &pathError)) {
        // The file is already in the managed library.
    } else {
        QDir libraryDir(root.absoluteFilePath(QStringLiteral("assets/人设卡")));
        if (!libraryDir.exists() && !libraryDir.mkpath(QStringLiteral("."))) {
            return resultMap(false, QStringLiteral("无法创建人设卡导入目录"));
        }

        const QString fileName = safeImportFileName(sourceInfo.fileName(), roleCardField(raw, QStringLiteral("name"), 80));
        const QString destination = uniqueFilePathInDir(libraryDir, fileName);
        if (!QFile::copy(sourceInfo.absoluteFilePath(), destination)) {
            return resultMap(false, QStringLiteral("角色卡复制失败，无法导入"));
        }
        relativePath = relativePathFromRoot(root, destination);
    }

    const QString currentRelativePath = QStringLiteral("data/current_role_card.json");
    const QString currentPath = root.absoluteFilePath(currentRelativePath);
    if (!QFileInfo::exists(currentPath)) {
        return resultMap(false, QStringLiteral("current_role_card.json 不存在，无法激活导入角色卡"));
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, currentRelativePath, QStringLiteral("current_role_card"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QString writeError;
    if (!writeJsonDocument(currentPath, QJsonDocument(activatedRoleCardStore(source, relativePath)), &writeError)) {
        return resultMap(false, QStringLiteral("current_role_card.json %1").arg(writeError), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("角色卡已导入并激活，旧文件已备份"), backupPath);
    result.insert(QStringLiteral("sourcePath"), relativePath);
    return result;
}

QVariantMap FantarealBridge::syncCurrentCardToPersona() {
    const QDir root(legacyRoot_);
    const QString cardRelativePath = QStringLiteral("data/current_role_card.json");
    const QString cardPath = root.absoluteFilePath(cardRelativePath);

    QFile cardFile(cardPath);
    if (!cardFile.exists()) {
        return resultMap(false, QStringLiteral("current_role_card.json 不存在，无法同步 Persona"));
    }
    if (!cardFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("current_role_card.json 无法读取：%1").arg(cardFile.errorString()));
    }

    QJsonParseError cardError;
    const QJsonDocument cardDocument = QJsonDocument::fromJson(cardFile.readAll(), &cardError);
    cardFile.close();
    if (cardError.error != QJsonParseError::NoError || !cardDocument.isObject()) {
        return resultMap(false, QStringLiteral("current_role_card.json JSON 无效：%1").arg(cardError.errorString()));
    }

    const QJsonObject card = cardDocument.object();
    if (!card.contains(QStringLiteral("raw")) || !card.value(QStringLiteral("raw")).isObject()) {
        return resultMap(false, QStringLiteral("current_role_card.json 缺少 raw 角色卡内容"));
    }

    const QJsonObject raw = card.value(QStringLiteral("raw")).toObject();
    const bool hasCoreContent =
        !roleCardField(raw, QStringLiteral("name"), 160).isEmpty()
        || !roleCardField(raw, QStringLiteral("description")).isEmpty()
        || !roleCardField(raw, QStringLiteral("personality")).isEmpty()
        || !roleCardField(raw, QStringLiteral("scenario")).isEmpty()
        || !roleCardField(raw, QStringLiteral("first_mes")).isEmpty()
        || !roleCardField(raw, QStringLiteral("mes_example")).isEmpty()
        || !roleCardField(raw, QStringLiteral("creator_notes")).isEmpty()
        || !raw.value(QStringLiteral("personas")).toObject().isEmpty();
    if (!hasCoreContent) {
        return resultMap(false, QStringLiteral("当前角色卡没有可同步的人格内容"));
    }

    const QString personaRelativePath = QStringLiteral("data/persona.json");
    const QString personaPath = root.absoluteFilePath(personaRelativePath);
    QFile personaFile(personaPath);
    if (!personaFile.exists()) {
        return resultMap(false, QStringLiteral("persona.json 不存在，无法同步 Persona"));
    }
    if (!personaFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("persona.json 无法读取：%1").arg(personaFile.errorString()));
    }

    QJsonParseError personaError;
    const QJsonDocument personaDocument = QJsonDocument::fromJson(personaFile.readAll(), &personaError);
    personaFile.close();
    if (personaError.error != QJsonParseError::NoError || !personaDocument.isObject()) {
        return resultMap(false, QStringLiteral("persona.json JSON 无效：%1").arg(personaError.errorString()));
    }

    QJsonObject persona = personaDocument.object();
    const QJsonObject generatedPersona = personaFromRoleCard(raw);
    persona.insert(QStringLiteral("name"), generatedPersona.value(QStringLiteral("name")));
    persona.insert(QStringLiteral("greeting"), generatedPersona.value(QStringLiteral("greeting")));
    persona.insert(QStringLiteral("system_prompt"), generatedPersona.value(QStringLiteral("system_prompt")));

    QString backupError;
    const QString backupPath = backupJsonFile(root, personaRelativePath, QStringLiteral("persona"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(personaPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("persona.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(persona).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("persona.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("persona.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("角色卡已同步到 Persona，旧 persona 已备份"), backupPath);
}

QVariantMap FantarealBridge::savePresetDraft(const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/preset.json");
    const QString presetPath = root.absoluteFilePath(relativePath);

    QFile file(presetPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("preset.json 不存在，无法保存预设"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("preset.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("preset.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject store = document.object();
    QJsonArray presets = store.value(QStringLiteral("presets")).toArray();
    if (presets.isEmpty()) {
        return resultMap(false, QStringLiteral("preset.json 中没有可保存的预设"));
    }

    const bool hasDraftPresetId = draft.contains(QStringLiteral("id"));
    QString activePresetId = draft.value(QStringLiteral("id")).toString().trimmed();
    if (activePresetId.isEmpty()) {
        activePresetId = store.value(QStringLiteral("active_preset_id")).toString();
    }

    const int presetIndex = findActivePresetIndex(presets, activePresetId);
    if (presetIndex < 0) {
        return resultMap(false, QStringLiteral("未找到活动预设，无法保存"));
    }

    QJsonObject activePreset = presets.at(presetIndex).toObject();
    const QString matchedPresetId = activePreset.value(QStringLiteral("id")).toString();
    if (hasDraftPresetId && activePresetId != matchedPresetId) {
        return resultMap(false, QStringLiteral("要保存的预设不存在或已切换"));
    }
    if (activePresetId.isEmpty() || activePresetId != matchedPresetId) {
        activePresetId = activePreset.value(QStringLiteral("id")).toString();
    }

    if (draft.contains(QStringLiteral("name"))) {
        QString name = draft.value(QStringLiteral("name")).toString().trimmed();
        if (name.size() > 64) {
            name = name.left(64);
        }
        if (name.isEmpty()) {
            name = activePreset.value(QStringLiteral("name")).toString(QStringLiteral("默认预设")).trimmed();
        }
        activePreset.insert(QStringLiteral("name"), name.isEmpty() ? QStringLiteral("默认预设") : name);
    }

    if (draft.contains(QStringLiteral("enabled"))) {
        activePreset.insert(QStringLiteral("enabled"), draft.value(QStringLiteral("enabled")).toBool());
    }

    QJsonObject modules = activePreset.value(QStringLiteral("modules")).toObject();
    for (const PresetModuleMeta& meta : presetModuleMetas()) {
        const QString key = QLatin1String(meta.key);
        if (!modules.contains(key)) {
            modules.insert(key, meta.defaultEnabled);
        }
    }

    const QVariantMap draftModules = draft.value(QStringLiteral("modules")).toMap();
    for (auto it = draftModules.constBegin(); it != draftModules.constEnd(); ++it) {
        if (isKnownPresetModule(it.key())) {
            modules.insert(it.key(), it.value().toBool());
        }
    }
    applyPresetModuleMutex(&modules);
    activePreset.insert(QStringLiteral("modules"), modules);
    applySubPresetDraft(&activePreset, draft);

    presets.replace(presetIndex, activePreset);
    store.insert(QStringLiteral("presets"), presets);
    if (!activePresetId.isEmpty()) {
        store.insert(QStringLiteral("active_preset_id"), activePresetId);
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("preset"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(presetPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("preset.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(store).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("preset.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("preset.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("预设已保存，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::importPresetFile(const QString& sourcePath) {
    const QDir root(legacyRoot_);
    const QString localPath = localFilePathFromInput(sourcePath);
    const QFileInfo sourceInfo(localPath);
    if (!sourceInfo.exists() || !sourceInfo.isFile()) {
        return resultMap(false, QStringLiteral("预设导入文件不存在"));
    }

    QString readError;
    const QJsonDocument importDocument = readJsonDocumentFile(sourceInfo.absoluteFilePath(), &readError);
    if (importDocument.isNull()) {
        return resultMap(false, QStringLiteral("预设无法读取：%1").arg(readError));
    }

    QString importError;
    const QJsonArray importedPresets = importedPresetArray(importDocument, sourceInfo.completeBaseName(), &importError);
    if (importedPresets.isEmpty()) {
        return resultMap(false, importError);
    }

    const QString relativePath = QStringLiteral("data/preset.json");
    const QString presetPath = root.absoluteFilePath(relativePath);
    QString currentError;
    QJsonObject store = readJsonObjectFile(presetPath, &currentError);
    if (store.isEmpty() && !currentError.isEmpty()) {
        return resultMap(false, QStringLiteral("preset.json 无法读取：%1").arg(currentError));
    }

    QJsonArray presets = store.value(QStringLiteral("presets")).toArray();
    QStringList existingIds;
    for (const QJsonValue& value : presets) {
        const QString id = value.toObject().value(QStringLiteral("id")).toString();
        if (!id.isEmpty()) {
            existingIds.append(id);
        }
    }

    QString lastAddedId;
    for (const QJsonValue& value : importedPresets) {
        QJsonObject preset = value.toObject();
        QString id = preset.value(QStringLiteral("id")).toString().trimmed();
        if (id.isEmpty() || existingIds.contains(id)) {
            id = generatedPresetId();
            preset.insert(QStringLiteral("id"), id);
        }
        existingIds.append(id);
        presets.append(preset);
        lastAddedId = id;
    }
    if (lastAddedId.isEmpty()) {
        return resultMap(false, QStringLiteral("未导入任何预设"));
    }

    store.insert(QStringLiteral("presets"), presets);
    store.insert(QStringLiteral("active_preset_id"), lastAddedId);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("preset"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QString writeError;
    if (!writeJsonDocument(presetPath, QJsonDocument(store), &writeError)) {
        return resultMap(false, QStringLiteral("preset.json %1").arg(writeError), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("预设已导入并激活，旧文件已备份"), backupPath);
    result.insert(QStringLiteral("presetId"), lastAddedId);
    return result;
}

QVariantMap FantarealBridge::saveWorldbookDraft(const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/worldbook.json");
    const QString worldbookPath = root.absoluteFilePath(relativePath);

    QFile file(worldbookPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("worldbook.json 不存在，无法保存世界书"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("worldbook.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("worldbook.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject worldbook = document.object();
    QJsonObject settings = worldbook.value(QStringLiteral("settings")).toObject();
    settings.insert(QStringLiteral("enabled"),
        draft.value(QStringLiteral("enabled"), settings.value(QStringLiteral("enabled")).toBool(true)).toBool());
    settings.insert(QStringLiteral("debug_enabled"),
        draft.value(QStringLiteral("debug_enabled"), settings.value(QStringLiteral("debug_enabled")).toBool(false)).toBool());
    settings.insert(QStringLiteral("max_hits"),
        draftInt(draft, QStringLiteral("max_hits"), settings.value(QStringLiteral("max_hits")).toInt(3), 1, 20));
    settings.insert(QStringLiteral("default_case_sensitive"),
        draft.value(QStringLiteral("default_case_sensitive"), settings.value(QStringLiteral("default_case_sensitive")).toBool(false)).toBool());
    settings.insert(QStringLiteral("default_whole_word"),
        draft.value(QStringLiteral("default_whole_word"), settings.value(QStringLiteral("default_whole_word")).toBool(false)).toBool());
    settings.insert(QStringLiteral("default_match_mode"),
        normalizedWorldbookMatchMode(draft, QStringLiteral("default_match_mode"), settings, QStringLiteral("any")));
    settings.insert(QStringLiteral("default_secondary_mode"),
        normalizedWorldbookMatchMode(draft, QStringLiteral("default_secondary_mode"), settings, QStringLiteral("all")));
    settings.insert(QStringLiteral("default_entry_type"), normalizedWorldbookEntryType(draft, settings));
    settings.insert(QStringLiteral("default_group_operator"), normalizedWorldbookGroupOperator(draft, settings));
    settings.insert(QStringLiteral("default_chance"),
        draftInt(draft, QStringLiteral("default_chance"), settings.value(QStringLiteral("default_chance")).toInt(100), 0, 100));
    settings.insert(QStringLiteral("default_sticky_turns"),
        draftInt(draft, QStringLiteral("default_sticky_turns"), settings.value(QStringLiteral("default_sticky_turns")).toInt(0), 0, 999));
    settings.insert(QStringLiteral("default_cooldown_turns"),
        draftInt(draft, QStringLiteral("default_cooldown_turns"), settings.value(QStringLiteral("default_cooldown_turns")).toInt(0), 0, 999));
    settings.insert(QStringLiteral("default_insertion_position"), normalizedWorldbookInsertionPosition(draft, settings));
    settings.insert(QStringLiteral("default_injection_depth"),
        draftInt(draft, QStringLiteral("default_injection_depth"), settings.value(QStringLiteral("default_injection_depth")).toInt(0), 0, 999));
    settings.insert(QStringLiteral("default_injection_role"), normalizedWorldbookInjectionRole(draft, settings));
    settings.insert(QStringLiteral("default_injection_order"),
        draftInt(draft, QStringLiteral("default_injection_order"), settings.value(QStringLiteral("default_injection_order")).toInt(100), 0, 999999));
    settings.insert(QStringLiteral("default_prompt_layer"), normalizedWorldbookPromptLayer(draft, settings));
    settings.insert(QStringLiteral("recursive_scan_enabled"),
        draft.value(QStringLiteral("recursive_scan_enabled"), settings.value(QStringLiteral("recursive_scan_enabled")).toBool(false)).toBool());
    settings.insert(QStringLiteral("recursion_max_depth"),
        draftInt(draft, QStringLiteral("recursion_max_depth"), settings.value(QStringLiteral("recursion_max_depth")).toInt(2), 0, 5));

    worldbook.insert(QStringLiteral("settings"), settings);
    if (!worldbook.value(QStringLiteral("entries")).isArray()) {
        worldbook.insert(QStringLiteral("entries"), QJsonArray{});
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("worldbook"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(worldbookPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("worldbook.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(worldbook).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("worldbook.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("worldbook.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("世界书设置已保存，旧文件已备份"), backupPath);
}

QVariantMap FantarealBridge::saveWorldbookEntry(int entryIndex, const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/worldbook.json");
    const QString worldbookPath = root.absoluteFilePath(relativePath);

    QFile file(worldbookPath);
    if (!file.exists()) {
        return resultMap(false, QStringLiteral("worldbook.json 不存在，无法保存世界书词条"));
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("worldbook.json 无法读取：%1").arg(file.errorString()));
    }

    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        return resultMap(false, QStringLiteral("worldbook.json JSON 无效：%1").arg(error.errorString()));
    }

    QJsonObject worldbook = document.object();
    const QJsonObject settings = worldbook.value(QStringLiteral("settings")).toObject();
    QJsonArray entries = worldbook.value(QStringLiteral("entries")).toArray();
    const bool isNewEntry = entryIndex < 0;
    if (!isNewEntry && (entryIndex >= entries.size() || !entries.at(entryIndex).isObject())) {
        return resultMap(false, QStringLiteral("世界书词条索引无效，无法保存"));
    }

    QString entryError;
    const int targetIndex = isNewEntry ? entries.size() : entryIndex;
    const QJsonObject current = isNewEntry ? QJsonObject{} : entries.at(entryIndex).toObject();
    const QJsonObject savedEntry = sanitizedWorldbookEntryFromDraft(draft, current, settings, targetIndex, isNewEntry, &entryError);
    if (savedEntry.isEmpty()) {
        return resultMap(false, entryError.isEmpty() ? QStringLiteral("世界书词条内容无效") : entryError);
    }

    if (isNewEntry) {
        entries.append(savedEntry);
    } else {
        entries.replace(entryIndex, savedEntry);
    }
    worldbook.insert(QStringLiteral("entries"), entries);

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("worldbook"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(worldbookPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("worldbook.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(worldbook).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("worldbook.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("worldbook.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(
        true,
        isNewEntry ? QStringLiteral("世界书词条已新增，旧文件已备份") : QStringLiteral("世界书词条已保存，旧文件已备份"),
        backupPath);
    result.insert(QStringLiteral("entryIndex"), targetIndex);
    return result;
}

QVariantMap FantarealBridge::importWorldbookFile(const QString& sourcePath) {
    const QDir root(legacyRoot_);
    const QString localPath = localFilePathFromInput(sourcePath);
    const QFileInfo sourceInfo(localPath);
    if (!sourceInfo.exists() || !sourceInfo.isFile()) {
        return resultMap(false, QStringLiteral("世界书导入文件不存在"));
    }

    QString readError;
    const QJsonDocument importDocument = readJsonDocumentFile(sourceInfo.absoluteFilePath(), &readError);
    if (importDocument.isNull()) {
        return resultMap(false, QStringLiteral("世界书无法读取：%1").arg(readError));
    }

    const QString relativePath = QStringLiteral("data/worldbook.json");
    const QString worldbookPath = root.absoluteFilePath(relativePath);
    QString currentError;
    const QJsonObject currentStore = readJsonObjectFile(worldbookPath, &currentError);
    if (currentStore.isEmpty() && !currentError.isEmpty()) {
        return resultMap(false, QStringLiteral("worldbook.json 无法读取：%1").arg(currentError));
    }

    QString importError;
    const QJsonObject importedStore = importedWorldbookStore(importDocument, currentStore, &importError);
    if (importedStore.isEmpty()) {
        return resultMap(false, importError);
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("worldbook"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QString writeError;
    if (!writeJsonDocument(worldbookPath, QJsonDocument(importedStore), &writeError)) {
        return resultMap(false, QStringLiteral("worldbook.json %1").arg(writeError), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(true, QStringLiteral("世界书已导入，旧文件已备份"), backupPath);
    result.insert(QStringLiteral("entryCount"), importedStore.value(QStringLiteral("entries")).toArray().size());
    return result;
}

QVariantMap FantarealBridge::saveMemoryEntry(int entryIndex, const QVariantMap& draft) {
    const QDir root(legacyRoot_);
    QString relativePath;
    QString pathError;
    if (!currentMemoryRelativePath(root, &relativePath, &pathError)) {
        return resultMap(false, pathError);
    }

    const QString memoryPath = root.absoluteFilePath(relativePath);
    const bool fileExists = QFileInfo::exists(memoryPath);
    QJsonArray entries;
    if (fileExists) {
        QString readError;
        if (!readJsonArrayFileStrict(memoryPath, &entries, &readError)) {
            return resultMap(false, QStringLiteral("memories.json %1").arg(readError));
        }
    }

    const bool isNewEntry = entryIndex < 0;
    if (!isNewEntry && (entryIndex >= entries.size() || !entries.at(entryIndex).isObject())) {
        return resultMap(false, QStringLiteral("记忆索引无效，无法保存"));
    }

    const int targetIndex = isNewEntry ? entries.size() : entryIndex;
    const QJsonObject current = isNewEntry ? QJsonObject{} : entries.at(entryIndex).toObject();
    QString entryError;
    const QJsonObject savedEntry = sanitizedMemoryEntryFromDraft(draft, current, targetIndex, isNewEntry, &entryError);
    if (savedEntry.isEmpty()) {
        return resultMap(false, entryError.isEmpty() ? QStringLiteral("记忆内容无效") : entryError);
    }

    if (isNewEntry) {
        entries.append(savedEntry);
    } else {
        entries.replace(entryIndex, savedEntry);
    }

    QString backupPath;
    if (fileExists) {
        QString backupError;
        backupPath = backupJsonFile(root, relativePath, QStringLiteral("memories"), &backupError);
        if (backupPath.isEmpty()) {
            return resultMap(false, backupError);
        }
    } else {
        const QFileInfo fileInfo(memoryPath);
        QDir parentDir = fileInfo.absoluteDir();
        if (!parentDir.exists() && !parentDir.mkpath(QStringLiteral("."))) {
            return resultMap(false, QStringLiteral("无法创建记忆目录：%1").arg(parentDir.absolutePath()));
        }
    }

    QSaveFile saveFile(memoryPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("memories.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(entries).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("memories.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("memories.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    QVariantMap result = resultMap(
        true,
        isNewEntry ? QStringLiteral("记忆已新增") : QStringLiteral("记忆已保存，旧文件已备份"),
        backupPath);
    result.insert(QStringLiteral("entryIndex"), targetIndex);
    result.insert(QStringLiteral("relativePath"), relativePath);
    return result;
}

QVariantMap FantarealBridge::sendChatMessage(const QString& message) {
    const QString content = sanitizedChatMessage(message);
    if (content.isEmpty()) {
        return resultMap(false, QStringLiteral("消息不能为空"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("conversations"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QJsonObject userMessage;
    userMessage.insert(QStringLiteral("role"), QStringLiteral("user"));
    userMessage.insert(QStringLiteral("content"), content);
    userMessage.insert(QStringLiteral("created_at"), QDateTime::currentDateTime().toString(QStringLiteral("yyyy-MM-dd HH:mm:ss")));
    userMessage.insert(QStringLiteral("message_id"), QUuid::createUuid().toString(QUuid::WithoutBraces));
    userMessage.insert(QStringLiteral("source"), QStringLiteral("huskarui"));
    conversations.append(userMessage);

    QSaveFile saveFile(conversationPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(conversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("消息已写入本地聊天历史"), backupPath);
}

QVariantMap FantarealBridge::sendChatMessageDemoReply(const QString& message) {
    const QString content = sanitizedChatMessage(message);
    if (content.isEmpty()) {
        return resultMap(false, QStringLiteral("消息不能为空"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    conversations.append(chatHistoryMessage(QStringLiteral("user"), content, QStringLiteral("huskarui")));
    const QString assistantContent = demoAssistantReply(root, content);
    conversations.append(chatHistoryMessage(
        QStringLiteral("assistant"),
        assistantContent,
        QStringLiteral("huskarui-demo"),
        outputPartsToJsonArray(fallbackOutputParts(assistantContent))));

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("conversations"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(conversationPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(conversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("本地演示回复已写入聊天历史"), backupPath);
}

void FantarealBridge::setChatGenerationState(bool generating, const QString& status) {
    if (chatGenerating_ == generating && chatGenerationStatus_ == status) {
        return;
    }
    chatGenerating_ = generating;
    chatGenerationStatus_ = status;
    emit chatGenerationChanged();
}

void FantarealBridge::setChatStreamingPreview(const QString& preview) {
    if (chatStreamingPreview_ == preview) {
        return;
    }
    chatStreamingPreview_ = preview;
    emit chatGenerationChanged();
}

void FantarealBridge::clearPendingChatRequest() {
    if (chatTimer_) {
        chatTimer_->stop();
        chatTimer_->disconnect(this);
    }
    if (chatReply_) {
        chatReply_->disconnect(this);
        chatReply_->deleteLater();
        chatReply_ = nullptr;
    }

    chatStreamingPreview_.clear();
    pendingChatResponseBuffer_.clear();
    pendingChatConversations_ = {};
    pendingChatConversationPath_.clear();
    pendingChatRelativePath_.clear();
    pendingChatAssistantSource_.clear();
    pendingChatSuccessMessage_.clear();
    pendingChatAbortMessage_.clear();
    pendingChatSawStream_ = false;
}

void FantarealBridge::finishPendingChatRequest(bool ok, const QString& message, const QString& backupPath) {
    const QVariantMap result = resultMap(ok, message, backupPath);
    clearPendingChatRequest();
    setChatGenerationState(false, {});
    emit chatGenerationFinished(result);
}

void FantarealBridge::completePendingChatRequest(const QString& assistantContent) {
    QJsonArray conversations = pendingChatConversations_;
    const QDir root(legacyRoot_);
    const QJsonArray displayParts = assistantDisplayParts(chatRuntimeConfig(root), assistantContent);
    conversations.append(chatHistoryMessage(QStringLiteral("assistant"), assistantContent, pendingChatAssistantSource_, displayParts));

    QString backupError;
    const QString backupPath = backupJsonFile(root, pendingChatRelativePath_, QStringLiteral("conversations"), &backupError);
    if (backupPath.isEmpty()) {
        finishPendingChatRequest(false, backupError);
        return;
    }

    QSaveFile saveFile(pendingChatConversationPath_);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        finishPendingChatRequest(false, QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
        return;
    }
    const QByteArray payload = QJsonDocument(conversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        finishPendingChatRequest(false, QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
        return;
    }
    if (!saveFile.commit()) {
        finishPendingChatRequest(false, QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
        return;
    }

    const QString successMessage = pendingChatSuccessMessage_;
    refreshLegacyScan();
    finishPendingChatRequest(true, successMessage, backupPath);
}

QVariantMap FantarealBridge::startPendingChatRequest(
    const QString& url,
    const QString& apiKey,
    int requestTimeout,
    const QJsonObject& payload,
    const QJsonArray& conversations,
    const QString& assistantSource,
    const QString& successMessage) {
    if (chatGenerating_) {
        return resultMap(false, QStringLiteral("已有聊天生成任务正在进行"));
    }
    if (url.trimmed().isEmpty()) {
        return resultMap(false, QStringLiteral("聊天模型 API URL 未配置"));
    }

    const QDir root(legacyRoot_);
    pendingChatRelativePath_ = QStringLiteral("data/conversations.json");
    pendingChatConversationPath_ = root.absoluteFilePath(pendingChatRelativePath_);
    pendingChatConversations_ = conversations;
    pendingChatAssistantSource_ = assistantSource;
    pendingChatSuccessMessage_ = successMessage;
    pendingChatAbortMessage_.clear();
    pendingChatResponseBuffer_.clear();
    pendingChatSawStream_ = false;
    setChatStreamingPreview({});

    QNetworkRequest request{ QUrl(url) };
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    request.setRawHeader("Accept", "text/event-stream, application/json");
    if (!apiKey.trimmed().isEmpty()) {
        request.setRawHeader("Authorization", QByteArray("Bearer ") + apiKey.trimmed().toUtf8());
    }

    chatReply_ = chatNetwork_->post(request, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    setChatGenerationState(true, QStringLiteral("模型生成中"));

    QObject::connect(chatReply_, &QNetworkReply::finished, this, [this, reply = chatReply_]() {
        if (reply != chatReply_) {
            reply->deleteLater();
            return;
        }
        if (!pendingChatAbortMessage_.isEmpty()) {
            finishPendingChatRequest(false, pendingChatAbortMessage_);
            return;
        }

        const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        pendingChatResponseBuffer_.append(reply->readAll());
        const QByteArray body = pendingChatResponseBuffer_;
        const QNetworkReply::NetworkError networkError = reply->error();
        const QString networkErrorString = reply->errorString();

        if (networkError != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
            const QString bodyPreview = responseErrorMessage(body);
            finishPendingChatRequest(false,
                QStringLiteral("模型请求失败：HTTP %1 / %2 %3").arg(statusCode).arg(networkErrorString, bodyPreview));
            return;
        }

        QString parseError;
        QString assistantContent;
        bool sawStream = pendingChatSawStream_;
        assistantContent = extractStreamingAssistantReply(body, &sawStream, &parseError);
        if (!sawStream) {
            assistantContent = extractAssistantReply(body, &parseError);
        }
        if (assistantContent.isEmpty()) {
            finishPendingChatRequest(false, parseError.isEmpty() ? QStringLiteral("模型返回空回复") : parseError);
            return;
        }

        completePendingChatRequest(assistantContent);
    });

    QObject::connect(chatReply_, &QNetworkReply::readyRead, this, [this, reply = chatReply_]() {
        if (reply != chatReply_) {
            return;
        }
        pendingChatResponseBuffer_.append(reply->readAll());
        if (chatRuntimeConfig(QDir(legacyRoot_)).outputSplittingEnabled) {
            setChatStreamingPreview({});
            return;
        }
        bool sawStream = false;
        const QString preview = extractStreamingAssistantReply(pendingChatResponseBuffer_, &sawStream);
        if (sawStream) {
            pendingChatSawStream_ = true;
            setChatStreamingPreview(preview);
        }
    });

    chatTimer_->disconnect(this);
    QObject::connect(chatTimer_, &QTimer::timeout, this, [this, requestTimeout]() {
        if (!chatReply_) {
            return;
        }
        pendingChatAbortMessage_ = QStringLiteral("模型请求超时（%1 秒），未写入聊天历史").arg(requestTimeout);
        setChatGenerationState(true, QStringLiteral("请求超时，正在停止"));
        chatReply_->abort();
    });
    chatTimer_->start(requestTimeout * 1000);

    QVariantMap result = resultMap(true, QStringLiteral("生成请求已开始"));
    result.insert(QStringLiteral("started"), true);
    return result;
}

QVariantMap FantarealBridge::startChatMessageWithReply(const QString& message) {
    const QString content = sanitizedChatMessage(message);
    if (content.isEmpty()) {
        return resultMap(false, QStringLiteral("消息不能为空"));
    }
    if (chatGenerating_) {
        return resultMap(false, QStringLiteral("已有聊天生成任务正在进行"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    conversations.append(chatHistoryMessage(QStringLiteral("user"), content, QStringLiteral("huskarui")));

    const ChatRuntimeConfig config = chatRuntimeConfig(root);
    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        if (!config.demoMode) {
            return resultMap(false, QStringLiteral("聊天模型未配置：请在设置页填写 LLM Base URL 和模型名，或启用 demo_mode"));
        }
        return sendChatMessageWithReply(message);
    }

    const QString url = buildApiUrl(config.baseUrl, QStringLiteral("chat/completions"));
    const QJsonArray messages = buildChatCompletionMessages(root, conversations, config);
    QString saveError;
    if (saveChatConversationsWithBackup(root, relativePath, conversations, &saveError).isEmpty()) {
        return resultMap(false, saveError);
    }
    refreshLegacyScan();

    return startPendingChatRequest(
        url,
        config.apiKey,
        config.requestTimeout,
        chatCompletionPayload(config, messages, true),
        conversations,
        QStringLiteral("huskarui-llm"),
        QStringLiteral("消息已发送，助手回复已写入本地聊天历史"));
}

QVariantMap FantarealBridge::startRegenerateLastChatReply() {
    if (chatGenerating_) {
        return resultMap(false, QStringLiteral("已有聊天生成任务正在进行"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    int lastUserIndex = -1;
    for (int i = conversations.size() - 1; i >= 0; --i) {
        const QJsonObject message = conversations.at(i).toObject();
        if (message.value(QStringLiteral("role")).toString() == QStringLiteral("user")
            && !sanitizedChatMessage(message.value(QStringLiteral("content")).toString()).isEmpty()) {
            lastUserIndex = i;
            break;
        }
    }
    if (lastUserIndex < 0) {
        return resultMap(false, QStringLiteral("没有可重试的用户消息"));
    }

    QJsonArray retryConversations;
    for (int i = 0; i <= lastUserIndex; ++i) {
        retryConversations.append(conversations.at(i));
    }
    for (int i = lastUserIndex + 1; i < conversations.size(); ++i) {
        const QString role = conversations.at(i).toObject().value(QStringLiteral("role")).toString();
        if (role != QStringLiteral("assistant")) {
            return resultMap(false, QStringLiteral("最后一条用户消息后存在非助手记录，已停止以避免覆盖历史"));
        }
    }

    const ChatRuntimeConfig config = chatRuntimeConfig(root);
    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        if (!config.demoMode) {
            return resultMap(false, QStringLiteral("聊天模型未配置：请在设置页填写 LLM Base URL 和模型名，或启用 demo_mode"));
        }
        return regenerateLastChatReply();
    }

    const QString url = buildApiUrl(config.baseUrl, QStringLiteral("chat/completions"));
    const QJsonArray messages = buildChatCompletionMessages(root, retryConversations, config);
    QString saveError;
    if (saveChatConversationsWithBackup(root, relativePath, retryConversations, &saveError).isEmpty()) {
        return resultMap(false, saveError);
    }
    refreshLegacyScan();

    return startPendingChatRequest(
        url,
        config.apiKey,
        config.requestTimeout,
        chatCompletionPayload(config, messages, true),
        retryConversations,
        QStringLiteral("huskarui-llm"),
        QStringLiteral("已重试生成最近一条助手回复，旧聊天已备份"));
}

QVariantMap FantarealBridge::stopChatGeneration() {
    if (!chatGenerating_ || !chatReply_) {
        return resultMap(false, QStringLiteral("当前没有正在生成的聊天"));
    }
    pendingChatAbortMessage_ = QStringLiteral("生成已停止，未写入聊天历史");
    setChatGenerationState(true, QStringLiteral("正在停止"));
    chatReply_->abort();
    return resultMap(true, QStringLiteral("已请求停止生成"));
}

void FantarealBridge::completeEndChatConversation(const QString& memorySummary, const QString& transcript) {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");

    const QVariantMap memoryResult = saveMemoryEntry(-1, memoryDraftFromSummary(memorySummary, transcript));
    if (!memoryResult.value(QStringLiteral("ok")).toBool()) {
        finishPendingChatRequest(false, QStringLiteral("长期记忆保存失败：%1").arg(memoryResult.value(QStringLiteral("message")).toString()));
        return;
    }

    QString clearError;
    const QString conversationBackupPath = saveChatConversationsWithBackup(root, relativePath, QJsonArray{}, &clearError);
    if (conversationBackupPath.isEmpty()) {
        finishPendingChatRequest(false, QStringLiteral("长期记忆已保存，但清空对话失败：%1").arg(clearError));
        return;
    }

    refreshLegacyScan();
    finishPendingChatRequest(true, QStringLiteral("对话已结束，长期记忆已写入，当前上下文已清空"), conversationBackupPath);
}

QVariantMap FantarealBridge::endChatConversation() {
    if (chatGenerating_) {
        return resultMap(false, QStringLiteral("正在生成回复，暂时不能结束对话"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    const QString transcript = conversationMemoryTranscript(conversations);
    if (transcript.trimmed().isEmpty()) {
        return resultMap(false, QStringLiteral("当前对话为空，无法写入长期记忆"));
    }

    const ChatRuntimeConfig config = chatRuntimeConfig(root);
    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        if (!config.demoMode) {
            return resultMap(false, QStringLiteral("聊天模型未配置，无法将当前对话总结为长期记忆"));
        }
    }

    QJsonArray visibleConversations = conversations;
    QJsonObject statusMessage = chatHistoryMessage(
        QStringLiteral("assistant"),
        QStringLiteral("正在整理回忆中......"),
        QStringLiteral("huskarui-memory"));
    statusMessage.insert(QStringLiteral("transient_status"), true);
    visibleConversations.append(statusMessage);
    QString statusSaveError;
    if (saveChatConversationsWithBackup(root, relativePath, visibleConversations, &statusSaveError).isEmpty()) {
        return resultMap(false, statusSaveError);
    }
    refreshLegacyScan();
    setChatGenerationState(true, QStringLiteral("正在整理回忆中......"));

    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        const QString fallbackSummary = QStringLiteral("本次对话摘要：\n%1").arg(clippedText(transcript, 2000, QStringLiteral("无内容")));
        QTimer::singleShot(0, this, [this, fallbackSummary, transcript]() {
            completeEndChatConversation(fallbackSummary, transcript);
        });
        QVariantMap result = resultMap(true, QStringLiteral("正在整理回忆中......"));
        result.insert(QStringLiteral("started"), true);
        return result;
    }

    const QString url = buildApiUrl(config.baseUrl, QStringLiteral("chat/completions"));
    if (url.trimmed().isEmpty()) {
        finishPendingChatRequest(false, QStringLiteral("聊天模型 API URL 未配置"));
        return resultMap(false, QStringLiteral("聊天模型 API URL 未配置"));
    }

    QNetworkRequest request{ QUrl(url) };
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    if (!config.apiKey.trimmed().isEmpty()) {
        request.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.trimmed().toUtf8());
    }

    chatReply_ = chatNetwork_->post(
        request,
        QJsonDocument(chatCompletionPayload(config, conversationMemoryMessages(root, conversations))).toJson(QJsonDocument::Compact));

    QObject::connect(chatReply_, &QNetworkReply::finished, this, [this, reply = chatReply_, transcript]() {
        if (reply != chatReply_) {
            reply->deleteLater();
            return;
        }
        if (!pendingChatAbortMessage_.isEmpty()) {
            finishPendingChatRequest(false, pendingChatAbortMessage_);
            return;
        }

        const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray body = reply->readAll();
        const QNetworkReply::NetworkError networkError = reply->error();
        const QString networkErrorString = reply->errorString();
        if (networkError != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
            finishPendingChatRequest(false,
                QStringLiteral("回忆整理请求失败：HTTP %1 / %2 %3")
                    .arg(statusCode)
                    .arg(networkErrorString, responseErrorMessage(body)));
            return;
        }

        QString parseError;
        const QString memorySummary = extractAssistantReply(body, &parseError);
        if (memorySummary.trimmed().isEmpty()) {
            finishPendingChatRequest(false, parseError.isEmpty() ? QStringLiteral("模型未返回长期记忆摘要") : parseError);
            return;
        }
        completeEndChatConversation(memorySummary, transcript);
    });

    chatTimer_->disconnect(this);
    pendingChatAbortMessage_.clear();
    QObject::connect(chatTimer_, &QTimer::timeout, this, [this, requestTimeout = config.requestTimeout]() {
        if (!chatReply_) {
            return;
        }
        pendingChatAbortMessage_ = QStringLiteral("回忆整理请求超时（%1 秒）").arg(requestTimeout);
        chatReply_->abort();
    });
    chatTimer_->start(config.requestTimeout * 1000);

    QVariantMap result = resultMap(true, QStringLiteral("正在整理回忆中......"));
    result.insert(QStringLiteral("started"), true);
    return result;
}

QVariantMap FantarealBridge::sendChatMessageWithReply(const QString& message) {
    const QString content = sanitizedChatMessage(message);
    if (content.isEmpty()) {
        return resultMap(false, QStringLiteral("消息不能为空"));
    }

    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    conversations.append(chatHistoryMessage(QStringLiteral("user"), content, QStringLiteral("huskarui")));

    const ChatRuntimeConfig config = chatRuntimeConfig(root);
    QString assistantContent;
    QString assistantSource = QStringLiteral("huskarui-llm");
    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        if (!config.demoMode) {
            return resultMap(false, QStringLiteral("聊天模型未配置：请在设置页填写 LLM Base URL 和模型名，或启用 demo_mode"));
        }
        assistantContent = demoAssistantReply(root, content);
        assistantSource = QStringLiteral("huskarui-demo");
    } else {
        QString requestError;
        assistantContent = requestAssistantReply(config, buildChatCompletionMessages(root, conversations, config), &requestError);
        if (assistantContent.trimmed().isEmpty()) {
            return resultMap(false, requestError.isEmpty() ? QStringLiteral("模型返回空回复") : requestError);
        }
    }

    const QJsonArray displayParts = assistantSource == QStringLiteral("huskarui-demo")
        ? outputPartsToJsonArray(fallbackOutputParts(assistantContent))
        : assistantDisplayParts(config, assistantContent);
    conversations.append(chatHistoryMessage(QStringLiteral("assistant"), assistantContent, assistantSource, displayParts));

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("conversations"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(conversationPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(conversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("消息已发送，助手回复已写入本地聊天历史"), backupPath);
}

QVariantMap FantarealBridge::regenerateLastChatReply() {
    const QDir root(legacyRoot_);
    const QString relativePath = QStringLiteral("data/conversations.json");
    const QString conversationPath = root.absoluteFilePath(relativePath);
    QJsonArray conversations;
    QString readError;
    if (!readJsonArrayFileStrict(conversationPath, &conversations, &readError)) {
        return resultMap(false, QStringLiteral("conversations.json %1").arg(readError));
    }

    int lastUserIndex = -1;
    QString lastUserContent;
    for (int i = conversations.size() - 1; i >= 0; --i) {
        const QJsonObject message = conversations.at(i).toObject();
        if (message.value(QStringLiteral("role")).toString() != QStringLiteral("user")) {
            continue;
        }
        const QString content = sanitizedChatMessage(message.value(QStringLiteral("content")).toString());
        if (!content.isEmpty()) {
            lastUserIndex = i;
            lastUserContent = content;
            break;
        }
    }
    if (lastUserIndex < 0) {
        return resultMap(false, QStringLiteral("没有可重试的用户消息"));
    }

    QJsonArray retryConversations;
    for (int i = 0; i <= lastUserIndex; ++i) {
        retryConversations.append(conversations.at(i));
    }
    for (int i = lastUserIndex + 1; i < conversations.size(); ++i) {
        const QString role = conversations.at(i).toObject().value(QStringLiteral("role")).toString();
        if (role != QStringLiteral("assistant")) {
            return resultMap(false, QStringLiteral("最后一条用户消息后存在非助手记录，已停止以避免覆盖历史"));
        }
    }

    const ChatRuntimeConfig config = chatRuntimeConfig(root);
    QString assistantContent;
    QString assistantSource = QStringLiteral("huskarui-llm");
    if (config.baseUrl.trimmed().isEmpty() || config.model.trimmed().isEmpty()) {
        if (!config.demoMode) {
            return resultMap(false, QStringLiteral("聊天模型未配置：请在设置页填写 LLM Base URL 和模型名，或启用 demo_mode"));
        }
        assistantContent = demoAssistantReply(root, lastUserContent);
        assistantSource = QStringLiteral("huskarui-demo");
    } else {
        QString requestError;
        assistantContent = requestAssistantReply(config, buildChatCompletionMessages(root, retryConversations, config), &requestError);
        if (assistantContent.trimmed().isEmpty()) {
            return resultMap(false, requestError.isEmpty() ? QStringLiteral("模型返回空回复") : requestError);
        }
    }

    const QJsonArray displayParts = assistantSource == QStringLiteral("huskarui-demo")
        ? outputPartsToJsonArray(fallbackOutputParts(assistantContent))
        : assistantDisplayParts(config, assistantContent);
    retryConversations.append(chatHistoryMessage(QStringLiteral("assistant"), assistantContent, assistantSource, displayParts));

    QString backupError;
    const QString backupPath = backupJsonFile(root, relativePath, QStringLiteral("conversations"), &backupError);
    if (backupPath.isEmpty()) {
        return resultMap(false, backupError);
    }

    QSaveFile saveFile(conversationPath);
    if (!saveFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return resultMap(false, QStringLiteral("conversations.json 无法写入：%1").arg(saveFile.errorString()), backupPath);
    }
    const QByteArray payload = QJsonDocument(retryConversations).toJson(QJsonDocument::Indented);
    if (saveFile.write(payload) != payload.size()) {
        return resultMap(false, QStringLiteral("conversations.json 写入失败：%1").arg(saveFile.errorString()), backupPath);
    }
    if (!saveFile.commit()) {
        return resultMap(false, QStringLiteral("conversations.json 提交失败：%1").arg(saveFile.errorString()), backupPath);
    }

    refreshLegacyScan();
    return resultMap(true, QStringLiteral("已重试生成最近一条助手回复，旧聊天已备份"), backupPath);
}

void FantarealBridge::refreshLegacyScan() {
    const QDir root(legacyRoot_);
    const QStringList criticalFiles = {
        "data/settings.json",
        "data/route_forwarding.json",
        "data/current_role_card.json",
        "data/preset.json",
        "data/worldbook.json",
        "data/worldbook_runtime_state.json",
        "data/creative_workshop_state.json",
        "data/conversations.json",
        "data/persona.json",
        "data/user_profile.json",
        "data/auto_saga/state.json",
        "data/mods/state_journal/state_journal.db",
        "data/logs/fantareal.log",
        "cards/template_single_role_card.json",
        "cards/template_multi_role_card.json",
    };

    const QStringList assetDirs = {
        "data/slots",
        "data/card_runtime/cards",
        "data/mobile_chat",
        "cards",
        "assets/人设卡",
        "assets/世界书",
        "assets/预设",
        "assets/事件预设",
        "static/uploads",
        "static/sprites",
        "mods",
        "exports",
    };

    criticalFileCount_ = criticalFiles.size();
    criticalFileFoundCount_ = 0;
    foundLegacyItems_.clear();
    missingLegacyItems_.clear();
    for (const QString& relativePath : criticalFiles) {
        QString jsonError;
        const bool jsonIsValid = relativePath.endsWith(QStringLiteral(".json"))
            ? isReadableJson(root, relativePath, &jsonError)
            : true;
        if (QFileInfo::exists(root.absoluteFilePath(relativePath)) && jsonIsValid) {
            ++criticalFileFoundCount_;
            foundLegacyItems_.append(relativePath);
        } else {
            missingLegacyItems_.append(jsonError.isEmpty()
                    ? relativePath
                    : QStringLiteral("%1（%2）").arg(relativePath, jsonError));
        }
    }

    assetDirCount_ = assetDirs.size();
    assetDirFoundCount_ = 0;
    for (const QString& relativePath : assetDirs) {
        if (QFileInfo(root.absoluteFilePath(relativePath)).isDir()) {
            ++assetDirFoundCount_;
            foundLegacyItems_.append(relativePath + QStringLiteral("/"));
        } else {
            missingLegacyItems_.append(relativePath + QStringLiteral("/"));
        }
    }

    criticalFilePercent_ = criticalFileCount_ == 0
        ? 0.0
        : (static_cast<double>(criticalFileFoundCount_) / criticalFileCount_) * 100.0;
    assetDirPercent_ = assetDirCount_ == 0
        ? 0.0
        : (static_cast<double>(assetDirFoundCount_) / assetDirCount_) * 100.0;

    cardFileCount_ = 0;
    const QStringList cardDirs = {
        "cards",
        "assets/人设卡",
        "data/card_runtime/cards",
    };
    for (const QString& relativePath : cardDirs) {
        const QDir dir(root.absoluteFilePath(relativePath));
        if (!dir.exists()) {
            continue;
        }
        cardFileCount_ += countFilesRecursively(dir, QStringList{ "*.json", "*.png", "*.webp" });
    }

    assetFileCount_ = 0;
    const QStringList assetLibraryDirs = {
        "assets/人设卡",
        "assets/世界书",
        "assets/预设",
        "assets/事件预设",
        "static/uploads",
        "static/sprites",
    };
    for (const QString& relativePath : assetLibraryDirs) {
        const QDir dir(root.absoluteFilePath(relativePath));
        if (!dir.exists()) {
            continue;
        }
        assetFileCount_ += countFilesRecursively(dir, QStringList{ "*" });
    }

    pluginManifestCount_ = 0;
    const QDir modsDir(root.absoluteFilePath(QStringLiteral("mods")));
    if (modsDir.exists()) {
        const QFileInfoList pluginDirs = modsDir.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
        for (const QFileInfo& pluginDir : pluginDirs) {
            if (QFileInfo::exists(QDir(pluginDir.absoluteFilePath()).absoluteFilePath(QStringLiteral("mod.json")))) {
                ++pluginManifestCount_;
            }
        }
    }

    scanSummary_ = QStringLiteral("%1/%2 关键文件，%3/%4 数据目录，%5 角色/卡片文件，%6 素材文件，%7 插件清单")
        .arg(criticalFileFoundCount_)
        .arg(criticalFileCount_)
        .arg(assetDirFoundCount_)
        .arg(assetDirCount_)
        .arg(cardFileCount_)
        .arg(assetFileCount_)
        .arg(pluginManifestCount_);

    const QJsonObject settings = readJsonObject(root, QStringLiteral("data/settings.json"), &settingsStatus_);
    settingsDraft_.clear();
    settingsRows_.clear();
    if (settings.isEmpty()) {
        settingsRows_.append(settingsStatus_);
    } else {
        settingsDraft_.insert(QStringLiteral("llm_base_url"), settings.value("llm_base_url").toString());
        settingsDraft_.insert(QStringLiteral("llm_api_key_configured"), !settings.value("llm_api_key").toString().trimmed().isEmpty());
        settingsDraft_.insert(QStringLiteral("llm_model"), settings.value("llm_model").toString());
        settingsDraft_.insert(QStringLiteral("theme"), settings.value("theme").toString());
        const QString backgroundPath = settings.value("background_image_path").toString();
        backgroundImagePreviewOpacity_ = qBound(0.0, settings.value("background_image_opacity").toDouble(0.42), 1.0);
        settingsDraft_.insert(QStringLiteral("background_image_path"), backgroundPath);
        settingsDraft_.insert(QStringLiteral("background_image_url"), backgroundImageUrl(root, backgroundPath));
        settingsDraft_.insert(QStringLiteral("background_image_opacity"), backgroundImagePreviewOpacity_);
        settingsDraft_.insert(QStringLiteral("temperature"), settings.value("temperature").toDouble());
        settingsDraft_.insert(QStringLiteral("history_limit"), settings.value("history_limit").toInt());
        settingsDraft_.insert(QStringLiteral("request_timeout"), settings.value("request_timeout").toInt());
        settingsDraft_.insert(QStringLiteral("demo_mode"), settings.value("demo_mode").toBool(false));
        settingsDraft_.insert(QStringLiteral("output_splitting_enabled"), settings.value("output_splitting_enabled").toBool(true));
        settingsDraft_.insert(QStringLiteral("embedding_base_url"), settings.value("embedding_base_url").toString());
        settingsDraft_.insert(QStringLiteral("embedding_api_key_configured"), !settings.value("embedding_api_key").toString().trimmed().isEmpty());
        settingsDraft_.insert(QStringLiteral("embedding_model"), settings.value("embedding_model").toString());
        settingsDraft_.insert(QStringLiteral("retrieval_top_k"), settings.value("retrieval_top_k").toInt());
        settingsDraft_.insert(QStringLiteral("rerank_enabled"), settings.value("rerank_enabled").toBool());
        settingsDraft_.insert(QStringLiteral("rerank_base_url"), settings.value("rerank_base_url").toString());
        settingsDraft_.insert(QStringLiteral("rerank_api_key_configured"), !settings.value("rerank_api_key").toString().trimmed().isEmpty());
        settingsDraft_.insert(QStringLiteral("rerank_model"), settings.value("rerank_model").toString());
        settingsDraft_.insert(QStringLiteral("rerank_top_n"), settings.value("rerank_top_n").toInt());
        settingsDraft_.insert(QStringLiteral("memory_summary_length"), settings.value("memory_summary_length").toString());
        settingsDraft_.insert(QStringLiteral("memory_summary_max_chars"), settings.value("memory_summary_max_chars").toInt());
        settingsDraft_.insert(QStringLiteral("first_launch_disclaimer_accepted"), settings.value("first_launch_disclaimer_accepted").toBool(false));
        settingsDraft_.insert(QStringLiteral("disclaimer_version"), settings.value("disclaimer_version").toString());
        settingsDraft_.insert(QStringLiteral("age_group"), settings.value("age_group").toString());
        settingsDraft_.insert(QStringLiteral("minor_mode_enabled"), settings.value("minor_mode_enabled").toBool(false));

        settingsRows_.append(rowText(QStringLiteral("LLM Base URL"), displayText(settings.value("llm_base_url").toString())));
        settingsRows_.append(rowText(QStringLiteral("LLM API Key"), secretStatus(settings.value("llm_api_key").toString())));
        settingsRows_.append(rowText(QStringLiteral("LLM Model"), displayText(settings.value("llm_model").toString())));
        settingsRows_.append(rowText(QStringLiteral("主题"), displayText(settings.value("theme").toString(), QStringLiteral("默认"))));
        settingsRows_.append(rowText(QStringLiteral("背景图片"), backgroundPath.trimmed().isEmpty() ? QStringLiteral("预制渐变") : displayText(backgroundPath)));
        settingsRows_.append(rowText(QStringLiteral("温度"), settings.value("temperature").toDouble()));
        settingsRows_.append(rowText(QStringLiteral("历史轮数"), settings.value("history_limit").toInt()));
        settingsRows_.append(rowText(QStringLiteral("请求超时"), QStringLiteral("%1 秒").arg(settings.value("request_timeout").toInt())));
        settingsRows_.append(rowText(QStringLiteral("本地演示模式"), enabledText(settings.value("demo_mode").toBool(false))));
        settingsRows_.append(rowText(QStringLiteral("输出气泡切分"), enabledText(settings.value("output_splitting_enabled").toBool(true))));
        settingsRows_.append(rowText(QStringLiteral("Embedding Model"), displayText(settings.value("embedding_model").toString())));
        settingsRows_.append(rowText(QStringLiteral("Embedding API Key"), secretStatus(settings.value("embedding_api_key").toString())));
        settingsRows_.append(rowText(QStringLiteral("Rerank"), enabledText(settings.value("rerank_enabled").toBool())));
        settingsRows_.append(rowText(QStringLiteral("记忆摘要"), displayText(settings.value("memory_summary_length").toString(), QStringLiteral("默认"))));
    }

    const QJsonObject routes = readJsonObject(root, QStringLiteral("data/route_forwarding.json"), &routeStatus_);
    routeDraft_.clear();
    routeRows_.clear();
    if (routes.isEmpty()) {
        routeRows_.append(routeStatus_);
    } else {
        const QJsonArray providers = routes.value("providers").toArray();
        QString strategy = routes.value("strategy").toString();
        if (strategy != QStringLiteral("round_robin")) {
            strategy = QStringLiteral("priority");
        }
        const int retryAttempts = qBound(1, routes.value("retry_attempts").toInt(3), 10);

        routeDraft_.insert(QStringLiteral("enabled"), routes.value("enabled").toBool(false));
        routeDraft_.insert(QStringLiteral("hook_all_posts"), routes.value("hook_all_posts").toBool(true));
        routeDraft_.insert(QStringLiteral("failover_enabled"), routes.value("failover_enabled").toBool(true));
        routeDraft_.insert(QStringLiteral("rotate_keys"), routes.value("rotate_keys").toBool(true));
        routeDraft_.insert(QStringLiteral("retry_attempts"), retryAttempts);
        routeDraft_.insert(QStringLiteral("strategy"), strategy);
        routeDraft_.insert(QStringLiteral("providerCount"), static_cast<int>(providers.size()));
        routeDraft_.insert(QStringLiteral("providers"), routeProvidersToVariant(providers));

        routeRows_.append(rowText(QStringLiteral("路由总开关"), enabledText(routeDraft_.value(QStringLiteral("enabled")).toBool())));
        routeRows_.append(rowText(QStringLiteral("Hook 全部 POST"), enabledText(routeDraft_.value(QStringLiteral("hook_all_posts")).toBool())));
        routeRows_.append(rowText(QStringLiteral("故障转移"), enabledText(routeDraft_.value(QStringLiteral("failover_enabled")).toBool())));
        routeRows_.append(rowText(QStringLiteral("轮换 Key"), enabledText(routeDraft_.value(QStringLiteral("rotate_keys")).toBool())));
        routeRows_.append(rowText(QStringLiteral("重试次数"), retryAttempts));
        routeRows_.append(rowText(QStringLiteral("策略"), strategy == QStringLiteral("round_robin") ? QStringLiteral("round_robin") : QStringLiteral("priority")));
        routeRows_.append(rowText(QStringLiteral("Provider 数量"), static_cast<int>(providers.size())));
    }

    const QJsonObject card = readJsonObject(root, QStringLiteral("data/current_role_card.json"), &cardStatus_);
    cardDraft_.clear();
    cardRows_.clear();
    if (card.isEmpty()) {
        cardRows_.append(cardStatus_);
    } else {
        const QJsonObject raw = card.value("raw").toObject();
        const QJsonArray tags = raw.value("tags").toArray();
        const QJsonObject stateJournal = raw.value("stateJournal").toObject();
        const QJsonObject workshop = raw.value("creativeWorkshop").toObject();
        const QJsonObject opening = workshop.value("opening").toObject();
        const QJsonObject personas = raw.value("personas").toObject();
        const bool stateJournalEnabled = stateJournal.value("enabled").toBool(true);
        const bool workshopEnabled = workshop.value("enabled").toBool(true);
        const bool openingEnabled = opening.value("enabled").toBool(false);
        const QString currentSourcePath = card.value(QStringLiteral("source_path")).toString();

        cardDraft_.insert(QStringLiteral("source_name"), card.value("source_name").toString());
        cardDraft_.insert(QStringLiteral("card_uid"), card.value("card_uid").toString());
        cardDraft_.insert(QStringLiteral("source_path"), currentSourcePath);
        cardDraft_.insert(QStringLiteral("name"), raw.value("name").toString());
        cardDraft_.insert(QStringLiteral("description"), raw.value("description").toString());
        cardDraft_.insert(QStringLiteral("personality"), raw.value("personality").toString());
        cardDraft_.insert(QStringLiteral("scenario"), raw.value("scenario").toString());
        cardDraft_.insert(QStringLiteral("first_mes"), raw.value("first_mes").toString());
        cardDraft_.insert(QStringLiteral("mes_example"), raw.value("mes_example").toString());
        cardDraft_.insert(QStringLiteral("creator_notes"), raw.value("creator_notes").toString());
        cardDraft_.insert(QStringLiteral("creator_comment"), raw.value("creator_comment").toString());
        cardDraft_.insert(QStringLiteral("tagsText"), tagsTextFromArray(tags));
        cardDraft_.insert(QStringLiteral("tagCount"), static_cast<int>(tags.size()));
        cardDraft_.insert(QStringLiteral("personaCount"), static_cast<int>(personas.size()));
        cardDraft_.insert(QStringLiteral("dynamicSceneCount"), static_cast<int>(workshop.value("dynamicScenes").toArray().size()));
        cardDraft_.insert(QStringLiteral("stateJournalEnabled"), stateJournalEnabled);
        cardDraft_.insert(QStringLiteral("creativeWorkshopEnabled"), workshopEnabled);
        cardDraft_.insert(QStringLiteral("openingEnabled"), openingEnabled);

        cardRows_.append(rowText(QStringLiteral("来源文件"), displayText(card.value("source_name").toString())));
        cardRows_.append(rowText(QStringLiteral("来源路径"), displayText(currentSourcePath)));
        cardRows_.append(rowText(QStringLiteral("Card UID"), displayText(card.value("card_uid").toString())));
        cardRows_.append(rowText(QStringLiteral("角色名"), displayText(raw.value("name").toString())));
        cardRows_.append(rowText(QStringLiteral("标签数量"), static_cast<int>(tags.size())));
        cardRows_.append(rowText(QStringLiteral("Persona 数量"), static_cast<int>(personas.size())));
        cardRows_.append(rowText(QStringLiteral("状态日志"), enabledText(stateJournalEnabled)));
        cardRows_.append(rowText(QStringLiteral("演出工坊"), enabledText(workshopEnabled)));
        cardRows_.append(rowText(QStringLiteral("开场演出"), enabledText(openingEnabled)));
        cardRows_.append(rowText(QStringLiteral("动态场景"), static_cast<int>(workshop.value("dynamicScenes").toArray().size())));
    }
    const QJsonObject presetStore = readJsonObject(root, QStringLiteral("data/preset.json"), &presetStatus_);
    presetDraft_.clear();
    presetRows_.clear();
    if (presetStore.isEmpty()) {
        presetRows_.append(presetStatus_);
    } else {
        const QJsonArray presets = presetStore.value("presets").toArray();
        const QString activePresetId = presetStore.value("active_preset_id").toString();
        QJsonObject activePreset;
        for (const QJsonValue& value : presets) {
            const QJsonObject preset = value.toObject();
            if (preset.value("id").toString() == activePresetId) {
                activePreset = preset;
                break;
            }
        }
        if (activePreset.isEmpty() && !presets.isEmpty()) {
            activePreset = presets.first().toObject();
        }

        const QJsonObject modules = activePreset.value("modules").toObject();
        const QJsonArray extraPrompts = activePreset.value("extra_prompts").toArray();
        const QJsonArray promptGroups = activePreset.value("prompt_groups").toArray();
        QJsonObject draftModules = modules;
        for (const PresetModuleMeta& meta : presetModuleMetas()) {
            const QString key = QLatin1String(meta.key);
            if (!draftModules.contains(key)) {
                draftModules.insert(key, meta.defaultEnabled);
            }
        }
        applyPresetModuleMutex(&draftModules);

        presetDraft_.insert(QStringLiteral("id"), activePreset.value("id").toString());
        presetDraft_.insert(QStringLiteral("active_preset_id"), activePresetId);
        presetDraft_.insert(QStringLiteral("name"), activePreset.value("name").toString());
        presetDraft_.insert(QStringLiteral("enabled"), activePreset.value("enabled").toBool(true));
        presetDraft_.insert(QStringLiteral("modules"), presetModulesToVariant(draftModules));
        presetDraft_.insert(QStringLiteral("moduleItems"), presetModuleItemsToVariant(draftModules));
        presetDraft_.insert(QStringLiteral("subPresetItems"), presetSubPresetItemsToVariant(extraPrompts, promptGroups));
        presetDraft_.insert(QStringLiteral("presetCount"), static_cast<int>(presets.size()));
        presetDraft_.insert(QStringLiteral("extraPromptCount"), static_cast<int>(extraPrompts.size()));
        presetDraft_.insert(QStringLiteral("promptGroupCount"), static_cast<int>(promptGroups.size()));

        presetRows_.append(rowText(QStringLiteral("活动预设 ID"), displayText(activePresetId)));
        presetRows_.append(rowText(QStringLiteral("活动预设名"), displayText(activePreset.value("name").toString())));
        presetRows_.append(rowText(QStringLiteral("预设总数"), static_cast<int>(presets.size())));
        presetRows_.append(rowText(QStringLiteral("启用状态"), enabledText(activePreset.value("enabled").toBool())));
        presetRows_.append(rowText(QStringLiteral("启用模块"), QStringLiteral("%1/%2").arg(countEnabledFlags(draftModules)).arg(presetModuleMetas().size())));
        presetRows_.append(rowText(QStringLiteral("额外提示"), static_cast<int>(extraPrompts.size())));
        presetRows_.append(rowText(QStringLiteral("提示分组"), static_cast<int>(promptGroups.size())));
        if (!extraPrompts.isEmpty()) {
            const QJsonObject firstPrompt = extraPrompts.first().toObject();
            presetRows_.append(rowText(QStringLiteral("首个提示"), clippedText(firstPrompt.value("name").toString() + QStringLiteral(" / ") + firstPrompt.value("content").toString())));
        }
    }

    const QJsonObject worldbook = readJsonObject(root, QStringLiteral("data/worldbook.json"), &worldbookStatus_);
    worldbookDraft_.clear();
    worldbookEntryDrafts_.clear();
    worldbookRows_.clear();
    if (worldbook.isEmpty()) {
        worldbookRows_.append(worldbookStatus_);
    } else {
        const QJsonObject worldbookSettings = worldbook.value("settings").toObject();
        const QJsonArray entries = worldbook.value("entries").toArray();
        int enabledEntries = 0;
        for (const QJsonValue& value : entries) {
            const QJsonObject entry = value.toObject();
            if (entry.value("enabled").toBool(true)) {
                ++enabledEntries;
            }
        }

        const QJsonObject runtime = readJsonObject(root, QStringLiteral("data/worldbook_runtime_state.json"), nullptr);
        worldbookDraft_.insert(QStringLiteral("enabled"), worldbookSettings.value("enabled").toBool(true));
        worldbookDraft_.insert(QStringLiteral("debug_enabled"), worldbookSettings.value("debug_enabled").toBool(false));
        worldbookDraft_.insert(QStringLiteral("max_hits"), qBound(1, worldbookSettings.value("max_hits").toInt(3), 20));
        worldbookDraft_.insert(QStringLiteral("default_case_sensitive"), worldbookSettings.value("default_case_sensitive").toBool(false));
        worldbookDraft_.insert(QStringLiteral("default_whole_word"), worldbookSettings.value("default_whole_word").toBool(false));
        worldbookDraft_.insert(QStringLiteral("default_match_mode"),
            (worldbookSettings.value("default_match_mode").toString() == QStringLiteral("all")) ? QStringLiteral("all") : QStringLiteral("any"));
        worldbookDraft_.insert(QStringLiteral("default_secondary_mode"),
            (worldbookSettings.value("default_secondary_mode").toString() == QStringLiteral("any")) ? QStringLiteral("any") : QStringLiteral("all"));
        worldbookDraft_.insert(QStringLiteral("default_entry_type"),
            normalizedWorldbookEntryType(QVariantMap{}, worldbookSettings));
        worldbookDraft_.insert(QStringLiteral("default_group_operator"),
            normalizedWorldbookGroupOperator(QVariantMap{}, worldbookSettings));
        worldbookDraft_.insert(QStringLiteral("default_chance"), qBound(0, worldbookSettings.value("default_chance").toInt(100), 100));
        worldbookDraft_.insert(QStringLiteral("default_sticky_turns"), qBound(0, worldbookSettings.value("default_sticky_turns").toInt(0), 999));
        worldbookDraft_.insert(QStringLiteral("default_cooldown_turns"), qBound(0, worldbookSettings.value("default_cooldown_turns").toInt(0), 999));
        worldbookDraft_.insert(QStringLiteral("default_insertion_position"),
            normalizedWorldbookInsertionPosition(QVariantMap{}, worldbookSettings));
        worldbookDraft_.insert(QStringLiteral("default_injection_depth"), qBound(0, worldbookSettings.value("default_injection_depth").toInt(0), 999));
        worldbookDraft_.insert(QStringLiteral("default_injection_role"),
            normalizedWorldbookInjectionRole(QVariantMap{}, worldbookSettings));
        worldbookDraft_.insert(QStringLiteral("default_injection_order"), qBound(0, worldbookSettings.value("default_injection_order").toInt(100), 999999));
        worldbookDraft_.insert(QStringLiteral("default_prompt_layer"),
            normalizedWorldbookPromptLayer(QVariantMap{}, worldbookSettings));
        worldbookDraft_.insert(QStringLiteral("recursive_scan_enabled"), worldbookSettings.value("recursive_scan_enabled").toBool(false));
        worldbookDraft_.insert(QStringLiteral("recursion_max_depth"), qBound(0, worldbookSettings.value("recursion_max_depth").toInt(2), 5));
        worldbookDraft_.insert(QStringLiteral("entryCount"), static_cast<int>(entries.size()));
        worldbookDraft_.insert(QStringLiteral("enabledEntryCount"), enabledEntries);
        worldbookDraft_.insert(QStringLiteral("runtimeTurnIndex"), runtime.value("turn_index").toInt());
        worldbookEntryDrafts_ = worldbookEntriesToVariant(entries, worldbookSettings);

        worldbookRows_.append(rowText(QStringLiteral("世界书开关"), enabledText(worldbookSettings.value("enabled").toBool())));
        worldbookRows_.append(rowText(QStringLiteral("词条数量"), static_cast<int>(entries.size())));
        worldbookRows_.append(rowText(QStringLiteral("启用词条"), enabledEntries));
        worldbookRows_.append(rowText(QStringLiteral("最大命中"), worldbookSettings.value("max_hits").toInt()));
        worldbookRows_.append(rowText(QStringLiteral("匹配模式"), displayText(worldbookSettings.value("default_match_mode").toString(), QStringLiteral("默认"))));
        worldbookRows_.append(rowText(QStringLiteral("注入位置"), displayText(worldbookSettings.value("default_insertion_position").toString(), QStringLiteral("默认"))));
        worldbookRows_.append(rowText(QStringLiteral("递归扫描"), enabledText(worldbookSettings.value("recursive_scan_enabled").toBool())));
        worldbookRows_.append(rowText(QStringLiteral("运行轮次"), runtime.value("turn_index").toInt()));
        if (!entries.isEmpty()) {
            const QJsonObject firstEntry = entries.first().toObject();
            worldbookRows_.append(rowText(QStringLiteral("首个词条"), clippedText(firstEntry.value("title").toString() + QStringLiteral(" / ") + firstEntry.value("content").toString())));
        }
    }

    const QJsonArray conversations = readJsonArray(root, QStringLiteral("data/conversations.json"), &chatStatus_);
    const bool outputSplittingEnabled = settings.value("output_splitting_enabled").toBool(true);
    chatMessages_.clear();
    for (int i = 0; i < conversations.size(); ++i) {
        const QJsonObject message = conversations.at(i).toObject();
        const QString role = message.value("role").toString();
        const QString content = message.value("content").toString().trimmed();
        if ((role == QStringLiteral("user") || role == QStringLiteral("assistant") || role == QStringLiteral("system"))
            && !content.isEmpty()) {
            chatMessages_.append(chatMessageToVariant(message, i, outputSplittingEnabled));
        }
    }

    chatRows_.clear();
    const QJsonObject persona = readJsonObject(root, QStringLiteral("data/persona.json"), nullptr);
    const QJsonObject userProfile = readJsonObject(root, QStringLiteral("data/user_profile.json"), nullptr);
    chatRows_.append(rowText(QStringLiteral("消息数量"), static_cast<int>(chatMessages_.size())));
    chatRows_.append(rowText(QStringLiteral("Persona"), displayText(persona.value("name").toString())));
    chatRows_.append(rowText(QStringLiteral("Persona 问候"), clippedText(persona.value("greeting").toString())));
    chatRows_.append(rowText(QStringLiteral("用户昵称"), displayText(userProfile.value("nickname").toString())));
    chatRows_.append(rowText(QStringLiteral("用户档案"), clippedText(userProfile.value("profile_text").toString())));
    if (!chatMessages_.isEmpty()) {
        const QVariantMap lastMessage = chatMessages_.last().toMap();
        chatRows_.append(rowText(QStringLiteral("最后消息"), clippedText(lastMessage.value(QStringLiteral("content")).toString())));
    } else {
        chatRows_.append(rowText(QStringLiteral("历史状态"), QStringLiteral("暂无历史消息，可进入新会话草稿")));
    }

    memoryDrafts_.clear();
    memoryRows_.clear();
    const QDir memoryRoot(root.absoluteFilePath(QStringLiteral("data/card_runtime/cards")));
    const int memoryJsonCount = countFilesRecursively(memoryRoot, QStringList{ "memories.json" });
    int memoryItemCount = 0;
    QDirIterator memoryIt(
        memoryRoot.absolutePath(),
        QStringList{ "memories.json" },
        QDir::Files | QDir::NoSymLinks,
        QDirIterator::Subdirectories);
    while (memoryIt.hasNext()) {
        memoryItemCount += static_cast<int>(readJsonArrayFile(memoryIt.next()).size());
    }

    QString currentMemoryRelative;
    QString currentMemoryStatus;
    if (currentMemoryRelativePath(root, &currentMemoryRelative, &currentMemoryStatus)) {
        const QString currentMemoryPath = root.absoluteFilePath(currentMemoryRelative);
        QJsonArray currentMemories;
        if (QFileInfo::exists(currentMemoryPath)) {
            QString readError;
            if (readJsonArrayFileStrict(currentMemoryPath, &currentMemories, &readError)) {
                memoryDrafts_ = memoryEntriesToVariant(currentMemories, currentMemoryRelative);
                currentMemoryStatus = QStringLiteral("%1 已读取").arg(currentMemoryRelative);
            } else {
                currentMemoryStatus = QStringLiteral("%1 %2").arg(currentMemoryRelative, readError);
            }
        } else {
            currentMemoryStatus = QStringLiteral("%1 待创建").arg(currentMemoryRelative);
        }
    }

    QString sagaStatus;
    const QJsonObject autoSaga = readJsonObject(root, QStringLiteral("data/auto_saga/state.json"), &sagaStatus);
    const QJsonObject sagaSettings = autoSaga.value("settings").toObject();
    memoryStatus_ = currentMemoryStatus.isEmpty() ? sagaStatus : currentMemoryStatus;
    memoryRows_.append(rowText(QStringLiteral("当前记忆文件"), displayText(currentMemoryRelative)));
    memoryRows_.append(rowText(QStringLiteral("当前可编辑记忆"), static_cast<int>(memoryDrafts_.size())));
    memoryRows_.append(rowText(QStringLiteral("记忆文件"), memoryJsonCount));
    memoryRows_.append(rowText(QStringLiteral("记忆条目"), memoryItemCount));
    memoryRows_.append(rowText(QStringLiteral("Auto Saga"), enabledText(sagaSettings.value("enabled").toBool())));
    memoryRows_.append(rowText(QStringLiteral("Saga 轮次"), autoSaga.value("turn").toInt()));
    memoryRows_.append(rowText(QStringLiteral("事件主题"), displayText(autoSaga.value("event_theme").toString())));
    memoryRows_.append(rowText(QStringLiteral("当前阶段"), displayText(autoSaga.value("env").toObject().value("time").toString())));
    memoryRows_.append(rowText(QStringLiteral("世界书运行条目"), static_cast<int>(readJsonObject(root, QStringLiteral("data/worldbook_runtime_state.json"), nullptr).value("entries").toObject().size())));

    emit scanChanged();
}
