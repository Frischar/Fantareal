#include "fantarealbridge.h"

#include <QGuiApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QQuickWindow>
#include <QQmlApplicationEngine>
#include <QQmlError>
#include <QSGRendererInterface>
#include <QStringList>
#include <QTextStream>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>
#include <QtQml/qqml.h>

#ifdef BUILD_HUSKARUI_STATIC_LIBRARY
#include <QtQml/qqmlextensionplugin.h>
Q_IMPORT_QML_PLUGIN(HuskarUI_ImplPlugin)
Q_IMPORT_QML_PLUGIN(HuskarUI_BasicPlugin)
#endif

#include "husapp.h"

namespace {

void runtimeMessageHandler(QtMsgType type, const QMessageLogContext& context, const QString& message) {
    const QString logPath = QCoreApplication::applicationDirPath() + QStringLiteral("/FantarealHuskarUI.log");
    QFile logFile(logPath);
    if (logFile.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
        QTextStream stream(&logFile);
        stream << QDateTime::currentDateTime().toString(Qt::ISODateWithMs) << " ";
        switch (type) {
        case QtDebugMsg:
            stream << "DEBUG";
            break;
        case QtInfoMsg:
            stream << "INFO";
            break;
        case QtWarningMsg:
            stream << "WARN";
            break;
        case QtCriticalMsg:
            stream << "CRITICAL";
            break;
        case QtFatalMsg:
            stream << "FATAL";
            break;
        }
        stream << " " << message;
        if (context.file) {
            stream << " (" << context.file << ":" << context.line << ")";
        }
        stream << "\n";
    }
}

bool hasArgument(const QStringList& arguments, const QString& option) {
    return arguments.contains(option);
}

int runCardAuthoringDefaultExports(FantarealBridge& bridge) {
    QTextStream out(stdout);
    QTextStream err(stderr);

    const QVariantMap loadResult = bridge.loadCardAuthoringWorkspace();
    if (!loadResult.value(QStringLiteral("ok")).toBool()) {
        err << "loadCardAuthoringWorkspace failed: "
            << loadResult.value(QStringLiteral("message")).toString()
            << "\n";
        return 2;
    }

    QVariantMap draft = loadResult.value(QStringLiteral("project")).toMap();
    if (draft.isEmpty()) {
        draft = bridge.cardAuthoringDraft();
    }
    if (draft.isEmpty()) {
        err << "card authoring draft is empty\n";
        return 3;
    }

    const QVariantMap projectExport = bridge.exportCardAuthoringProjectToDefaultDir(draft);
    if (!projectExport.value(QStringLiteral("ok")).toBool()) {
        err << "exportCardAuthoringProjectToDefaultDir failed: "
            << projectExport.value(QStringLiteral("message")).toString()
            << "\n";
        return 4;
    }

    const QVariantMap compiledExport = bridge.exportCompiledCardAuthoringRoleCardToDefaultDir(draft);
    if (!compiledExport.value(QStringLiteral("ok")).toBool()) {
        err << "exportCompiledCardAuthoringRoleCardToDefaultDir failed: "
            << compiledExport.value(QStringLiteral("message")).toString()
            << "\n";
        return 5;
    }

    out << "Card authoring default exports completed\n";
    out << "ProjectExport: " << projectExport.value(QStringLiteral("exportedPath")).toString() << "\n";
    out << "CompiledRoleCardExport: " << compiledExport.value(QStringLiteral("exportedPath")).toString() << "\n";
    return 0;
}

QString fantarealRuntimeRoot() {
    const QString envRoot = qEnvironmentVariable("FANTAREAL_ROOT").trimmed();
    if (!envRoot.isEmpty()) {
        return QDir::fromNativeSeparators(envRoot);
    }
    return QDir::currentPath();
}

QString firstExistingPath(const QStringList& paths) {
    for (const QString& path : paths) {
        if (!path.trimmed().isEmpty() && QFileInfo::exists(path)) {
            return path;
        }
    }
    return {};
}

QString cardAuthoringAcceptanceSamplePath(const QString& runtimeRoot) {
    const QString envSample = qEnvironmentVariable("FANTAREAL_CARD_AUTHORING_SAMPLE").trimmed();
    const QDir root(runtimeRoot);
    const QDir appDir(QCoreApplication::applicationDirPath());
    return firstExistingPath({
        QDir::fromNativeSeparators(envSample),
        root.absoluteFilePath(QStringLiteral("manual_acceptance_samples/card-authoring-full.cardwork.json")),
        appDir.absoluteFilePath(QStringLiteral("../manual_acceptance_samples/card-authoring-full.cardwork.json")),
    });
}

QVariantMap compactStep(const QString& name, const QVariantMap& result) {
    QVariantMap step;
    step.insert(QStringLiteral("name"), name);
    step.insert(QStringLiteral("ok"), result.value(QStringLiteral("ok")).toBool());
    step.insert(QStringLiteral("message"), result.value(QStringLiteral("message")).toString());

    const QStringList copiedKeys = {
        QStringLiteral("savedPath"),
        QStringLiteral("importedPath"),
        QStringLiteral("archivedPath"),
        QStringLiteral("exportedPath"),
        QStringLiteral("filename"),
        QStringLiteral("warning_count"),
    };
    for (const QString& key : copiedKeys) {
        if (result.contains(key)) {
            step.insert(key, result.value(key));
        }
    }
    if (result.contains(QStringLiteral("summary"))) {
        step.insert(QStringLiteral("summary"), result.value(QStringLiteral("summary")));
    }
    if (result.contains(QStringLiteral("backups"))) {
        step.insert(QStringLiteral("backup_count"), result.value(QStringLiteral("backups")).toList().size());
    }
    if (result.contains(QStringLiteral("backupPath"))) {
        step.insert(QStringLiteral("backupPath"), result.value(QStringLiteral("backupPath")));
    }
    if (result.contains(QStringLiteral("candidates"))) {
        step.insert(QStringLiteral("candidate_count"), result.value(QStringLiteral("candidates")).toList().size());
    }
    return step;
}

bool appendCheckedStep(
    QVariantList* steps,
    const QString& name,
    const QVariantMap& result,
    QTextStream& err) {
    steps->append(compactStep(name, result));
    if (!result.value(QStringLiteral("ok")).toBool()) {
        err << name << " failed: " << result.value(QStringLiteral("message")).toString() << "\n";
        return false;
    }
    return true;
}

bool writeCardAuthoringAcceptanceReport(
    const QString& runtimeRoot,
    const QVariantMap& report,
    QString* reportPath,
    QString* errorMessage) {
    QDir root(runtimeRoot);
    const QString relativeDir = QStringLiteral("data/card_authoring/acceptance");
    if (!root.mkpath(relativeDir)) {
        if (errorMessage) {
            *errorMessage = QStringLiteral("cannot create %1").arg(root.absoluteFilePath(relativeDir));
        }
        return false;
    }

    const QString path = root.absoluteFilePath(relativeDir + QStringLiteral("/headless_acceptance.json"));
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        if (errorMessage) {
            *errorMessage = file.errorString();
        }
        return false;
    }
    const QByteArray payload = QJsonDocument::fromVariant(report).toJson(QJsonDocument::Indented);
    if (file.write(payload) != payload.size()) {
        if (errorMessage) {
            *errorMessage = file.errorString();
        }
        return false;
    }
    if (reportPath) {
        *reportPath = path;
    }
    return true;
}

