#include "database/databaseworker.h"

#include "database/databaseservice.h"

#include <algorithm>

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QJsonValue>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>
#include <QUrl>

#include <utility>

namespace {
QString apiEndpoint(QString baseUrl, const QString& endpoint) {
    baseUrl = baseUrl.trimmed();
    while (baseUrl.endsWith(QLatin1Char('/'))) {
        baseUrl.chop(1);
    }
    return baseUrl.isEmpty() ? QString() : baseUrl + QLatin1Char('/') + endpoint;
}

QString remoteMessage(const QByteArray& body) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(body, &error);
    if (error.error == QJsonParseError::NoError && document.isObject()) {
        const QJsonObject root = document.object();
        const QJsonValue errorValue = root.value(QStringLiteral("error"));
        if (errorValue.isObject()) {
            const QString message = errorValue.toObject().value(QStringLiteral("message")).toString().trimmed();
            if (!message.isEmpty()) {
                return message.left(400);
            }
        }
        const QString message = root.value(QStringLiteral("message")).toString().trimmed();
        if (!message.isEmpty()) {
            return message.left(400);
        }
    }
    return QString::fromUtf8(body).simplified().left(400);
}

QString responseContent(const QByteArray& body, QString* errorMessage) {
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(body, &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("provider response is not valid JSON");
        }
        return {};
    }
    const QJsonArray choices = document.object().value(QStringLiteral("choices")).toArray();
    if (choices.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("provider response has no choices");
        }
        return {};
    }
    const QJsonValue content = choices.first().toObject().value(QStringLiteral("message")).toObject().value(QStringLiteral("content"));
    if (!content.isString() || content.toString().trimmed().isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("provider response has no message content");
        }
        return {};
    }
    return content.toString().trimmed();
}

QJsonObject jsonObjectFromReply(QString text, QString* errorMessage) {
    text = text.trimmed();
    if (text.startsWith(QStringLiteral("```"))) {
        const int firstNewline = text.indexOf(QLatin1Char('\n'));
        if (firstNewline >= 0) {
            text = text.mid(firstNewline + 1);
        }
        const int closingFence = text.lastIndexOf(QStringLiteral("```"));
        if (closingFence >= 0) {
            text = text.left(closingFence);
        }
    }
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(text.trimmed().toUtf8(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("worker output is not a JSON object: %1").arg(error.errorString());
        }
        return {};
    }
    return document.object();
}

QJsonObject normalizedScene(const QJsonObject& source) {
    QJsonObject scene;
    const QStringList fields = {
        QStringLiteral("time"), QStringLiteral("timeSlot"), QStringLiteral("season"),
        QStringLiteral("location"), QStringLiteral("weather"), QStringLiteral("atmosphere"),
        QStringLiteral("characters"), QStringLiteral("timeDelta"), QStringLiteral("eventSummary"),
    };
    for (const QString& field : fields) {
        const QString value = source.value(field).toString().trimmed();
        if (!value.isEmpty()) {
            scene.insert(field, value);
        }
    }
    return scene;
}

QJsonArray normalizedFields(const QJsonValue& value) {
    QJsonArray fields;
    const QJsonArray source = value.toArray();
    for (const QJsonValue& item : source) {
        const QJsonObject object = item.toObject();
        const QString key = object.value(QStringLiteral("key")).toString().trimmed();
        const QString label = object.value(QStringLiteral("label")).toString().trimmed();
        const QJsonValue fieldValue = object.value(QStringLiteral("value"));
        if (key.isEmpty() || label.isEmpty() || fieldValue.isUndefined() || fieldValue.isNull()) {
            continue;
        }
        QJsonObject field;
        field.insert(QStringLiteral("key"), key);
        field.insert(QStringLiteral("label"), label);
        field.insert(QStringLiteral("value"), fieldValue);
        fields.append(field);
    }
    return fields;
}

QString normalizedFieldLabel(const QString& key) {
    static const QHash<QString, QString> labels{
        { QStringLiteral("emotion"), QStringLiteral("情绪") },
        { QStringLiteral("mood"), QStringLiteral("情绪") },
        { QStringLiteral("clothing"), QStringLiteral("服饰") },
        { QStringLiteral("posture"), QStringLiteral("姿态与动作") },
        { QStringLiteral("scene"), QStringLiteral("场景") },
        { QStringLiteral("sensory_field"), QStringLiteral("感官状态") },
        { QStringLiteral("body_temperature"), QStringLiteral("身体状态") },
        { QStringLiteral("body_motion"), QStringLiteral("肢体动态") },
        { QStringLiteral("micro_reaction"), QStringLiteral("细微反应") },
        { QStringLiteral("visual_focus"), QStringLiteral("关注点") },
        { QStringLiteral("interaction"), QStringLiteral("角色互动") },
        { QStringLiteral("summary"), QStringLiteral("摘要") },
    };
    return labels.value(key, key);
}

