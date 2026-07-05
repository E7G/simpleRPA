#pragma once

#include <QWidget>
#include <QTimer>
#include <QPoint>
#include <QRect>
#include <QStringList>

class PreviewOverlay : public QWidget
{
    Q_OBJECT

public:
    static PreviewOverlay* get_instance(QWidget* parent = nullptr);

    void showPreview(int x, int y, int width, int height, const QString& text);
    void showMousePreview(int x, int y);
    void showImagePreview(const QString& imagePath, int foundX, int foundY);
    void showClickPosition(int x, int y, const QString& label = QString());
    void showDragLine(int startX, int startY, int endX, int endY);
    void showRegion(int x, int y, int width, int height, const QString& label = QString());
    void showScrollPosition(int x, int y, int clicks);
    void showImageMatch(const QString& imagePath, double confidence);
    void showTextPreview(const QString& text, const QString& title = QString());
    void showHotkeyPreview(const QStringList& keys);
    void showActionGroupPreview(const QString& groupName, int actionCount, const QString& description);
    void hidePreview();

    void setAutoHideDuration(int ms);

private:
    explicit PreviewOverlay(QWidget* parent = nullptr);

    void paintEvent(QPaintEvent* event) override;

    enum OverlayType { None, Region, Crosshair, Image, Drag, Scroll, Text, Hotkey, ActionGroup };
    void setupGeometry();
    QPoint physToWidget(int x, int y) const;
    void startPreview();
    void drawLabel(QPainter& painter, const QRect& anchor, const QString& text, const QColor& color);
    void drawInfoCard(QPainter& painter, const QString& title, const QStringList& lines, const QColor& color);

    OverlayType m_type;

    QRect m_rect;
    QString m_text;
    QString m_imagePath;
    QPoint m_crosshairPos;
    QPoint m_imageFoundPos;
    QPoint m_dragStart;
    QPoint m_dragEnd;
    int m_scrollClicks;
    double m_confidence;
    QStringList m_lines;

    QTimer* m_hideTimer;
    int m_autoHideDuration;
};
