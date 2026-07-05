#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QLabel>
#include <QFrame>
#include <QTimer>

#include "QFluent/Label.h"
#include "QFluent/PushButton.h"
#include "QFluent/LineEdit.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/SpinBox.h"
#include "QFluent/Navigation/Pivot.h"
#include "FluentIcon.h"
#include "fluent_theme.h"

#include "simpleRPA_ffi.h"

class QProcess;

class CommandManagerWidget : public QWidget
{
    Q_OBJECT

public:
    explicit CommandManagerWidget(QWidget* parent = nullptr);
    ~CommandManagerWidget();

private:
    void setupUI();
    void loadCommands();
    void showAddForm();
    void showEditForm(const QJsonObject& command);
    void hideForm();
    void saveCommand();
    void testCommand();
    void runCommand(const QString& commandId);
    void deleteCommand(const QString& commandId);
    void refreshList();

    FfiCommandManager* m_manager;
    QWidget* m_formCard;
    SubtitleLabel* m_formTitle;
    LineEdit* m_nameEdit;
    LineEdit* m_commandEdit;
    LineEdit* m_patternEdit;
    LineEdit* m_descriptionEdit;
    DoubleSpinBox* m_delaySpin;
    PushButton* m_testBtn;
    QTimer* m_testTimer;
    QProcess* m_testProcess;
    double m_testSeconds;
    QString m_editingCommandId;
    QVBoxLayout* m_listLayout;
    QWidget* m_emptyWidget;
    QLabel* m_statusLabel;
};