void appendNormalizedField(QJsonArray* fields, QSet<QString>* keys,
    const QString& key, const QString& label, const QJsonValue& value) {
    const QString normalizedKey = key.trimmed();
    if (!fields || !keys || normalizedKey.isEmpty() || keys->contains(normalizedKey)
        || value.isUndefined() || value.isNull()) {
        return;
    }
    if (value.isString() && value.toString().trimmed().isEmpty()) {
        return;
    }
    fields->append(QJsonObject{
        { QStringLiteral("key"), normalizedKey },
        { QStringLiteral("label"), label.trimmed().isEmpty() ? normalizedFieldLabel(normalizedKey) : label.trimmed() },
        { QStringLiteral("value"), value },
    });
    keys->insert(normalizedKey);
}

QJsonArray configuredDisplayFields(const QJsonObject& databaseConfig, const QJsonObject& character) {
    QJsonArray result;
    QSet<QString> seen;
    const QString roleId = character.value(QStringLiteral("roleId")).toString().trimmed();
    const QString name = character.value(QStringLiteral("name")).toString().trimmed();
    auto collect = [&](const QJsonArray& fields, const QString& ownerRoleId) {
        for (const QJsonValue& value : fields) {
            const QJsonObject field = value.toObject();
            if (field.value(QStringLiteral("enabled")).isBool()
                && !field.value(QStringLiteral("enabled")).toBool()) {
                continue;
            }
            if (field.value(QStringLiteral("display")).isBool()
                && !field.value(QStringLiteral("display")).toBool()) {
                continue;
            }
            const QString fieldRoleId = field.value(QStringLiteral("role_id")).toString().trimmed();
            if (!fieldRoleId.isEmpty() && !roleId.isEmpty() && fieldRoleId != roleId) {
                continue;
            }
            if (!ownerRoleId.isEmpty() && !roleId.isEmpty() && ownerRoleId != roleId) {
                continue;
            }
            const QString key = field.value(QStringLiteral("key")).toString().trimmed();
            if (key.isEmpty() || seen.contains(key)) {
                continue;
            }
            result.append(QJsonObject{
                { QStringLiteral("key"), key },
                { QStringLiteral("label"), field.value(QStringLiteral("label")).toString().trimmed().isEmpty()
                        ? key : field.value(QStringLiteral("label")).toString().trimmed() },
                { QStringLiteral("instruction"), field.value(QStringLiteral("instruction")).toString().trimmed() },
            });
            seen.insert(key);
        }
    };
    collect(databaseConfig.value(QStringLiteral("snapshotFields")).toArray(), {});
    for (const QJsonValue& value : databaseConfig.value(QStringLiteral("roles")).toArray()) {
        const QJsonObject role = value.toObject();
        const QString ownerRoleId = role.value(QStringLiteral("role_id")).toString().trimmed();
        const QString roleName = role.value(QStringLiteral("role_name")).toString().trimmed();
        if ((!roleId.isEmpty() && ownerRoleId != roleId)
            && (!name.isEmpty() && roleName != name)) {
            continue;
        }
        collect(role.value(QStringLiteral("snapshotFields")).toArray(), ownerRoleId);
    }
    return result;
}

QJsonArray normalizedMetrics(const QJsonValue& value) {
    QJsonArray metrics;
    for (const QJsonValue& item : value.toArray()) {
        const QJsonObject object = item.toObject();
        const QString key = object.value(QStringLiteral("key")).toString().trimmed();
        const QString label = object.value(QStringLiteral("label")).toString().trimmed();
        if (key.isEmpty() || label.isEmpty()) {
            continue;
        }
        QJsonObject metric;
        metric.insert(QStringLiteral("key"), key);
        metric.insert(QStringLiteral("label"), label);
        metric.insert(QStringLiteral("value"), object.value(QStringLiteral("value")));
        if (object.contains(QStringLiteral("maximum"))) {
            metric.insert(QStringLiteral("maximum"), object.value(QStringLiteral("maximum")));
        }
        if (object.contains(QStringLiteral("delta"))) {
            metric.insert(QStringLiteral("delta"), object.value(QStringLiteral("delta")));
        }
        const QString reason = object.value(QStringLiteral("reason")).toString().trimmed();
        if (!reason.isEmpty()) {
            metric.insert(QStringLiteral("reason"), reason);
        }
        metrics.append(metric);
    }
    return metrics;
}

