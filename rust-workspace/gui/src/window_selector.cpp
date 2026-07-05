#include "window_selector.h"
#include <QJsonDocument>
#include <QJsonArray>
#include <QJsonObject>
#include <QHBoxLayout>
#include <QShowEvent>
#include "fluent_theme.h"

using FIT = Fluent::IconType;

WindowSelector::WindowSelector(QWidget* parent)
    : QWidget(parent)
    , m_windowUtils(window_utils_new())
    , m_refreshed(false)
{
    setupUI();
    connect(m_refreshBtn, &QPushButton::clicked, this, &WindowSelector::onRefreshClicked);
    connect(m_windowCombo, &ComboBox::currentIndexChanged, this, &WindowSelector::onSelectionChanged);
}

WindowSelector::~WindowSelector()
{
    window_utils_free(m_windowUtils);
}

void WindowSelector::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(6);

    auto* rowLayout = new QHBoxLayout();
    rowLayout->setSpacing(4);

    m_windowCombo = new ComboBox();
    m_windowCombo->setPlaceholderText(QStringLiteral("\u8bf7\u9009\u62e9\u7a97\u53e3..."));
    m_windowCombo->setMinimumWidth(200);
    rowLayout->addWidget(m_windowCombo, 1);

    m_refreshBtn = new PushButton(QStringLiteral("\u5237\u65b0"), FIT::SYNC);
    m_refreshBtn->setFixedWidth(72);
    rowLayout->addWidget(m_refreshBtn);

    layout->addLayout(rowLayout);

    m_statusLabel = new CaptionLabel();
    m_statusLabel->setStyleSheet(FluentTheme::mutedCaptionStyle());
    layout->addWidget(m_statusLabel);
}

void WindowSelector::refreshWindows()
{
    m_windows.clear();
    m_windowCombo->clear();

    char* json = window_utils_get_all_windows_json(m_windowUtils);
    if (!json) {
        m_statusLabel->setText(QStringLiteral("\u65e0\u6cd5\u83b7\u53d6\u7a97\u53e3\u5217\u8868"));
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(json).toUtf8());
    window_utils_free_string(json);

    if (!doc.isArray()) {
        m_statusLabel->setText(QStringLiteral("\u7a97\u53e3\u6570\u636e\u683c\u5f0f\u9519\u8bef"));
        return;
    }

    QJsonArray arr = doc.array();
    for (int i = 0; i < arr.size(); ++i) {
        QJsonObject obj = arr[i].toObject();
        int64_t hwnd = obj["hwnd"].toVariant().toLongLong();
        QString title = obj["title"].toString();
        int width = obj["width"].toInt();
        int height = obj["height"].toInt();

        WindowInfo info;
        info.hwnd = hwnd;
        info.title = title;
        info.x = obj["x"].toInt();
        info.y = obj["y"].toInt();
        m_windows.append(info);

        QString display = QString("%1 [%2x%3]")
            .arg(title.isEmpty() ? QStringLiteral("\u65e0\u6807\u9898\u7a97\u53e3") : title)
            .arg(width).arg(height);
        m_windowCombo->addItem(display);
    }

    m_statusLabel->setText(QStringLiteral("\u627e\u5230 %1 \u4e2a\u7a97\u53e3").arg(m_windows.size()));
    m_refreshed = true;
}

int64_t WindowSelector::getSelectedHwnd() const
{
    int index = m_windowCombo->currentIndex();
    if (index < 0 || index >= m_windows.size()) return 0;
    return m_windows[index].hwnd;
}

QString WindowSelector::getSelectedTitle() const
{
    int index = m_windowCombo->currentIndex();
    if (index < 0 || index >= m_windows.size()) return QString();
    return m_windows[index].title;
}

QPoint WindowSelector::getSelectedWindowOffset() const
{
    int index = m_windowCombo->currentIndex();
    if (index < 0 || index >= m_windows.size()) return QPoint();
    return QPoint(m_windows[index].x, m_windows[index].y);
}

void WindowSelector::setSelectedWindow(int64_t hwnd, const QString& title)
{
    if (!m_refreshed) {
        refreshWindows();
    }

    for (int i = 0; i < m_windows.size(); ++i) {
        if ((hwnd != 0 && m_windows[i].hwnd == hwnd)
            || (!title.isEmpty() && m_windows[i].title == title)) {
            m_windowCombo->setCurrentIndex(i);
            return;
        }
    }
}

void WindowSelector::onRefreshClicked()
{
    refreshWindows();
}

void WindowSelector::onSelectionChanged(int index)
{
    if (index < 0 || index >= m_windows.size()) return;
    emit windowSelected(m_windows[index].hwnd, m_windows[index].title);
}

void WindowSelector::showEvent(QShowEvent* event)
{
    QWidget::showEvent(event);
    if (!m_refreshed) {
        refreshWindows();
    }
}
