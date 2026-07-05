#include "tray_service.h"

TrayService::TrayService(QObject* parent)
    : QObject(parent)
    , m_trayIcon(nullptr)
    , m_menu(nullptr)
{
}

TrayService::~TrayService()
{
    hide();
}

bool TrayService::setup(const QIcon& icon, const QString& tooltip)
{
    if (!QSystemTrayIcon::isSystemTrayAvailable()) {
        return false;
    }

    m_trayIcon = new QSystemTrayIcon(icon, this);
    m_trayIcon->setToolTip(tooltip);

    m_menu = new QMenu();
    m_showAction = m_menu->addAction("显示窗口");
    m_runAction = m_menu->addAction("全部运行");
    m_menu->addSeparator();
    m_quitAction = m_menu->addAction("退出");

    m_trayIcon->setContextMenu(m_menu);

    connect(m_showAction, &QAction::triggered, this, &TrayService::showWindowRequested);
    connect(m_runAction, &QAction::triggered, this, &TrayService::runDashboardRequested);
    connect(m_quitAction, &QAction::triggered, this, &TrayService::quitRequested);
    connect(m_trayIcon, &QSystemTrayIcon::activated, this,
        [this](QSystemTrayIcon::ActivationReason reason) {
            if (reason == QSystemTrayIcon::DoubleClick) {
                emit showWindowRequested();
            }
        });

    return true;
}

void TrayService::show()
{
    if (m_trayIcon) {
        m_trayIcon->show();
    }
}

void TrayService::hide()
{
    if (m_trayIcon) {
        m_trayIcon->hide();
    }
}

bool TrayService::is_visible() const
{
    return m_trayIcon && m_trayIcon->isVisible();
}
