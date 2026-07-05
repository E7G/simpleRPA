#ifndef WINDOW_SELECTOR_H
#define WINDOW_SELECTOR_H

#include <QWidget>
#include <QComboBox>
#include <QPushButton>
#include <QHBoxLayout>
#include <cstdint>

class WindowSelector : public QWidget {
    Q_OBJECT

public:
    explicit WindowSelector(QWidget* parent = nullptr);

    void refreshWindows();
    int64_t getSelectedHwnd();
    QString getSelectedTitle();
    void setSelectedWindow(int64_t hwnd, const QString& title);

signals:
    void windowSelected(int64_t hwnd);

private:
    void onRefreshClicked();
    void onSelectionChanged(int index);

    QComboBox* windowCombo;
    QPushButton* refreshBtn;
    QVector<int64_t> hwnds;
};

#endif