QJsonArray normalizedCharacters(const QJsonValue& value, const QJsonObject& databaseConfig) {
    QJsonArray characters;
    for (const QJsonValue& item : value.toArray()) {
        const QJsonObject source = item.toObject();
        const QString name = source.value(QStringLiteral("name")).toString().trimmed();
        if (name.isEmpty()) {
            continue;
        }
        QJsonObject character;
        const QString roleId = source.value(QStringLiteral("roleId")).toString().trimmed();
        if (!roleId.isEmpty()) {
            character.insert(QStringLiteral("roleId"), roleId);
        }
        character.insert(QStringLiteral("name"), name);
        QJsonArray fields = normalizedFields(source.value(QStringLiteral("fields")));
        QSet<QString> fieldKeys;
        for (const QJsonValue& fieldValue : fields) {
            fieldKeys.insert(fieldValue.toObject().value(QStringLiteral("key")).toString());
        }
        for (const QJsonValue& fieldValue : configuredDisplayFields(databaseConfig, source)) {
            const QJsonObject field = fieldValue.toObject();
            const QString key = field.value(QStringLiteral("key")).toString();
            const QString label = field.value(QStringLiteral("label")).toString();
            QJsonValue displayValue = source.value(key);
            if (displayValue.isUndefined() && !label.isEmpty()) {
                displayValue = source.value(label);
            }
            appendNormalizedField(&fields, &fieldKeys, key, label, displayValue);
        }
        const QStringList legacyFields{
            QStringLiteral("emotion"), QStringLiteral("mood"), QStringLiteral("clothing"),
            QStringLiteral("posture"), QStringLiteral("scene"), QStringLiteral("sensory_field"),
            QStringLiteral("body_temperature"), QStringLiteral("body_motion"),
            QStringLiteral("micro_reaction"), QStringLiteral("visual_focus"),
            QStringLiteral("interaction"), QStringLiteral("summary"),
        };
        for (const QString& key : legacyFields) {
            appendNormalizedField(&fields, &fieldKeys, key, normalizedFieldLabel(key), source.value(key));
        }
        const QSet<QString> reserved{
            QStringLiteral("roleId"), QStringLiteral("name"), QStringLiteral("fields"),
            QStringLiteral("metrics"), QStringLiteral("variables"),
        };
        for (const QString& key : source.keys()) {
            if (reserved.contains(key) || fieldKeys.contains(key)) {
                continue;
            }
            const QJsonValue displayValue = source.value(key);
            if (displayValue.isArray() || displayValue.isObject()) {
                continue;
            }
            appendNormalizedField(&fields, &fieldKeys, key, normalizedFieldLabel(key), displayValue);
        }
        if (!fields.isEmpty()) {
            character.insert(QStringLiteral("fields"), fields);
        }
        const QJsonArray metrics = normalizedMetrics(
            source.value(QStringLiteral("metrics")).isArray()
                ? source.value(QStringLiteral("metrics"))
                : source.value(QStringLiteral("variables")));
        if (!metrics.isEmpty()) {
            character.insert(QStringLiteral("metrics"), metrics);
        }
        characters.append(character);
    }
    return characters;
}

QJsonArray normalizedRelationships(const QJsonValue& value) {
    QJsonArray relationships;
    for (const QJsonValue& item : value.toArray()) {
        const QJsonObject source = item.toObject();
        const QString pair = source.value(QStringLiteral("pair")).toString().trimmed();
        if (pair.isEmpty()) {
            continue;
        }
        QJsonObject relationship;
        relationship.insert(QStringLiteral("pair"), pair);
        for (const QString& field : { QStringLiteral("stage"), QStringLiteral("change") }) {
            const QString text = source.value(field).toString().trimmed();
            if (!text.isEmpty()) {
                relationship.insert(field, text);
            }
        }
        relationships.append(relationship);
    }
    return relationships;
}

