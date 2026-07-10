#pragma once

#include "card_authoring/cardauthoringpaths.h"

#include <QJsonArray>
#include <QJsonObject>
#include <QString>
#include <QStringList>

class CardAuthoringService final {
public:
    explicit CardAuthoringService(QString rootPath);

    CardAuthoringPaths paths() const;
    QJsonObject createEmptyProject() const;
    QJsonObject normalizeProject(const QJsonObject& project) const;
    QJsonObject saveWorkspace(const QJsonObject& project, QString* savedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject loadWorkspace(QString* errorMessage = nullptr) const;
    QJsonArray listProjects(QString* errorMessage = nullptr) const;
    QJsonObject loadProject(const QString& filename, QString* errorMessage = nullptr) const;
    QJsonObject saveProject(const QString& filename, const QJsonObject& project, QString* savedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject deleteProject(const QString& filename, QString* archivedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject importProjectFile(const QString& sourcePath, QString* importedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject exportProjectFile(const QString& targetPath, const QJsonObject& project, QString* exportedPath = nullptr, QString* errorMessage = nullptr) const;
    QJsonObject buildCandidatePromptPack(const QString& thinkingMode = {}) const;
    QJsonObject normalizeCandidateReview(const QJsonObject& project, const QJsonObject& review) const;
    QJsonObject applyCandidateReview(const QJsonObject& project, const QJsonObject& review, const QStringList& selectedCandidateIds = {}) const;
    QJsonObject compileRoleCard(const QJsonObject& project) const;
    QStringList validateProject(const QJsonObject& project) const;
    QJsonObject buildApplyPreview(const QJsonObject& project, const QStringList& modules = {}) const;
    QJsonObject applySelected(const QJsonObject& project, const QStringList& selectedGroupIds = {}) const;

private:
    CardAuthoringPaths paths_;
};
