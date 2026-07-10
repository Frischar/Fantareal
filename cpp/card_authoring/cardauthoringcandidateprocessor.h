#pragma once

#include <QJsonObject>
#include <QStringList>

class CardAuthoringCandidateProcessor final {
public:
    QJsonObject normalizeReview(const QJsonObject& project, const QJsonObject& review) const;
    QJsonObject applyCandidates(const QJsonObject& project, const QJsonObject& review, const QStringList& selectedCandidateIds = {}) const;
};
