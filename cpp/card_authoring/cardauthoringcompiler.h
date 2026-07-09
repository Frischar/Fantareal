#pragma once

#include <QJsonObject>
#include <QStringList>

class CardAuthoringCompiler final {
public:
    QJsonObject compileRoleCard(const QJsonObject& project) const;
    QStringList validateProject(const QJsonObject& project) const;

private:
    QJsonObject databaseToStateJournal(const QJsonObject& database) const;
};
