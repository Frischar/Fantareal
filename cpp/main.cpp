#include "fantarealbridge.h"

#include <QGuiApplication>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QQuickWindow>
#include <QQmlApplicationEngine>
#include <QQmlError>
#include <QSGRendererInterface>
#include <QTextStream>
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

    FantarealBridge bridge;
    qmlRegisterSingletonInstance("Fantareal", 1, 0, "FantarealBridge", &bridge);
    engine.loadFromModule("Fantareal", "FantarealApp");

    if (engine.rootObjects().isEmpty()) {
        qCritical() << "QML root object load failed. Import paths:" << engine.importPathList();
        return 1;
    }

    return QGuiApplication::exec();
}
