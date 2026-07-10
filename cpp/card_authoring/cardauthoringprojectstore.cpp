#include "card_authoring/cardauthoringprojectstore.h"

#include "card_authoring/cardauthoringmodels.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QRegularExpression>
#include <QSaveFile>
#include <QUuid>

#include <utility>

namespace {
QString projectBaseName(QString filename) {
    filename = QFileInfo(filename).fileName().trimmed();
    const QString extension = CardAuthoringPaths::projectFileExtension();
    if (filename.endsWith(extension, Qt::CaseInsensitive)) {
        filename.chop(extension.size());
    }
    return filename.trimmed().isEmpty() ? QStringLiteral("untitled") : filename.trimmed();
}

QString projectTitleFallback(const QJsonObject& project, const QString& fallback) {
    QString title = project.value(QStringLiteral("title")).toString().trimmed();
    if (!title.isEmpty()) {
        return title;
    }
    title = project.value(QStringLiteral("persona_card")).toObject().value(QStringLiteral("name")).toString().trimmed();
    if (!title.isEmpty()) {
        return title;
    }
    return projectBaseName(fallback);
}

QJsonObject projectListItem(const QFileInfo& info, const QJsonObject& project, const QString& message = {}) {
    const QJsonObject persona = project.value(QStringLiteral("persona_card")).toObject();
    const QJsonObject database = project.value(QStringLiteral("database")).toObject();
    const QJsonObject worldbook = project.value(QStringLiteral("worldbook")).toObject();
    const QJsonObject memory = project.value(QStringLiteral("memory")).toObject();

    QJsonObject item;
    item.insert(QStringLiteral("ok"), message.isEmpty());
    item.insert(QStringLiteral("filename"), info.fileName());
    item.insert(QStringLiteral("path"), QDir::fromNativeSeparators(info.absoluteFilePath()));
    item.insert(QStringLiteral("title"), message.isEmpty() ? projectTitleFallback(project, info.fileName()) : info.fileName());
    item.insert(QStringLiteral("persona_name"), persona.value(QStringLiteral("name")).toString());
    item.insert(QStringLiteral("updated_at"), project.value(QStringLiteral("updated_at")).toString());
    item.insert(QStringLiteral("modified_at"), info.lastModified().toUTC().toString(Qt::ISODateWithMs));
    item.insert(QStringLiteral("file_size"), static_cast<double>(info.size()));
    item.insert(QStringLiteral("variable_count"), database.value(QStringLiteral("variables")).toArray().size());
    item.insert(QStringLiteral("stage_count"), database.value(QStringLiteral("stages")).toArray().size());
    item.insert(QStringLiteral("tag_count"), database.value(QStringLiteral("tags")).toArray().size());
    item.insert(QStringLiteral("worldbook_entry_count"), worldbook.value(QStringLiteral("entries")).toArray().size());
    item.insert(QStringLiteral("memory_item_count"), memory.value(QStringLiteral("items")).toArray().size());
    if (!message.isEmpty()) {
        item.insert(QStringLiteral("message"), message);
    }
    return item;
}

QString timestampSuffix() {
    return QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMdd-HHmmsszzz"));
}

QString uniqueFilePathInDir(const QDir& dir, const QString& fileName) {
    const QFileInfo info(fileName);
    const QString suffix = info.suffix().isEmpty() ? QStringLiteral("json") : info.suffix();
    QString baseName = info.completeBaseName().trimmed();
    if (baseName.isEmpty()) {
        baseName = QStringLiteral("project");
    }
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
}

CardAuthoringProjectStore::CardAuthoringProjectStore(QString rootPath)
    : paths_(std::move(rootPath)) {
}

CardAuthoringPaths CardAuthoringProjectStore::paths() const {
    return paths_;
}

QJsonObject CardAuthoringProjectStore::createEmptyProject() const {
    return CardAuthoring::createEmptyProject();
}

QJsonObject CardAuthoringProjectStore::normalizeProject(const QJsonObject& project) const {
    return CardAuthoring::normalizeProject(project);
}

QString CardAuthoringProjectStore::safeProjectFilename(const QString& filename) {
    QString safe = filename.trimmed();
    safe.replace(QLatin1Char('\\'), QLatin1Char('_'));
    safe.replace(QLatin1Char('/'), QLatin1Char('_'));
    safe.replace(QRegularExpression(QStringLiteral("[<>:\"|?*]+")), QStringLiteral("_"));
    safe = safe.trimmed();
    if (safe.isEmpty()) {
        safe = QStringLiteral("untitled");
    }
    if (!safe.endsWith(CardAuthoringPaths::projectFileExtension(), Qt::CaseInsensitive)) {
        safe += CardAuthoringPaths::projectFileExtension();
    }
    return safe;
}

QJsonObject CardAuthoringProjectStore::loadWorkspace(QString* errorMessage) const {
    return readProjectFile(paths_.workspacePath(), errorMessage);
}

QJsonObject CardAuthoringProjectStore::saveWorkspace(const QJsonObject& project, QString* savedPath, QString* errorMessage) const {
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }
    QJsonObject normalized = normalizeProject(project);
    normalized.insert(QStringLiteral("updated_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
    if (!writeProjectFile(paths_.workspacePath(), normalized, errorMessage)) {
        return {};
    }
    const QString autosavePath = QDir(paths_.autosavesPath()).absoluteFilePath(QStringLiteral("autosave.cardwork.json"));
    if (!writeProjectFile(autosavePath, normalized, errorMessage)) {
        return {};
    }
    if (savedPath) {
        *savedPath = paths_.workspacePath();
    }
    return normalized;
}

QJsonArray CardAuthoringProjectStore::listProjects(QString* errorMessage) const {
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }

    QJsonArray result;
    QDir projectsDir(paths_.projectsPath());
    const QFileInfoList entries = projectsDir.entryInfoList(
        QStringList{ QStringLiteral("*.cardwork.json") },
        QDir::Files | QDir::Readable,
        QDir::Time | QDir::Name);
    for (const QFileInfo& entry : entries) {
        QString readError;
        const QJsonObject project = readProjectFile(entry.absoluteFilePath(), &readError);
        result.append(projectListItem(entry, project, readError));
    }
    return result;
}

QJsonObject CardAuthoringProjectStore::loadProject(const QString& filename, QString* errorMessage) const {
    return readProjectFile(paths_.projectPath(safeProjectFilename(filename)), errorMessage);
}

QJsonObject CardAuthoringProjectStore::saveProject(const QString& filename, const QJsonObject& project, QString* savedPath, QString* errorMessage) const {
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }
    QJsonObject normalized = normalizeProject(project);
    normalized.insert(QStringLiteral("updated_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
    const QString path = paths_.projectPath(safeProjectFilename(filename));
    if (!writeProjectFile(path, normalized, errorMessage)) {
        return {};
    }
    if (savedPath) {
        *savedPath = path;
    }
    return normalized;
}

QJsonObject CardAuthoringProjectStore::deleteProject(const QString& filename, QString* archivedPath, QString* errorMessage) const {
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }

    const QString safeFilename = safeProjectFilename(filename);
    const QString path = paths_.projectPath(safeFilename);
    QFileInfo sourceInfo(path);
    if (!sourceInfo.exists() || !sourceInfo.isFile()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("card authoring project does not exist: %1").arg(safeFilename);
        }
        return {};
    }