QVariantMap headlessAcceptanceCandidateReview() {
    return QVariantMap{
        { QStringLiteral("summary"), QStringLiteral("headless acceptance candidate review") },
        { QStringLiteral("candidates"), QVariantList{
            QVariantMap{
                { QStringLiteral("id"), QStringLiteral("headless_acceptance_database_tag") },
                { QStringLiteral("module"), QStringLiteral("database") },
                { QStringLiteral("action"), QStringLiteral("json_patch") },
                { QStringLiteral("target"), QVariantMap{
                    { QStringLiteral("path"), QStringLiteral("database.tags") },
                    { QStringLiteral("operation"), QStringLiteral("append") },
                } },
                { QStringLiteral("after"), QVariantMap{
                    { QStringLiteral("tag"), QStringLiteral("database.tag.headless-acceptance") },
                    { QStringLiteral("title"), QStringLiteral("Headless Acceptance Tag") },
                    { QStringLiteral("trigger"), QStringLiteral("headless acceptance trigger") },
                    { QStringLiteral("target"), QStringLiteral("worldbook") },
                    { QStringLiteral("description"), QStringLiteral("Generated by the packaged headless acceptance flow.") },
                    { QStringLiteral("notes"), QStringLiteral("Headless acceptance should auto-create a tag consumer.") },
                } },
                { QStringLiteral("group_id"), QStringLiteral("database_mechanism") },
            },
        } },
    };
}

