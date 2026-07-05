#include "preview_overlay.h"

#include <QPainter>
#include <QPainterPath>
#include <QScreen>
#include <QGuiApplication>
#include <QApplication>
#include <QFontMetrics>
#include <QFileInfo>
#include <QPixmap>
#include <algorithm>
#include <cmath>

PreviewOverlay* PreviewOverlay::get_instance(QWidget* parent)
{
    static PreviewOverlay* instance = nullptr;
    if (!instance) {
        instance = new PreviewOverlay(parent);
    }
    return instance;
}

PreviewOverlay::PreviewOverlay(QWidget* parent)
    : QWidget(parent)
    , m_type(None)
    , m_scrollClicks(0)
    , m_confidence(0.0)
    , m_autoHideDuration(2000)
{
    setWindowFlags(Qt::FramelessWindowHint
                   | Qt::WindowStaysOnTopHint
                   | Qt::Tool
                   | Qt::WindowTransparentForInput);
    setAttribute(Qt::WA_TranslucentBackground);
    setAttribute(Qt::WA_ShowWithoutActivating);

    m_hideTimer = new QTimer(this);
    m_hideTimer->setSingleShot(true);
    connect(m_hideTimer, &QTimer::timeout, this, &PreviewOverlay::hidePreview);
    setupGeometry();
}

void PreviewOverlay::showPreview(int x, int y, int width, int height, const QString& text)
{
    showRegion(x, y, width, height, text);
}

void PreviewOverlay::showMousePreview(int x, int y)
{
    showClickPosition(x, y, QString());
}

void PreviewOverlay::showImagePreview(const QString& imagePath, int foundX, int foundY)
{
    m_type = Image;
    m_imagePath = imagePath;
    m_imageFoundPos = physToWidget(foundX, foundY);
    m_confidence = 0.0;
    m_lines.clear();
    startPreview();
}

void PreviewOverlay::showClickPosition(int x, int y, const QString& label)
{
    m_type = Crosshair;
    m_crosshairPos = physToWidget(x, y);
    m_text = label;
    startPreview();
}

void PreviewOverlay::showDragLine(int startX, int startY, int endX, int endY)
{
    m_type = Drag;
    m_dragStart = physToWidget(startX, startY);
    m_dragEnd = physToWidget(endX, endY);
    m_text = "Drag";
    startPreview();
}

void PreviewOverlay::showRegion(int x, int y, int width, int height, const QString& label)
{
    m_type = Region;
    const QPoint topLeft = physToWidget(x, y);
    const QPoint bottomRight = physToWidget(x + width, y + height);
    m_rect = QRect(topLeft, bottomRight).normalized();
    if (m_rect.width() < 8) {
        m_rect.setWidth(8);
    }
    if (m_rect.height() < 8) {
        m_rect.setHeight(8);
    }
    m_text = label;
    startPreview();
}

void PreviewOverlay::showScrollPosition(int x, int y, int clicks)
{
    m_type = Scroll;
    m_crosshairPos = physToWidget(x, y);
    m_scrollClicks = clicks;
    startPreview();
}

void PreviewOverlay::showImageMatch(const QString& imagePath, double confidence)
{
    m_type = Image;
    m_imagePath = imagePath;
    m_imageFoundPos = QPoint();
    m_confidence = confidence;
    m_lines.clear();
    startPreview();
}

void PreviewOverlay::showTextPreview(const QString& text, const QString& title)
{
    m_type = Text;
    m_text = title.isEmpty() ? "Text" : title;
    m_lines = QStringList{text};
    startPreview();
}

void PreviewOverlay::showHotkeyPreview(const QStringList& keys)
{
    m_type = Hotkey;
    m_text = "Hotkey";
    m_lines = QStringList{keys.join(" + ")};
    startPreview();
}

void PreviewOverlay::showActionGroupPreview(const QString& groupName, int actionCount, const QString& description)
{
    m_type = ActionGroup;
    m_text = groupName;
    m_lines = QStringList{QString("%1 actions").arg(actionCount)};
    if (!description.isEmpty()) {
        m_lines << description;
    }
    startPreview();
}

void PreviewOverlay::hidePreview()
{
    m_type = None;
    m_hideTimer->stop();
    hide();
}

void PreviewOverlay::setAutoHideDuration(int ms)
{
    m_autoHideDuration = ms;
}

void PreviewOverlay::setupGeometry()
{
    const QList<QScreen*> screens = QGuiApplication::screens();
    if (screens.isEmpty()) {
        return;
    }

    QRect virtualGeometry = screens.first()->geometry();
    for (QScreen* screen : screens) {
        virtualGeometry = virtualGeometry.united(screen->geometry());
    }
    setGeometry(virtualGeometry);
}

