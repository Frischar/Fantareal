#pragma once

#include <QJsonObject>
#include <QString>

class CardAuthoringPromptPack final {
public:
    static QString normalizeThinkingMode(const QString& thinkingMode);

    QJsonObject load(const QString& thinkingMode = {}) const;
    QJsonObject candidateSchema() const;
};
