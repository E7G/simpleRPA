#include <QApplication>
#include "Theme.h"
#include "main_window.h"

int main(int argc, char *argv[])
{
#if QT_VERSION >= QT_VERSION_CHECK(5, 14, 0)
    QGuiApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);
#endif
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QCoreApplication::setAttribute(Qt::AA_EnableHighDpiScaling);
    QCoreApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
#endif
    QCoreApplication::setAttribute(Qt::AA_DontCreateNativeWidgetSiblings);

    QApplication app(argc, argv);
    app.setStyle("Fusion");

    QFont font;
    font.setFamilies({"Microsoft YaHei", "PingFang SC", "Segoe UI"});
    font.setPixelSize(14);
    app.setFont(font);

    Theme::setThemeColor(QColor("#0066b4"), true);
    Theme::setThemeMode(Fluent::ThemeMode::AUTO, true);

    MainWindow w;
    w.show();
    return app.exec();
}