QPoint PreviewOverlay::physToWidget(int x, int y) const
{
    double dpr = 1.0;
    if (QScreen* screen = QGuiApplication::primaryScreen()) {
        dpr = screen->devicePixelRatio();
        if (dpr <= 0.0) {
            dpr = 1.0;
        }
    }

    const QRect geo = geometry();
    return QPoint(static_cast<int>(std::round(x / dpr)) - geo.x(),
                  static_cast<int>(std::round(y / dpr)) - geo.y());
}

void PreviewOverlay::startPreview()
{
    setupGeometry();
    show();
    raise();
    update();
    m_hideTimer->start(m_autoHideDuration);
}

void PreviewOverlay::drawLabel(QPainter& painter, const QRect& anchor, const QString& text, const QColor& color)
{
    if (text.isEmpty()) {
        return;
    }

    QFont font("Segoe UI", 10);
    painter.setFont(font);
    QFontMetrics fm(font);
    const int textWidth = std::min(fm.horizontalAdvance(text) + 16, std::max(120, width() - 24));
    const int textHeight = fm.height() + 8;
    QRect labelRect(anchor.x(), anchor.y() - textHeight - 6, textWidth, textHeight);
    if (labelRect.top() < 8) {
        labelRect.moveTop(anchor.bottom() + 6);
    }
    if (labelRect.right() > width() - 8) {
        labelRect.moveRight(width() - 8);
    }
    if (labelRect.left() < 8) {
        labelRect.moveLeft(8);
    }

    painter.setPen(Qt::NoPen);
    painter.setBrush(color);
    painter.drawRoundedRect(labelRect, 4, 4);
    painter.setPen(Qt::white);
    painter.drawText(labelRect.adjusted(8, 0, -8, 0), Qt::AlignVCenter | Qt::TextSingleLine, text);
}

void PreviewOverlay::drawInfoCard(QPainter& painter, const QString& title, const QStringList& lines, const QColor& color)
{
    QFont titleFont("Segoe UI", 12, QFont::DemiBold);
    QFont bodyFont("Segoe UI", 10);
    QFontMetrics titleFm(titleFont);
    QFontMetrics bodyFm(bodyFont);

    int contentWidth = titleFm.horizontalAdvance(title);
    for (const QString& line : lines) {
        contentWidth = std::max(contentWidth, bodyFm.horizontalAdvance(line));
    }
    const int cardWidth = std::clamp(contentWidth + 44, 260, std::max(260, width() - 48));
    const int lineCount = std::max(1, static_cast<int>(lines.size()));
    const int cardHeight = 48 + titleFm.height() + lineCount * (bodyFm.height() + 4);
    QRect card((width() - cardWidth) / 2, (height() - cardHeight) / 2, cardWidth, cardHeight);

    painter.setPen(Qt::NoPen);
    painter.setBrush(QColor(0, 0, 0, 90));
    painter.drawRect(rect());

    painter.setBrush(QColor(255, 255, 255, 242));
    painter.drawRoundedRect(card, 8, 8);
    painter.setBrush(color);
    painter.drawRoundedRect(QRect(card.left(), card.top(), 6, card.height()), 3, 3);

    QRect titleRect = card.adjusted(22, 14, -18, -card.height() + 38);
    painter.setFont(titleFont);
    painter.setPen(QColor(24, 24, 24));
    painter.drawText(titleRect, Qt::AlignVCenter | Qt::TextSingleLine, title);

    painter.setFont(bodyFont);
    painter.setPen(QColor(78, 78, 78));
    int y = titleRect.bottom() + 10;
    for (const QString& line : lines) {
        QRect lineRect(card.left() + 22, y, card.width() - 40, bodyFm.height() + 2);
        painter.drawText(lineRect, Qt::AlignVCenter | Qt::TextSingleLine, line);
        y += bodyFm.height() + 4;
    }
}