DatabaseTurnResult normalizedResult(const DatabaseWorkerRequest& request, const QJsonObject& output,
    QStringList* warnings) {
    const QJsonObject source = output.value(QStringLiteral("display")).toObject();
    QJsonObject title;
    title.insert(QStringLiteral("schemaVersion"), 1);
    title.insert(QStringLiteral("title"), source.value(QStringLiteral("title")).toString().trimmed().isEmpty()
            ? QStringLiteral("本轮状态")
            : source.value(QStringLiteral("title")).toString().trimmed());
    const QString subtitle = source.value(QStringLiteral("subtitle")).toString().trimmed();
    if (!subtitle.isEmpty()) {
        title.insert(QStringLiteral("subtitle"), subtitle);
    }
    title.insert(QStringLiteral("sequenceLabel"), QStringLiteral("第 %1 条状态记录").arg(request.turn.turnIndex));
    const QJsonObject scene = normalizedScene(source.value(QStringLiteral("scene")).toObject());
    if (!scene.isEmpty()) {
        title.insert(QStringLiteral("scene"), scene);
    }

    QJsonObject record;
    record.insert(QStringLiteral("schemaVersion"), 1);
    const QString summary = source.value(QStringLiteral("summary")).toString().trimmed();
    if (!summary.isEmpty()) {
        record.insert(QStringLiteral("summary"), summary);
    }
    const QJsonArray characters = normalizedCharacters(
        source.value(QStringLiteral("characters")), request.databaseConfig);
    if (!characters.isEmpty()) {
        record.insert(QStringLiteral("characters"), characters);
    }
    const QJsonArray relationships = normalizedRelationships(source.value(QStringLiteral("relationships")));
    if (!relationships.isEmpty()) {
        record.insert(QStringLiteral("relationships"), relationships);
    }
    const QJsonArray metrics = normalizedMetrics(source.value(QStringLiteral("metrics")));
    if (!metrics.isEmpty()) {
        record.insert(QStringLiteral("metrics"), metrics);
    }

    DatabaseTurnResult result;
    result.display.turnId = request.turn.turnId;
    result.display.title = title;
    result.display.record = record;
    QJsonObject updatesSource = output.value(QStringLiteral("updates")).toObject();
    if (output.value(QStringLiteral("storyTimeDelta")).isObject()) {
        updatesSource.insert(QStringLiteral("storyTimeDelta"), output.value(QStringLiteral("storyTimeDelta")));
    } else if (output.value(QStringLiteral("story_time_delta")).isObject()) {
        updatesSource.insert(QStringLiteral("story_time_delta"), output.value(QStringLiteral("story_time_delta")));
    }
    result.updates = normalizeDatabaseUpdates(updatesSource, request.databaseConfig, warnings);
    result.databaseConfig = request.databaseConfig;
    result.expectedAttemptCount = request.turn.attemptCount;
    return result;
}

QJsonArray limitedRuntimeItems(const QList<QJsonObject>& items, int limit) {
    QJsonArray result;
    const int count = qMin(items.size(), limit);
    for (int index = 0; index < count; ++index) {
        result.append(items.at(index));
    }
    return result;
}

QJsonObject workerRuntimeContext(const DatabaseRuntimeView& view) {
    QJsonObject context;
    context.insert(QStringLiteral("schemaVersion"), 1);
    context.insert(QStringLiteral("cardUid"), view.cardUid);
    context.insert(QStringLiteral("snapshots"), limitedRuntimeItems(view.snapshots, 12));
    context.insert(QStringLiteral("characters"), limitedRuntimeItems(view.characters, 24));
    context.insert(QStringLiteral("variables"), limitedRuntimeItems(view.variables, 160));
    context.insert(QStringLiteral("relationships"), limitedRuntimeItems(view.relationships, 80));
    context.insert(QStringLiteral("stages"), limitedRuntimeItems(view.stages, 80));
    context.insert(QStringLiteral("ledger"), limitedRuntimeItems(view.ledger, 24));
    context.insert(QStringLiteral("storyTime"), view.storyTime);
    context.insert(QStringLiteral("activeTags"), limitedRuntimeItems(view.activeTags, 80));
    context.insert(QStringLiteral("truncated"), view.snapshots.size() > 12 || view.characters.size() > 24
            || view.variables.size() > 160 || view.relationships.size() > 80
            || view.stages.size() > 80 || view.ledger.size() > 24);
    return context;
}

