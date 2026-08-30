// AnimeOS - desktop reveal launcher.
//
// Runs once at session start, on top of the real desktop, with one window per
// screen. The petals video is a 1920x1080 scene (packed colour|matte), so each
// window plays it 1:1 on its own monitor; mirroring per screen keeps the petal
// aspect correct and matches how the SDDM greeter itself is mirrored, so the
// whole cinematic reads as one system-wide moment instead of a stretched one.
#include <QCoreApplication>
#include <QGuiApplication>
#include <QQmlEngine>
#include <QQuickView>
#include <QScreen>
#include <QTimer>
#include <cstdio>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    const QUrl qmlFile = QUrl::fromLocalFile(
        QCoreApplication::applicationDirPath() + QStringLiteral("/Reveal.qml"));

    QList<QQuickView *> views;
    for (QScreen *screen : QGuiApplication::screens()) {
        QQuickView *view = new QQuickView;
        view->setFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint
                       | Qt::Tool | Qt::WindowTransparentForInput);
        view->setColor(Qt::transparent);
        view->setResizeMode(QQuickView::SizeRootObjectToView);
        view->setScreen(screen);
        view->setSource(qmlFile);
        view->showFullScreen();
        fprintf(stderr, "reveal: requested screen %s at %d,%d\n",
                screen->name().toUtf8().constData(),
                screen->geometry().x(), screen->geometry().y());
        // KWin ignores the pre-map screen hint on Wayland and maps every new
        // window to one output; re-applying the screen after the surface is
        // mapped is what actually moves it.
        QTimer::singleShot(400, view, [view, screen]() {
            view->setScreen(screen);
        });
        if (QQmlEngine *engine = qmlEngine(view))
            QObject::connect(engine, &QQmlEngine::quit,
                             &app, &QCoreApplication::quit);
        views.append(view);
    }

    // Report where the compositor actually placed each window, so a window
    // that lands on the wrong output is visible in the log instead of silent.
    for (QQuickView *view : views) {
        QTimer::singleShot(1200, view, [view]() {
            const QScreen *s = view->screen();
            fprintf(stderr, "reveal: view now on %s geometry %d,%d %dx%d\n",
                    s ? s->name().toUtf8().constData() : "none",
                    view->geometry().x(), view->geometry().y(),
                    view->geometry().width(), view->geometry().height());
        });
    }

    // Hard backstop, mirroring the QML timer: under QQuickView a QML
    // Qt.quit() has been seen not to reach QCoreApplication, so an
    // always-on-top window could otherwise outlive the animation. The
    // dissolve is over long before this fires; anything left is transparent.
    QTimer::singleShot(3500, &app, &QCoreApplication::quit);

    const int rc = app.exec();
    qDeleteAll(views);
    return rc;
}
