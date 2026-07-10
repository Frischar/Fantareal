#include "card_authoring/cardauthoringpromptpack.h"

#include <QFile>
#include <QJsonArray>
#include <QJsonObject>
#include <QStringList>

namespace {
constexpr auto kPromptPackVersion = "human_character_system_v1";
constexpr auto kPromptResourcePrefix = ":/resources/card_authoring/prompts/human_character_system/";

const QStringList& fastPromptFiles() {
    static const QStringList files{
        QStringLiteral("wheelchair_core.md"),
        QStringLiteral("runtime_package.md"),
        QStringLiteral("container_router.md"),
        QStringLiteral("candidate_rules.md"),
        QStringLiteral("humanizer_guard.md"),
        QStringLiteral("database_designer.md"),
        QStringLiteral("worldbook_preset_memory.md"),
    };
    return files;
}

const QStringList& deepPromptFiles() {
    static const QStringList files{
        QStringLiteral("orchestration_planner.md"),
        QStringLiteral("deep_reference.md"),
        QStringLiteral("question_bank_reference.md"),
        QStringLiteral("case_reference.md"),
        QStringLiteral("fa_container_deep_router.md"),
    };
    return files;
}

QString readPromptResource(const QString& fileName, bool* ok = nullptr) {
    QFile file(QString::fromLatin1(kPromptResourcePrefix) + fileName);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (ok) {
            *ok = false;
        }
        return {};
    }
    if (ok) {
        *ok = true;
    }
    return QString::fromUtf8(file.readAll()).trimmed();
}
}

QString CardAuthoringPromptPack::normalizeThinkingMode(const QString& thinkingMode) {
    const QString mode = thinkingMode.trimmed().toLower();
    return (mode == QStringLiteral("deep")
            || mode == QStringLiteral("depth")
            || mode == QStringLiteral("think")
            || mode == QStringLiteral("slow")
            || mode == QStringLiteral("full"))
        ? QStringLiteral("deep")
        : QStringLiteral("fast");
}

QJsonObject CardAuthoringPromptPack::load(const QString& thinkingMode) const {
    const QString mode = normalizeThinkingMode(thinkingMode);
    QStringList fileNames = fastPromptFiles();
    if (mode == QStringLiteral("deep")) {
        fileNames.append(deepPromptFiles());
    }

    QJsonArray files;
    QJsonArray missingFiles;
    QStringList sections;
    for (const QString& fileName : fileNames) {
        bool readOk = false;
        const QString content = readPromptResource(fileName, &readOk);
        if (!readOk || content.isEmpty()) {
            missingFiles.append(fileName);
            continue;
        }

        QJsonObject item;
        item.insert(QStringLiteral("filename"), fileName);
        item.insert(QStringLiteral("deep_only"), deepPromptFiles().contains(fileName));
        item.insert(QStringLiteral("content"), content);
        item.insert(QStringLiteral("size"), content.size());
        files.append(item);
        sections.append(content);
    }

    QJsonObject result;
    result.insert(QStringLiteral("ok"), !files.isEmpty() && missingFiles.isEmpty());
    result.insert(QStringLiteral("version"), QString::fromLatin1(kPromptPackVersion));
    result.insert(QStringLiteral("thinking_mode"), mode);
    result.insert(QStringLiteral("file_count"), files.size());
    result.insert(QStringLiteral("prompt_files"), files);
    result.insert(QStringLiteral("missing_files"), missingFiles);
    result.insert(QStringLiteral("candidate_schema"), candidateSchema());
    result.insert(QStringLiteral("system_prompt"), sections.join(QStringLiteral("\n\n")));
    return result;
}

QJsonObject CardAuthoringPromptPack::candidateSchema() const {
    QJsonObject target;
    target.insert(QStringLiteral("path"), QStringLiteral("persona_card.name|worldbook.entries.0.content|preset.presets.0.extra_prompts.0.content|memory.items.0.content|database.variables.0.description"));
    target.insert(QStringLiteral("operation"), QStringLiteral("set|append|delete"));

    QJsonObject candidate;
    candidate.insert(QStringLiteral("id"), QStringLiteral("optional; generated when missing"));
    candidate.insert(QStringLiteral("module"), QStringLiteral("persona|worldbook|preset|memory|database"));
    candidate.insert(QStringLiteral("action"), QStringLiteral("json_patch"));
    candidate.insert(QStringLiteral("label"), QStringLiteral("short user-facing label"));
    candidate.insert(QStringLiteral("reason"), QStringLiteral("why this change belongs in this container"));
    candidate.insert(QStringLiteral("target"), target);
    candidate.insert(QStringLiteral("before"), QStringLiteral("current value or null"));
    candidate.insert(QStringLiteral("after"), QStringLiteral("final JSON value to write"));
    candidate.insert(QStringLiteral("group_id"), QStringLiteral("stable_group_id"));
    candidate.insert(QStringLiteral("group_title"), QStringLiteral("candidate group title"));
    candidate.insert(QStringLiteral("container_role"), QStringLiteral("role of this container in the runtime package"));
    candidate.insert(QStringLiteral("depends_on"), QJsonArray{});
    candidate.insert(QStringLiteral("draft_only"), false);

    QJsonObject group;
    group.insert(QStringLiteral("group_id"), QStringLiteral("stable_group_id"));
    group.insert(QStringLiteral("group_title"), QStringLiteral("candidate group title"));
    group.insert(QStringLiteral("candidate_ids"), QJsonArray{ QStringLiteral("optional; backend may rebuild this") });

    QJsonObject plan;
    plan.insert(QStringLiteral("intent_type"), QStringLiteral("create|repair|expand|polish"));
    plan.insert(QStringLiteral("quality_goal"), QStringLiteral("brief quality goal"));
    plan.insert(QStringLiteral("package_mode"), QStringLiteral("runtime_package|single_edit|repair"));
    plan.insert(QStringLiteral("required_containers"), QJsonArray{ QStringLiteral("persona"), QStringLiteral("worldbook"), QStringLiteral("memory"), QStringLiteral("database") });

    QJsonObject schema;
    schema.insert(QStringLiteral("summary"), QStringLiteral("short review summary"));
    schema.insert(QStringLiteral("plan"), plan);
    schema.insert(QStringLiteral("candidate_groups"), QJsonArray{ group });
    schema.insert(QStringLiteral("candidates"), QJsonArray{ candidate });
    return schema;
}
