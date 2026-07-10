#include "card_authoring/cardauthoringservice.h"

#include "card_authoring/cardauthoringapplyplanner.h"
#include "card_authoring/cardauthoringcandidateprocessor.h"
#include "card_authoring/cardauthoringcompiler.h"
#include "card_authoring/cardauthoringmodels.h"
#include "card_authoring/cardauthoringpromptpack.h"
#include "card_authoring/cardauthoringprojectstore.h"

#include <utility>

CardAuthoringService::CardAuthoringService(QString rootPath)
    : paths_(std::move(rootPath)) {
}

CardAuthoringPaths CardAuthoringService::paths() const {
    return paths_;
}

QJsonObject CardAuthoringService::createEmptyProject() const {
    return CardAuthoring::createEmptyProject();
}

QJsonObject CardAuthoringService::normalizeProject(const QJsonObject& project) const {
    return CardAuthoring::normalizeProject(project);
}

QJsonObject CardAuthoringService::saveWorkspace(const QJsonObject& project, QString* savedPath, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).saveWorkspace(project, savedPath, errorMessage);
}

QJsonObject CardAuthoringService::loadWorkspace(QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).loadWorkspace(errorMessage);
}

QJsonArray CardAuthoringService::listProjects(QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).listProjects(errorMessage);
}

QJsonObject CardAuthoringService::loadProject(const QString& filename, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).loadProject(filename, errorMessage);
}

QJsonObject CardAuthoringService::saveProject(const QString& filename, const QJsonObject& project, QString* savedPath, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).saveProject(filename, project, savedPath, errorMessage);
}

QJsonObject CardAuthoringService::deleteProject(const QString& filename, QString* archivedPath, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).deleteProject(filename, archivedPath, errorMessage);
}

QJsonObject CardAuthoringService::importProjectFile(const QString& sourcePath, QString* importedPath, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).importProjectFile(sourcePath, importedPath, errorMessage);
}

QJsonObject CardAuthoringService::exportProjectFile(const QString& targetPath, const QJsonObject& project, QString* exportedPath, QString* errorMessage) const {
    return CardAuthoringProjectStore(paths_.rootPath()).exportProjectFile(targetPath, project, exportedPath, errorMessage);
}

QJsonObject CardAuthoringService::buildCandidatePromptPack(const QString& thinkingMode) const {
    return CardAuthoringPromptPack().load(thinkingMode);
}

QJsonObject CardAuthoringService::normalizeCandidateReview(const QJsonObject& project, const QJsonObject& review) const {
    return CardAuthoringCandidateProcessor().normalizeReview(project, review);
}

QJsonObject CardAuthoringService::applyCandidateReview(const QJsonObject& project, const QJsonObject& review, const QStringList& selectedCandidateIds) const {
    return CardAuthoringCandidateProcessor().applyCandidates(project, review, selectedCandidateIds);
}

QJsonObject CardAuthoringService::compileRoleCard(const QJsonObject& project) const {
    return CardAuthoringCompiler().compileRoleCard(project);
}

QStringList CardAuthoringService::validateProject(const QJsonObject& project) const {
    return CardAuthoringCompiler().validateProject(project);
}

QJsonObject CardAuthoringService::buildApplyPreview(const QJsonObject& project, const QStringList& modules) const {
    return CardAuthoringApplyPlanner(paths_.rootPath()).buildPreview(project, modules);
}

QJsonObject CardAuthoringService::applySelected(const QJsonObject& project, const QStringList& selectedGroupIds) const {
    return CardAuthoringApplyPlanner(paths_.rootPath()).applySelected(project, selectedGroupIds);
}