QString workerPrompt(const DatabaseWorkerRequest& request, const QJsonObject& runtimeContext) {
    QJsonObject roleConfig;
    roleConfig.insert(QStringLiteral("database"), request.databaseConfig);
    roleConfig.insert(QStringLiteral("name"), request.roleName);
    QJsonObject context;
    context.insert(QStringLiteral("runtime"), runtimeContext);
    context.insert(QStringLiteral("recentHistory"), request.recentHistory);
    roleConfig.insert(QStringLiteral("runtime_context"), context);
    return QStringLiteral(
        "请根据本轮助手回复和角色数据库配置，返回一个 JSON 对象。根对象必须包含 updates 对象和 display 对象。"
        "不输出 Markdown，不输出 SQL，不创建字段。updates 固定为 "
        "{schemaVersion:1,snapshot?,variables:[],relationships:[],ledger:[],tags:[]}："
        "variables 的每项必须使用已配置的 roleId 和 key，包含 value，可选 label、maximum、delta、reason；"
        "relationships 只记录会持续影响后续剧情的长期关系变化，每项使用 "
        "{pairKey,roleA?,roleB?,stage?,attitude?,summary?,change?}；"
        "普通寒暄、一次性互动或关系保持稳定时不要写入 relationships；"
        "更新已有关系时沿用 runtime_context.relationships 中的 pairKey，不要交换关系双方或创建重复关系；"
        "不得输出或决定 stages，阶段由程序根据变量和剧情时间规则计算；"
        "tags 每项使用角色配置已有的非阶段 tag，包含 tag、active，可选 reason；"
        "snapshot 必须包含 scope、title、payload 对象；ledger 每项必须包含 entryType、content，可选 payload 和角色配置已有的 activationTag。"
        "如果 runtime_context.storyTime 已启用且已初始化，根对象额外输出 storyTimeDelta："
        "{changed,deltaSeconds,deltaText,confidence,reason}，只输出本轮增量，不计算绝对时间；"
        "display 是给普通用户阅读的状态记录，固定使用："
        "{title,subtitle,scene,summary,characters,relationships,metrics}。"
        "scene 可包含 time、timeSlot、season、location、weather、atmosphere、characters、timeDelta、eventSummary。"
        "characters 每项固定使用 {roleId,name,fields,metrics}；fields 每项为 {key,label,value}，"
        "metrics 每项为 {key,label,value,maximum,delta,reason}。"
        "必须分别输出本轮涉及的每个启用角色，不得把多角色合并成一个角色。"
        "角色存在 snapshotFields 时，fields 优先按这些字段及其 label 输出；"
        "没有 snapshotFields 时，至少按正文中可观察到的情绪、服饰与动作、关注点、互动和摘要输出，"
        "不得替用户决定行动、台词或内心。"
        "存在已配置变量时，metrics 使用已有 key，并结合 runtime_context 中的当前值输出本轮后的 value、maximum 与 delta；"
        "没有变化可以省略，不得凭空创建变量。"
        "relationships 每项为 {pair,stage,change}，用于记录关系与阶段变化；没有明显变化时可以写保持稳定。"
        "summary 是对本轮状态变化的自然语言概括，不要把 JSON 字段名直接堆给用户。\n\n"
        "角色配置：\n%1\n\n助手回复：\n%2")
        .arg(QString::fromUtf8(QJsonDocument(roleConfig).toJson(QJsonDocument::Compact)), request.assistantContent.left(16000));
}

QString repairPrompt(const QString& source) {
    return QStringLiteral("把下面内容修复为一个合法 JSON 对象。只输出 JSON，不得添加说明。"
                          "根对象必须包含 updates 对象和 display 对象；保留已有 storyTimeDelta 和 relationships，"
                          "但不要添加 stages。\n\n%1")
        .arg(source.left(18000));
}

QJsonObject completionPayload(const DatabaseWorkerConfig& config, const QString& prompt, bool includeResponseFormat) {
    QJsonObject system;
    system.insert(QStringLiteral("role"), QStringLiteral("system"));
    system.insert(QStringLiteral("content"), QStringLiteral("你是 Fantareal 数据库记录 Worker，必须产生结构化 JSON。"));
    QJsonObject user;
    user.insert(QStringLiteral("role"), QStringLiteral("user"));
    user.insert(QStringLiteral("content"), prompt);
    QJsonObject payload;
    payload.insert(QStringLiteral("model"), config.model);
    payload.insert(QStringLiteral("temperature"), config.temperature);
    payload.insert(QStringLiteral("stream"), false);
    payload.insert(QStringLiteral("messages"), QJsonArray{ system, user });
    if (includeResponseFormat) {
        payload.insert(QStringLiteral("response_format"), QJsonObject{ { QStringLiteral("type"), QStringLiteral("json_object") } });
    }
    return payload;
}
}

