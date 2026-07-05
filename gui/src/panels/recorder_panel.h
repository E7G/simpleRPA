#ifndef RECORDER_PANEL_H
#define RECORDER_PANEL_H

#include <QWidget>
#include <QPushButton>
#include <QVBoxLayout>
#include <QLabel>

class RecorderPanel : public QWidget {
    Q_OBJECT

public:
    explicit RecorderPanel(QWidget* parent = nullptr);

signals:
    void recordingStarted();
    void recordingStopped();

private:
    void onStartRecording();
    void onStopRecording();

    QPushButton* startBtn;
    QPushButton* stopBtn;
    QLabel* statusLabel;
    bool recording = false;
};

#endif