int runCardAuthoringHeadlessAcceptance(FantarealBridge& bridge) {
    QTextStream out(stdout);
    QTextStream err(stderr);

    const QString runtimeRoot = fantarealRuntimeRoot();
    const QString samplePath = cardAuthoringAcceptanceSamplePath(runtimeRoot);
    QVariantList steps;
    QVariantMap report;
    report.insert(QStringLiteral("ok"), false);
    report.insert(QStringLiteral("runtimeRoot"), runtimeRoot);
    report.insert(QStringLiteral("samplePath"), samplePath);
    report.insert(QStringLiteral("startedAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));

    auto finish = [&](int code) {
        report.insert(QStringLiteral("finishedAt"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
        report.insert(QStringLiteral("steps"), steps);
        report.insert(QStringLiteral("ok"), code == 0);
        QString reportPath;
        QString reportError;
        if (writeCardAuthoringAcceptanceReport(runtimeRoot, report, &reportPath, &reportError)) {
            out << "HeadlessAcceptanceReport: " << reportPath << "\n";
        } else {
            err << "headless acceptance report write failed: " << reportError << "\n";
        }
        return code;
    };

    const QVariantMap runtimeLoad = bridge.loadCurrentRuntimeCardAuthoringDraft();
    if (!appendCheckedStep(&steps, QStringLiteral("loadCurrentRuntimeCardAuthoringDraft"), runtimeLoad, err)) {
        return finish(2);
    }

    QVariantMap draft;
    if (!samplePath.isEmpty()) {
        const QVariantMap importResult = bridge.importCardAuthoringProjectFile(QUrl::fromLocalFile(samplePath).toString());
        if (!appendCheckedStep(&steps, QStringLiteral("importManualAcceptanceSample"), importResult, err)) {
            return finish(3);
        }
        draft = importResult.value(QStringLiteral("project")).toMap();
    } else {
        draft = runtimeLoad.value(QStringLiteral("project")).toMap();
    }
    if (draft.isEmpty()) {
        err << "headless acceptance draft is empty\n";
        return finish(4);
    }
    draft.insert(QStringLiteral("title"), QStringLiteral("Headless Acceptance Project"));

    const QVariantMap archiveProject = bridge.saveCardAuthoringProject(
        QStringLiteral("headless-acceptance-archive.cardwork.json"),
        draft);
    if (!appendCheckedStep(&steps, QStringLiteral("saveArchiveProbeProject"), archiveProject, err)) {
        return finish(5);
    }
    const QVariantMap deleteArchiveProject = bridge.deleteCardAuthoringProject(
        QStringLiteral("headless-acceptance-archive.cardwork.json"));
    if (!appendCheckedStep(&steps, QStringLiteral("deleteArchiveProbeProject"), deleteArchiveProject, err)) {
        return finish(6);
    }

    const QVariantMap normalizeCandidates = bridge.normalizeCardAuthoringCandidates(
        draft,
        headlessAcceptanceCandidateReview());
    if (!appendCheckedStep(&steps, QStringLiteral("normalizeAcceptanceCandidates"), normalizeCandidates, err)) {
        return finish(7);
    }
    const QVariantMap applyCandidates = bridge.applyCardAuthoringCandidates(
        draft,
        headlessAcceptanceCandidateReview(),
        QVariantList{ QStringLiteral("headless_acceptance_database_tag") });
    if (!appendCheckedStep(&steps, QStringLiteral("applySelectedAcceptanceCandidate"), applyCandidates, err)) {
        return finish(8);
    }
    draft = applyCandidates.value(QStringLiteral("project")).toMap();
    if (draft.isEmpty()) {
        err << "headless acceptance candidate project is empty\n";
        return finish(9);
    }

    const QVariantMap saveWorkspace = bridge.saveCardAuthoringWorkspace(draft);
    if (!appendCheckedStep(&steps, QStringLiteral("saveWorkspace"), saveWorkspace, err)) {
        return finish(10);
    }
    draft = saveWorkspace.value(QStringLiteral("project")).toMap();

    const QVariantMap saveProject = bridge.saveCardAuthoringProject(
        QStringLiteral("headless-acceptance.cardwork.json"),
        draft);
    if (!appendCheckedStep(&steps, QStringLiteral("saveProject"), saveProject, err)) {
        return finish(11);
    }
    draft = saveProject.value(QStringLiteral("project")).toMap();

    const QVariantMap validate = bridge.validateCardAuthoringDraft(draft);
    if (!appendCheckedStep(&steps, QStringLiteral("validateDraft"), validate, err)) {
        return finish(12);
    }

    const QVariantMap compile = bridge.compileCardAuthoringDraft(draft);
    if (!appendCheckedStep(&steps, QStringLiteral("compileDraft"), compile, err)) {
        return finish(13);
    }

    const QVariantList allModules{
        QStringLiteral("persona"),
        QStringLiteral("database"),
        QStringLiteral("worldbook"),
        QStringLiteral("preset"),
        QStringLiteral("memory"),
    };
    const QVariantMap preview = bridge.previewCardAuthoringApply(draft, allModules);
    if (!appendCheckedStep(&steps, QStringLiteral("previewAllModules"), preview, err)) {
        return finish(14);
    }
    if (preview.value(QStringLiteral("summary")).toMap().value(QStringLiteral("change_count")).toInt() <= 0) {
        err << "previewAllModules produced no changes\n";
        return finish(15);
    }

    const QVariantMap apply = bridge.applyCardAuthoringDraft(draft, allModules);
    if (!appendCheckedStep(&steps, QStringLiteral("applyAllModules"), apply, err)) {
        return finish(16);
    }
    if (apply.value(QStringLiteral("backups")).toList().isEmpty()
        && apply.value(QStringLiteral("backupPath")).toString().isEmpty()) {
        err << "applyAllModules did not report backups\n";
        return finish(17);
    }

    const QVariantMap projectExport = bridge.exportCardAuthoringProjectToDefaultDir(draft);
    if (!appendCheckedStep(&steps, QStringLiteral("exportProjectToDefaultDir"), projectExport, err)) {
        return finish(18);
    }

    const QVariantMap compiledExport = bridge.exportCompiledCardAuthoringRoleCardToDefaultDir(draft);
    if (!appendCheckedStep(&steps, QStringLiteral("exportCompiledRoleCardToDefaultDir"), compiledExport, err)) {
        return finish(19);
    }

    report.insert(QStringLiteral("projectExportPath"), projectExport.value(QStringLiteral("exportedPath")).toString());
    report.insert(QStringLiteral("compiledRoleCardExportPath"), compiledExport.value(QStringLiteral("exportedPath")).toString());
    out << "Card authoring headless acceptance completed\n";
    out << "ProjectExport: " << report.value(QStringLiteral("projectExportPath")).toString() << "\n";
    out << "CompiledRoleCardExport: " << report.value(QStringLiteral("compiledRoleCardExportPath")).toString() << "\n";
    return finish(0);
}

}

int main(int argc, char* argv[]) {
#ifndef Q_OS_MAC
    QQuickWindow::setGraphicsApi(QSGRendererInterface::OpenGL);
#endif
    QQuickWindow::setDefaultAlphaBuffer(true);

    qInstallMessageHandler(runtimeMessageHandler);

    QGuiApplication app(argc, argv);
    app.setOrganizationName(QStringLiteral("Fantareal"));
    app.setApplicationName(QStringLiteral("FantarealHuskarUI"));
    app.setApplicationDisplayName(QStringLiteral("Fantareal PC"));
    app.setApplicationVersion(QStringLiteral("0.1.0"));

    FantarealBridge bridge;
    if (hasArgument(app.arguments(), QStringLiteral("--card-authoring-export-defaults"))) {
        return runCardAuthoringDefaultExports(bridge);
    }
    if (hasArgument(app.arguments(), QStringLiteral("--card-authoring-headless-acceptance"))) {
        return runCardAuthoringHeadlessAcceptance(bridge);
    }

    QQmlApplicationEngine engine;
    QObject::connect(&engine, &QQmlApplicationEngine::warnings, &app, [](const QList<QQmlError>& warnings) {
        for (const QQmlError& warning : warnings) {
            qWarning().noquote() << warning.toString();
        }
    });

    const QString packagedHuskarUIPath = QCoreApplication::applicationDirPath() + QStringLiteral("/HuskarUI/qml");
    if (QDir(packagedHuskarUIPath).exists()) {
        engine.addImportPath(packagedHuskarUIPath);
    }
    HusApp::initialize(&engine);

    qmlRegisterSingletonInstance("Fantareal", 1, 0, "FantarealBridge", &bridge);
    engine.loadFromModule("Fantareal", "FantarealApp");

    if (engine.rootObjects().isEmpty()) {
        qCritical() << "QML root object load failed. Import paths:" << engine.importPathList();
        return 1;
    }

    return QGuiApplication::exec();
}