DatabaseWorker::DatabaseWorker(QString rootPath, QObject* parent)
    : QObject(parent)
    , rootPath_(std::move(rootPath))
    , network_(new QNetworkAccessManager(this)) {
}

void DatabaseWorker::start(const DatabaseWorkerRequest& request) {
    const QString turnId = request.turn.turnId.trimmed();
    const QString cardUid = request.turn.cardUid.trimmed();
    if (turnId.isEmpty() || cardUid.isEmpty() || request.turn.messageId.trimmed().isEmpty()) {
        return;
    }
    if (isActive(turnId)) {
        return;
    }
    queuedRequests_[cardUid].append(request);
    queuedTurnIds_.insert(turnId);
    dispatchNext(cardUid);
}

void DatabaseWorker::cancel(const QString& turnId) {
    const QString id = turnId.trimmed();
    if (id.isEmpty()) {
        return;
    }
    if (queuedTurnIds_.remove(id)) {
        for (auto it = queuedRequests_.begin(); it != queuedRequests_.end(); ++it) {
            QList<DatabaseWorkerRequest>& requests = it.value();
            for (int index = requests.size() - 1; index >= 0; --index) {
                if (requests.at(index).turn.turnId.trimmed() == id) {
                    requests.removeAt(index);
                }
            }
        }
        for (auto it = queuedRequests_.begin(); it != queuedRequests_.end();) {
            if (it.value().isEmpty()) {
                it = queuedRequests_.erase(it);
            } else {
                ++it;
            }
        }
        return;
    }
    if (activeReplies_.contains(id) && activeReplies_.value(id)) {
        cancelledTurnIds_.insert(id);
        activeReplies_.value(id)->abort();
    }
}

bool DatabaseWorker::isActive(const QString& turnId) const {
    const QString id = turnId.trimmed();
    return queuedTurnIds_.contains(id) || activeRequests_.contains(id);
}

void DatabaseWorker::dispatchNext(const QString& cardUid) {
    const QString card = cardUid.trimmed();
    if (card.isEmpty() || activeTurnByCard_.contains(card)) {
        return;
    }
    auto queueIt = queuedRequests_.find(card);
    if (queueIt == queuedRequests_.end() || queueIt->isEmpty()) {
        queuedRequests_.remove(card);
        return;
    }

    DatabaseWorkerRequest request = queueIt->takeFirst();
    if (queueIt->isEmpty()) {
        queuedRequests_.erase(queueIt);
    }
    const QString turnId = request.turn.turnId.trimmed();
    queuedTurnIds_.remove(turnId);

    DatabaseService service(rootPath_);
    const std::optional<DatabaseTurnView> currentTurn = service.turnById(turnId);
    if (!currentTurn || currentTurn->turn.status != DatabaseTurnStatus::Pending) {
        QTimer::singleShot(0, this, [this, card]() { dispatchNext(card); });
        return;
    }
    request.turn = currentTurn->turn;

    activeTurnByCard_.insert(card, turnId);
    activeRequests_.insert(turnId, request);
    const DatabaseWorkerConfig config = service.loadWorkerConfig();
    if (!config.enabled) {
        failTurn(request, QStringLiteral("config_missing"), QStringLiteral("DatabaseWorker 已关闭"));
        return;
    }
    if (config.apiBaseUrl.isEmpty() || config.apiKey.isEmpty() || config.model.isEmpty()) {
        failTurn(request, QStringLiteral("config_missing"), QStringLiteral("请在数据库页面完成 DatabaseWorker 的地址、密钥和模型配置"));
        return;
    }
    const QJsonObject runtimeContext = workerRuntimeContext(service.runtimeView(card, 24));
    sendWorkerRequest(request, config, workerPrompt(request, runtimeContext), 0, true);
}

