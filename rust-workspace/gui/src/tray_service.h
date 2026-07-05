#pragma once

#include <QObject>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QAction>
#include <QIcon>

class TrayService : public QObject
{
    Q_OBJECT

public:
    explicit TrayService(QObject* parent = nullptr);
    ~TrayService();

    bool setup(const QIcon& icon, const QString& tooltip = "SimpleRPA");
    void show();
    void hide();
    bool is_visible() const;

signals:
    void showWindowRequested();
    void runDashboardRequested();
    void quitRequested();

private:
    QSystemTrayIcon* m_trayIcon;
    QMenu* m_menu;
    QAction* m_showAction;
    QAction* m_runAction;
    QAction* m_quitAction;
};
