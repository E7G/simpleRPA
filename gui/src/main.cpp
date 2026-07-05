#include <QApplication>
#include <QIcon>
#include <QSplashScreen>
#include <QPixmap>
#include <QPainter>
#include <QFont>
#include <QColor>
#include <QLinearGradient>
#include <QScreen>

#include "main_window.h"

static QPixmap createSplash() {
    int w = 480, h = 200;
    QPixmap pixmap(w, h);
    pixmap.fill(Qt::transparent);

    QPainter painter(&pixmap);
    painter.setRenderHint(QPainter::Antialiasing);

    QLinearGradient grad(0, 0, w, h);
    grad.setColorAt(0, QColor(0, 120, 212));
    grad.setColorAt(1, QColor(116, 39, 116));
    painter.fillRect(0, 0, w, h, grad);

    painter.setPen(QColor(255, 255, 255));
    QFont font("Segoe UI", 26, QFont::Bold);
    painter.setFont(font);
    painter.drawText(pixmap.rect().adjusted(0, -24, 0, 0), Qt::AlignCenter, "SimpleRPA");

    QFont font2("Segoe UI", 10);
    painter.setFont(font2);
    painter.setPen(QColor(230, 230, 255));
    painter.drawText(pixmap.rect().adjusted(0, 28, 0, 0), Qt::AlignCenter, "桌面流程自动化 (Rust + C++)");

    painter.end();
    return pixmap;
}

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName("SimpleRPA");
    app.setApplicationVersion("0.2.0");

    QSplashScreen splash(createSplash());
    splash.show();
    app.processEvents();

    MainWindow window;
    window.show();
    splash.finish(&window);

    return app.exec();
}