void DatabaseWorker::sendWorkerRequest(const DatabaseWorkerRequest& request, const DatabaseWorkerConfig& config,
    const QString& prompt, int repairAttempt, bool includeResponseFormat) {
    const QString endpoint = apiEndpoint(config.apiBaseUrl, QStringLiteral("chat/completions"));
    QNetworkRequest networkRequest{ QUrl(endpoint) };
    networkRequest.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    networkRequest.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.toUtf8());
    networkRequest.setTransferTimeout(config.requestTimeout * 1000);

    QNetworkReply* reply = network_->post(networkRequest,
        QJsonDocument(completionPayload(config, prompt, includeResponseFormat)).toJson(QJsonDocument::Compact));
    activeReplies_.insert(request.turn.turnId, reply);
    QObject::connect(reply, &QNetworkReply::finished, this,
        [this, request, config, prompt, repairAttempt, includeResponseFormat, reply]() {
            if (activeReplies_.value(request.turn.turnId) != reply) {
                reply->deleteLater();
                return;
            }
            activeReplies_.remove(request.turn.turnId);
            const QByteArray body = reply->readAll();
            const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
            const QNetworkReply::NetworkError networkError = reply->error();
            const QString errorString = reply->errorString();
            reply->deleteLater();

            if (cancelledTurnIds_.remove(request.turn.turnId)) {
                finishTurn(request, {
                    true,
                    {},
                    QStringLiteral("DatabaseWorker 请求已取消"),
                    request.turn.turnId,
                });
                return;
            }

            if (networkError != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
                if (includeResponseFormat && statusCode == 400) {
                    sendWorkerRequest(request, config, prompt, repairAttempt, false);
                    return;
                }
                const QString code = statusCode == 401 || statusCode == 403
                    ? QStringLiteral("provider_auth")
                    : (networkError == QNetworkReply::TimeoutError ? QStringLiteral("provider_timeout") : QStringLiteral("provider_network"));
                failTurn(request, code, QStringLiteral("DatabaseWorker 请求失败：HTTP %1 / %2 %3")
                    .arg(statusCode).arg(errorString, remoteMessage(body)));
                return;
            }

            QString responseError;
            const QString content = responseContent(body, &responseError);
            if (content.isEmpty()) {
                failTurn(request, QStringLiteral("provider_response"), responseError);
                return;
            }
            QString parseError;
            const QJsonObject output = jsonObjectFromReply(content, &parseError);
            if (output.isEmpty() || !output.value(QStringLiteral("display")).isObject()
                || !output.value(QStringLiteral("updates")).isObject()) {
                if (repairAttempt < config.maxRepairAttempts) {
                    sendWorkerRequest(request, config, repairPrompt(content), repairAttempt + 1, false);
                    return;
                }
                failTurn(request, QStringLiteral("invalid_json"), parseError.isEmpty()
                    ? QStringLiteral("DatabaseWorker 输出缺少 display 对象")
                    : parseError);
                return;
            }

            QStringList warnings;
            DatabaseTurnResult result = normalizedResult(request, output, &warnings);
            result.display.workerModel = config.model;
            QJsonArray warningValues;
            for (const QString& warning : warnings) {
                warningValues.append(warning);
            }
            result.display.warningsJson = QString::fromUtf8(QJsonDocument(warningValues).toJson(QJsonDocument::Compact));
            DatabaseService service(rootPath_);
            const DatabaseOperationResult saved = service.saveTurnResult(result);
            if (!saved.ok) {
                const DatabaseOperationResult persistedError = service.markTurnError(
                    request.turn.turnId, saved.code, saved.message, request.turn.attemptCount);
                if (!persistedError.ok
                    && persistedError.code != QStringLiteral("stale_attempt")
                    && persistedError.code != QStringLiteral("invalid_state")) {
                    finishTurn(request, {
                        false,
                        QStringLiteral("error_persist_failed"),
                        QStringLiteral("状态记录失败状态无法写入数据库：%1").arg(persistedError.message),
                        request.turn.turnId,
                    }, false);
                    return;
                }
            }
            finishTurn(request, saved);
        });
}

void DatabaseWorker::finishTurn(
    const DatabaseWorkerRequest& request, const DatabaseOperationResult& result, bool continueCardQueue) {
    const QString turnId = request.turn.turnId.trimmed();
    const QString cardUid = request.turn.cardUid.trimmed();
    activeReplies_.remove(turnId);
    activeRequests_.remove(turnId);
    cancelledTurnIds_.remove(turnId);
    if (activeTurnByCard_.value(cardUid) == turnId) {
        activeTurnByCard_.remove(cardUid);
    }
    emit turnFinished(request.turn.messageId, result);
    if (continueCardQueue) {
        QTimer::singleShot(0, this, [this, cardUid]() { dispatchNext(cardUid); });
    }
}

