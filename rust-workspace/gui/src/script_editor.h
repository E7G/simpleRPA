#pragma once

#include <QWidget>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QStackedWidget>
#include <QFrame>
#include <QMenu>
#include <QAction>
#include <QKeyEvent>
#include <QJsonArray>
#include <QPushButton>
#include <QTimer>
#include <QVector>

#include "QFluent/Label.h"
#include "QFluent/LineEdit.h"
#include "QFluent/PushButton.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/Navigation/Pivot.h"
#include "QFluent/TabBar.h"
#include "FluentIcon.h"
#include "fluent_theme.h"

#include "simpleRPA_ffi.h"
#include "action_list_row.h"

class ListWidget;

class ScriptEditor : public QWidget
{
    Q_OBJECT

public:
    explicit ScriptEditor(QWidget* parent = nullptr);
    ~ScriptEditor() override;

    QString getCurrentActionsJson() const;
    QString getLocalActionGroupsJson() const;
    void setLocalActionGroupsJson(const QString& json);
    QString currentTabName() const;
    void setCurrentTabName(const QString& name);
    void addAction(const QString& actionJson);
    void removeAction(int index);
    void clearActions();
    void setActions(const QString& json);
    void updateAction(int index, const QString& actionJson);
    int selectedActionIndex() const;
    int actionCount() const;
    void setActionRunning(int index);
    void clearAllRunning();

signals:
    void actionSelected(const QString& actionJson, int index);
    void executeSingle(int index);
    void actionsChanged();
    void tabChanged(const QString& name, int index);

private:
    struct ScriptTabState {
        QString routeKey;
        QString title;
        QList<QString> actions;
        QList<QString> clipboard;
        QString localGroupsJson = "{}";
    };

    void keyPressEvent(QKeyEvent* event) override;

    void setupUI();
    void addNewTab(const QString& name = QString());
    void closeTab(int index);
    void switchToTab(int index);
    void saveCurrentTabState();
    void loadTabState(int index);
    void notifyActionsChanged();
    void refreshGroupList();
    void addGroupCard(const QJsonObject& group);
    QJsonObject localActionGroupByName(const QString& name) const;
    void editActionGroup(const QString& name);
    void deleteActionGroup(const QString& name);
    void startPreview();
    void togglePausePreview();
    void stopPreview();
    void previewNextAction();
    void highlightAction(int index);
    void clearHighlights();
    void showActionPreview(int index);
    void refreshList();
    void onItemClicked(int row);
    void onItemDoubleClicked(int row);
    void deleteAction(int index);
    QList<int> selectedRows() const;
    void selectRows(const QList<int>& rows, int currentRow = -1);
    void copySelectedActions();
    void pasteActionsAfterCurrent();
    void duplicateSelectedActions();
    void moveSelectedUp();
    void moveSelectedDown();
    void deleteSelectedActions();
    QJsonArray localActionGroupsArray() const;
    QJsonArray availableActionGroupsArray() const;
    QString selectedActionsJson(const QList<int>& rows) const;
    bool currentActionIsGroupRef(int row, QString* groupName = nullptr) const;
    void saveSelectedAsActionGroup();
    void insertActionGroupRef(const QString& name, int index);
    void expandActionGroupRef(int index);
    void clearAllWithConfirm();

    TabBar* m_tabBar;
    Pivot* m_viewPivot;
    QStackedWidget* m_viewStack;
    QWidget* m_actionPage;
    QWidget* m_groupPage;
    QVBoxLayout* m_groupsLayout;
    QLabel* m_emptyGroupsLabel;
    PrimaryPushButton* m_previewBtn;
    PushButton* m_pausePreviewBtn;
    PushButton* m_stopPreviewBtn;
    ListWidget* m_actionList;
    QLabel* m_statusLabel;
    QList<QString> m_actions;
    QList<QString> m_clipboard;
    FfiActionGroupManager* m_groupManager;
    QVector<ScriptTabState> m_tabs;
    int m_currentTabIndex;
    int m_tabCounter;
    int m_previewIndex;
    bool m_previewPaused;
    bool m_ignoreTabSignals;
    QTimer* m_previewTimer;
};