    QString readError;
    const QJsonObject project = readProjectFile(path, &readError);
    if (project.isEmpty() && !readError.isEmpty()) {
        if (errorMessage) {
            *errorMessage = readError;
        }
        return {};
    }

    QDir backupRoot(paths_.backupsPath());
    if (!backupRoot.mkpath(QStringLiteral("projects"))) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to create card authoring project archive directory");
        }
        return {};
    }

    const QString archiveFileName = QStringLiteral("%1.deleted.%2%3")
        .arg(projectBaseName(safeFilename), timestampSuffix(), CardAuthoringPaths::projectFileExtension());
    const QString archivePath = uniqueFilePathInDir(QDir(backupRoot.absoluteFilePath(QStringLiteral("projects"))), archiveFileName);
    if (!QFile::rename(path, archivePath)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to archive card authoring project");
        }
        return {};
    }

    if (archivedPath) {
        *archivedPath = archivePath;
    }
    return project;
}

QJsonObject CardAuthoringProjectStore::importProjectFile(const QString& sourcePath, QString* importedPath, QString* errorMessage) const {
    if (!paths_.ensureRuntimeDirectories(errorMessage)) {
        return {};
    }

    const QFileInfo sourceInfo(QDir::fromNativeSeparators(sourcePath));
    if (!sourceInfo.exists() || !sourceInfo.isFile()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("card authoring import file does not exist");
        }
        return {};
    }

    QJsonObject project = readProjectFile(sourceInfo.absoluteFilePath(), errorMessage);
    if (project.isEmpty()) {
        return {};
    }

    const QString fallback = projectTitleFallback(project, sourceInfo.completeBaseName());
    const QString filename = uniqueProjectFilename(fallback);
    return saveProject(filename, project, importedPath, errorMessage);
}

