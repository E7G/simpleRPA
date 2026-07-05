#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QLabel>
#include <QCheckBox>

#include "simpleRPA_ffi.h"

class CheckBox;
class DoubleSpinBox;
class ListWidget;
class PushButton;
class PrimaryPushButton;
class SpinBox;

class RecorderPanel : public QWidget
{
    Q_OBJECT

public:
    explicit RecorderPanel(QWidget* parent = nullptr);

signals:
    void actionRecorded(const QString& actionJson);
    void recordingStarted();
    void recordingStopped();
    void actionsCleared();

private:
    void setupUI();
    void toggleRecording();
    void clearActions();
    void updateConfig();

    FfiRecorder* m_recorder;
    PrimaryPushButton* m_recordBtn;
    PushButton* m_clearBtn;
    ListWidget* m_actionList;
    QLabel* m_statusLabel;
    QLabel* m_countLabel;
    CheckBox* m_recordClickCb;
    CheckBox* m_recordScrollCb;
    CheckBox* m_recordKeyboardCb;
    CheckBox* m_recordMoveCb;
    CheckBox* m_ignoreLastClickCb;
    SpinBox* m_minDistanceSpin;
    DoubleSpinBox* m_intervalSpin;
    bool m_isRecording;
};
