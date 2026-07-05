#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QPoint>
#include <cstdint>

#include "QFluent/ComboBox.h"
#include "QFluent/Label.h"
#include "QFluent/PushButton.h"
#include "simpleRPA_ffi.h"

class WindowSelector : public QWidget
{
    Q_OBJECT

public:
    explicit WindowSelector(QWidget* parent = nullptr);
    ~WindowSelector();

    int64_t getSelectedHwnd() const;
    QString getSelectedTitle() const;
    QPoint getSelectedWindowOffset() const;
    void setSelectedWindow(int64_t hwnd, const QString& title);
    void refreshWindows();

signals:
    void windowSelected(int64_t hwnd, const QString& title);

protected:
    void showEvent(QShowEvent* event) override;

private:
    void setupUI();
    void onRefreshClicked();
    void onSelectionChanged(int index);

    FfiWindowUtils* m_windowUtils;
    ComboBox* m_windowCombo;
    PushButton* m_refreshBtn;
    CaptionLabel* m_statusLabel;

    struct WindowInfo {
        int64_t hwnd;
        QString title;
        int x;
        int y;
    };
    QVector<WindowInfo> m_windows;
    bool m_refreshed;
};