void DatabaseWorker::failTurn(const DatabaseWorkerRequest& request, const QString& code, const QString& message) {
    const DatabaseOperationResult persistedError = DatabaseService(rootPath_).markTurnError(
        request.turn.turnId, code, message, request.turn.attemptCount);
    if (!persistedError.ok
        && persistedError.code != QStringLiteral("stale_attempt")
        && persistedError.code != QStringLiteral("invalid_state")) {
        finishTurn(request, {
            false,
            QStringLiteral("error_persist_failed"),
            QStringLiteral("DatabaseWorker 失败状态无法写入数据库：%1").arg(persistedError.message),
            request.turn.turnId,
        }, false);
        return;
    }
    finishTurn(request, {false, code, message, request.turn.turnId});
}

void DatabaseWorker::fetchModels() {
    const DatabaseWorkerConfig config = DatabaseService(rootPath_).loadWorkerConfig();
    if (config.apiBaseUrl.isEmpty() || config.apiKey.isEmpty()) {
        emit modelsFetched({}, {false, QStringLiteral("config_missing"), QStringLiteral("请先配置 DatabaseWorker 地址和密钥")});
        return;
    }
    QNetworkRequest request{ QUrl(apiEndpoint(config.apiBaseUrl, QStringLiteral("models"))) };
    request.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.toUtf8());
    request.setTransferTimeout(config.requestTimeout * 1000);
    QNetworkReply* reply = network_->get(request);
    QObject::connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const QByteArray body = reply->readAll();
        const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QNetworkReply::NetworkError error = reply->error();
        reply->deleteLater();
        if (error != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
            emit modelsFetched({}, {false, QStringLiteral("provider_network"), remoteMessage(body)});
            return;
        }
        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(body, &parseError);
        QStringList models;
        if (parseError.error == QJsonParseError::NoError && document.isObject()) {
            for (const QJsonValue& value : document.object().value(QStringLiteral("data")).toArray()) {
                const QString id = value.toObject().value(QStringLiteral("id")).toString().trimmed();
                if (!id.isEmpty()) {
                    models.append(id);
                }
            }
        }
        models.removeDuplicates();
        std::sort(models.begin(), models.end(), [](const QString& left, const QString& right) {
            return left.compare(right, Qt::CaseInsensitive) < 0;
        });
        emit modelsFetched(models, {true, {}, QStringLiteral("DatabaseWorker 模型列表已刷新")});
    });
}

void DatabaseWorker::testConnection() {
    const DatabaseWorkerConfig config = DatabaseService(rootPath_).loadWorkerConfig();
    if (config.apiBaseUrl.isEmpty() || config.apiKey.isEmpty() || config.model.isEmpty()) {
        emit connectionTested({false, QStringLiteral("config_missing"), QStringLiteral("请先配置 DatabaseWorker 的地址、密钥和模型")});
        return;
    }
    QNetworkRequest request{ QUrl(apiEndpoint(config.apiBaseUrl, QStringLiteral("chat/completions"))) };
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    request.setRawHeader("Authorization", QByteArray("Bearer ") + config.apiKey.toUtf8());
    request.setTransferTimeout(config.requestTimeout * 1000);
    QJsonObject payload;
    payload.insert(QStringLiteral("model"), config.model);
    payload.insert(QStringLiteral("temperature"), 0);
    payload.insert(QStringLiteral("max_tokens"), 1);
    payload.insert(QStringLiteral("messages"), QJsonArray{ QJsonObject{
        { QStringLiteral("role"), QStringLiteral("user") },
        { QStringLiteral("content"), QStringLiteral("ping") },
    } });
    QNetworkReply* reply = network_->post(request, QJsonDocument(payload).toJson(QJsonDocument::Compact));
    QObject::connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const QByteArray body = reply->readAll();
        const int statusCode = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QNetworkReply::NetworkError error = reply->error();
        reply->deleteLater();
        if (error != QNetworkReply::NoError || statusCode < 200 || statusCode >= 300) {
            emit connectionTested({false, statusCode == 401 || statusCode == 403 ? QStringLiteral("provider_auth") : QStringLiteral("provider_network"), remoteMessage(body)});
            return;
        }
        emit connectionTested({true, {}, QStringLiteral("DatabaseWorker 连接成功")});
    });
}