void PreviewOverlay::paintEvent(QPaintEvent*)
{
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);

    switch (m_type) {
    case Region: {
        painter.setPen(Qt::NoPen);
        painter.setBrush(QColor(0, 0, 0, 80));
        painter.drawRect(rect());

        painter.setPen(QPen(QColor(0, 120, 212), 2));
        painter.setBrush(QColor(0, 120, 212, 35));
        painter.drawRoundedRect(m_rect, 4, 4);
        drawLabel(painter, m_rect, m_text, QColor(0, 120, 212));
        break;
    }
    case Crosshair: {
        int armLen = 16;
        painter.setPen(QPen(QColor(255, 50, 50, 200), 2));
        painter.drawLine(m_crosshairPos.x() - armLen, m_crosshairPos.y(),
                         m_crosshairPos.x() + armLen, m_crosshairPos.y());
        painter.drawLine(m_crosshairPos.x(), m_crosshairPos.y() - armLen,
                         m_crosshairPos.x(), m_crosshairPos.y() + armLen);

        painter.setPen(Qt::NoPen);
        painter.setBrush(QColor(255, 50, 50, 60));
        painter.drawEllipse(m_crosshairPos, 6, 6);

        QFont font("Segoe UI", 10);
        painter.setFont(font);
        QString coordText = m_text.isEmpty()
            ? QString("(%1, %2)").arg(m_crosshairPos.x()).arg(m_crosshairPos.y())
            : m_text;
        QFontMetrics fm(font);
        int tw = fm.horizontalAdvance(coordText) + 12;
        int th = fm.height() + 6;
        QRect coordRect(m_crosshairPos.x() + 12, m_crosshairPos.y() + 12, tw, th);
        painter.setPen(Qt::NoPen);
        painter.setBrush(QColor(30, 30, 30, 200));
        painter.drawRoundedRect(coordRect, 3, 3);
        painter.setPen(Qt::white);
        painter.drawText(coordRect, Qt::AlignCenter, coordText);
        break;
    }
    case Image: {
        if (!m_imageFoundPos.isNull()) {
            int boxSize = 40;
            QRect boxRect(m_imageFoundPos.x() - boxSize / 2, m_imageFoundPos.y() - boxSize / 2,
                          boxSize, boxSize);
            painter.setPen(QPen(QColor(0, 160, 80), 3));
            painter.setBrush(QColor(0, 160, 80, 30));
            painter.drawRect(boxRect);
            drawLabel(painter, boxRect,
                      QString("(%1, %2)").arg(m_imageFoundPos.x()).arg(m_imageFoundPos.y()),
                      QColor(0, 160, 80));
        } else {
            QStringList lines;
            lines << QFileInfo(m_imagePath).fileName();
            if (m_confidence > 0.0) {
                lines << QString("confidence %1%").arg(static_cast<int>(m_confidence * 100));
            }
            drawInfoCard(painter, "Image match", lines, QColor(0, 160, 80));
        }
        break;
    }
    case Drag: {
        painter.setPen(Qt::NoPen);
        painter.setBrush(QColor(0, 0, 0, 70));
        painter.drawRect(rect());
        painter.setPen(QPen(QColor(0, 120, 212), 3, Qt::SolidLine, Qt::RoundCap));
        painter.drawLine(m_dragStart, m_dragEnd);
        painter.setBrush(QColor(0, 120, 212, 50));
        painter.drawEllipse(m_dragStart, 7, 7);
        painter.drawEllipse(m_dragEnd, 7, 7);
        QRect anchor(m_dragStart, m_dragEnd);
        drawLabel(painter, anchor.normalized(), "Drag", QColor(0, 120, 212));
        break;
    }
    case Scroll: {
        const int direction = m_scrollClicks >= 0 ? -1 : 1;
        const int length = 42;
        QPoint arrowEnd(m_crosshairPos.x(), m_crosshairPos.y() + direction * length);
        painter.setPen(QPen(QColor(196, 90, 17), 3, Qt::SolidLine, Qt::RoundCap));
        painter.drawLine(m_crosshairPos, arrowEnd);
        QPolygon arrow;
        arrow << arrowEnd
              << QPoint(arrowEnd.x() - 7, arrowEnd.y() - direction * 10)
              << QPoint(arrowEnd.x() + 7, arrowEnd.y() - direction * 10);
        painter.setBrush(QColor(196, 90, 17));
        painter.drawPolygon(arrow);
        drawLabel(painter, QRect(m_crosshairPos.x() - 20, m_crosshairPos.y() - 20, 40, 40),
                  QString("Scroll %1").arg(m_scrollClicks), QColor(196, 90, 17));
        break;
    }
    case Text:
        drawInfoCard(painter, m_text, m_lines, QColor(0, 120, 212));
        break;
    case Hotkey:
        drawInfoCard(painter, m_text, m_lines, QColor(120, 70, 180));
        break;
    case ActionGroup:
        drawInfoCard(painter, QString("Action group: %1").arg(m_text), m_lines, QColor(0, 153, 188));
        break;
    case None:
        break;
    }
}