QJsonObject CardAuthoringProjectStore::exportProjectFile(const QString& targetPath, const QJsonObject& project, QString* exportedPath, QString* errorMessage) const {
    const QString path = exportFilePath(targetPath, project, errorMessage);
    if (path.isEmpty()) {
        return {};
    }

    QJsonObject normalized = normalizeProject(project);
    normalized.insert(QStringLiteral("updated_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
    if (!writeProjectFile(path, normalized, errorMessage)) {
        return {};
    }
    if (exportedPath) {
        *exportedPath = path;
    }
    return normalized;
}

bool CardAuthoringProjectStore::writeProjectFile(const QString& path, const QJsonObject& project, QString* errorMessage) const {
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to open card authoring project: %1").arg(file.errorString());
        }
        return false;
    }
    file.write(QJsonDocument(project).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to save card authoring project: %1").arg(file.errorString());
        }
        return false;
    }
    return true;
}

QJsonObject CardAuthoringProjectStore::readProjectFile(const QString& path, QString* errorMessage) const {
    QFile file(path);
    if (!file.exists()) {
        return createEmptyProject();
    }
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("failed to read card authoring project: %1").arg(file.errorString());
        }
        return {};
    }
    QJsonParseError error;
    const QJsonDocument document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("invalid card authoring project JSON: %1").arg(error.errorString());
        }
        return {};
    }
    return normalizeProject(document.object());
}

QString CardAuthoringProjectStore::exportFilePath(const QString& targetPath, const QJsonObject& project, QString* errorMessage) const {
    const QString cleaned = QDir::fromNativeSeparators(targetPath).trimmed();
    if (cleaned.isEmpty()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("card authoring export path is empty");
        }
        return {};
    }

    QFileInfo targetInfo(cleaned);
    QDir targetDir = targetInfo.exists() && targetInfo.isDir()
        ? QDir(targetInfo.absoluteFilePath())
        : targetInfo.absoluteDir();
    if (!targetDir.exists()) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("card authoring export directory does not exist");
        }
        return {};
    }

    QString fileName = targetInfo.exists() && targetInfo.isDir()
        ? projectTitleFallback(project, QStringLiteral("project"))
        : targetInfo.fileName().trimmed();
    if (fileName.isEmpty()) {
        fileName = projectTitleFallback(project, QStringLiteral("project"));
    }
    if (fileName.endsWith(QStringLiteral(".json"), Qt::CaseInsensitive)
        && !fileName.endsWith(CardAuthoringPaths::projectFileExtension(), Qt::CaseInsensitive)) {
        fileName.chop(QStringLiteral(".json").size());
    }
    return targetDir.absoluteFilePath(safeProjectFilename(fileName));
}

QString CardAuthoringProjectStore::uniqueProjectFilename(const QString& filename) const {
    const QString safe = safeProjectFilename(filename);
    if (!QFileInfo::exists(paths_.projectPath(safe))) {
        return safe;
    }

    const QString baseName = projectBaseName(safe);
    const QString extension = CardAuthoringPaths::projectFileExtension();
    for (int attempt = 1; attempt <= 100; ++attempt) {
        const QString candidate = QStringLiteral("%1-%2%3").arg(baseName).arg(attempt).arg(extension);
        if (!QFileInfo::exists(paths_.projectPath(candidate))) {
            return candidate;
        }
    }
    return QStringLiteral("%1-%2%3")
        .arg(baseName, QUuid::createUuid().toString(QUuid::WithoutBraces), extension);
}
