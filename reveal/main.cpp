// AnimeOS - desktop reveal launcher.
//
// Runs once at session start, over the desktop, with one layer-shell overlay
// window per screen. The petals video is a 1920x1080 scene (packed
// colour|matte), so each window plays it 1:1 on its own monitor.
//
// A layer-shell overlay (rather than a plain window) is what makes this work
// at session start: the compositor shows it above everything the moment the
// reveal starts, with no dependence on the desktop shell having finished
// loading -- the KSplashQML splash proved that early-start plumbing is where
// the fragility lived. Started by animeos-reveal.service right after KWin.
#include <QCoreApplication>
#include <QGuiApplication>
#include <QQmlEngine>
#include <QQuickView>
#include <QScreen>
#include <QTimer>

#include <LayerShellQt/Shell>
#include <LayerShellQt/Window>

int main(int argc, char *argv[])
{
    qputenv("QT_QPA_PLATFORM", "wayland");
    LayerShellQt::Shell::useLayerShell();

    QGuiApplication app(argc, argv);

    const QUrl qmlFile = QUrl::fromLocalFile(
        QCoreApplication::applicationDirPath() + QStringLiteral("/Reveal.qml"));

    QList<QQuickView *> views;
    for (QScreen *screen : QGuiApplication::screens()) {
        QQuickView *view = new QQuickView;
        view->setFlags(Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint
                       | Qt::Tool);
        view->setColor(Qt::transparent);
        view->setDefaultAlphaBuffer(true);
        view->setResizeMode(QQuickView::SizeRootObjectToView);
        view->setScreen(screen);
        view->setGeometry(screen->geometry());
        view->setSource(qmlFile);

        if (auto *layer = LayerShellQt::Window::get(view)) {
            layer->setScope(QStringLiteral("animeos-reveal"));
            layer->setLayer(LayerShellQt::Window::LayerOverlay);
            layer->setExclusiveZone(-1);
            layer->setKeyboardInteractivity(LayerShellQt::Window::KeyboardInteractivityNone);
            layer->setScreen(screen);
        }

        view->show();
        // QQuickView::engine() is the engine that loaded the QML; qmlEngine()
        // looks the engine up on a QML object and returns null for the window.
        if (QQmlEngine *engine = view->engine())
            QObject::connect(engine, &QQmlEngine::quit,
                             &app, &QCoreApplication::quit);
        views.append(view);
    }

    // Hard backstop. If the media never loads, or the animation is somehow
    // never driven, an always-on-top window that stays alive is far worse than
    // no reveal at all -- so quit regardless. The dissolve is over long before
    // this; anything left is transparent.
    QTimer::singleShot(6000, &app, &QCoreApplication::quit);

    const int rc = app.exec();
    qDeleteAll(views);
    return rc;
}
