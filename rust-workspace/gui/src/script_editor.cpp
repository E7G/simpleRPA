#include "script_editor.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QMenu>
#include <QAction>
#include <QDialog>
#include <QDialogButtonBox>
#include <QFormLayout>
#include <QGuiApplication>
#include <QInputDialog>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QShortcut>
#include <QSizePolicy>
#include <QScreen>
#include <QSet>
#include <algorithm>

#include "QFluent/Label.h"
#include "QFluent/LineEdit.h"
#include "QFluent/ScrollArea.h"
#include "QFluent/CardWidget.h"
#include "QFluent/IconWidget.h"
#include "QFluent/ListView.h"
#include "QFluent/PushButton.h"
#include "QFluent/ToolButton.h"
#include "Theme.h"
#include "fluent_theme.h"
#include "preview_overlay.h"

using FIT = Fluent::IconType;

ScriptEditor::ScriptEditor(QWidget* parent)
    : QWidget(parent)
    , m_tabBar(nullptr)
    , m_viewPivot(nullptr)
    , m_viewStack(nullptr)
    , m_actionPage(nullptr)
    , m_groupPage(nullptr)
    , m_groupsLayout(nullptr)
    , m_emptyGroupsLabel(nullptr)
    , m_previewBtn(nullptr)
    , m_pausePreviewBtn(nullptr)
    , m_stopPreviewBtn(nullptr)
    , m_groupManager(action_group_manager_new())
    , m_currentTabIndex(-1)
    , m_tabCounter(0)
    , m_previewIndex(-1)
    , m_previewPaused(false)
    , m_ignoreTabSignals(false)
    , m_previewTimer(new QTimer(this))
{
    setupUI();
}

ScriptEditor::~ScriptEditor()
{
    if (m_groupManager) {
        action_group_manager_free(m_groupManager);
        m_groupManager = nullptr;
    }
}

void ScriptEditor::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(8);

    // ===== Header (matching Python: header_layout with action count) =====
    auto* headerLayout = new QHBoxLayout();
    m_statusLabel = new BodyLabel("0 个步骤");
    headerLayout->addWidget(m_statusLabel);
    headerLayout->addStretch();
    m_previewBtn = new PrimaryPushButton(QStringLiteral("\u9884\u89c8\u5168\u90e8"), FIT::VIEW);
    m_previewBtn->setFixedHeight(30);
    connect(m_previewBtn, &QPushButton::clicked, this, &ScriptEditor::startPreview);
    headerLayout->addWidget(m_previewBtn);
    m_pausePreviewBtn = new PushButton(QStringLiteral("\u6682\u505c"), FIT::PAUSE);
    m_pausePreviewBtn->setFixedHeight(30);
    m_pausePreviewBtn->setVisible(false);
    connect(m_pausePreviewBtn, &QPushButton::clicked, this, &ScriptEditor::togglePausePreview);
    headerLayout->addWidget(m_pausePreviewBtn);
    m_stopPreviewBtn = new PushButton(QStringLiteral("\u505c\u6b62\u9884\u89c8"), FIT::CANCEL);
    m_stopPreviewBtn->setFixedHeight(30);
    m_stopPreviewBtn->setVisible(false);
    connect(m_stopPreviewBtn, &QPushButton::clicked, this, &ScriptEditor::stopPreview);
    headerLayout->addWidget(m_stopPreviewBtn);
    layout->addLayout(headerLayout);

    m_previewTimer->setInterval(2500);
    connect(m_previewTimer, &QTimer::timeout, this, &ScriptEditor::previewNextAction);

    m_tabBar = new TabBar(this);
    m_tabBar->setTabsClosable(true);
    m_tabBar->setCloseButtonDisplayMode(TabCloseButtonDisplayMode::OnHover);
    m_tabBar->setMovable(false);
    m_tabBar->setAddButtonVisible(true);
    m_tabBar->setTabShadowEnabled(false);
    m_tabBar->setFixedHeight(40);
    connect(m_tabBar, &TabBar::tabAddRequested, this, [this]() { addNewTab(); });
    connect(m_tabBar, &TabBar::tabCloseRequested, this, &ScriptEditor::closeTab);
    connect(m_tabBar, &TabBar::currentChanged, this, &ScriptEditor::switchToTab);
    layout->addWidget(m_tabBar);

    m_viewPivot = new Pivot(this);
    m_viewPivot->addItem("actions", "动作列表");
    m_viewPivot->addItem("groups", "动作组");
    connect(m_viewPivot, &Pivot::currentItemChanged, this, [this](const QString& key) {
        if (m_viewStack) {
            m_viewStack->setCurrentIndex(key == "groups" ? 1 : 0);
        }
        if (key == "groups") {
            refreshGroupList();
        }
    });
    layout->addWidget(m_viewPivot);

    m_viewStack = new QStackedWidget(this);
    layout->addWidget(m_viewStack, 1);

    // ===== Action list =====
    m_actionPage = new QWidget(this);
    auto* actionPageLayout = new QVBoxLayout(m_actionPage);
    actionPageLayout->setContentsMargins(0, 0, 0, 0);
    actionPageLayout->setSpacing(0);

    auto* scrollArea = new ScrollArea();
    scrollArea->setWidgetResizable(true);
    scrollArea->setFrameShape(QFrame::NoFrame);
    scrollArea->setStyleSheet("QScrollArea { border: none; background: transparent; }");

    auto* scrollContent = new QWidget();
    m_actionList = new ListWidget();
    m_actionList->setStyleSheet(FluentTheme::flowListStyle());
    m_actionList->setSelectionMode(QAbstractItemView::ExtendedSelection);
    m_actionList->setContextMenuPolicy(Qt::CustomContextMenu);

    auto addShortcut = [this](const QKeySequence& key, auto slot) {
        auto* shortcut = new QShortcut(key, this);
        shortcut->setContext(Qt::WidgetWithChildrenShortcut);
        connect(shortcut, &QShortcut::activated, this, slot);
    };
    addShortcut(QKeySequence::Copy, [this]() { copySelectedActions(); });
    addShortcut(QKeySequence::Paste, [this]() { pasteActionsAfterCurrent(); });
    addShortcut(QKeySequence(Qt::Key_Delete), [this]() { deleteSelectedActions(); });
    addShortcut(QKeySequence(Qt::CTRL | Qt::Key_Up), [this]() { moveSelectedUp(); });
    addShortcut(QKeySequence(Qt::CTRL | Qt::Key_Down), [this]() { moveSelectedDown(); });
    addShortcut(QKeySequence(Qt::CTRL | Qt::Key_T), [this]() { addNewTab(); });
    addShortcut(QKeySequence(Qt::CTRL | Qt::Key_W), [this]() { closeTab(m_currentTabIndex); });

    connect(m_actionList, &QListWidget::customContextMenuRequested, this, [this](const QPoint& pos) {
        QListWidgetItem* item = m_actionList->itemAt(pos);
        if (item && !item->isSelected()) {
            m_actionList->clearSelection();
            item->setSelected(true);
            m_actionList->setCurrentItem(item);
        }

        QMenu menu(this);
        const QList<int> rows = selectedRows();
        const bool hasSelection = !rows.isEmpty();
        const int insertAfter = item ? m_actionList->row(item) : m_actions.size() - 1;
        QString groupName;
        const bool isGroupRef = item && currentActionIsGroupRef(m_actionList->row(item), &groupName);

        auto* copyAction = menu.addAction("复制", [this]() { copySelectedActions(); });
        copyAction->setEnabled(hasSelection);
        auto* pasteAction = menu.addAction("粘贴", [this]() { pasteActionsAfterCurrent(); });
        pasteAction->setEnabled(!m_clipboard.isEmpty());
        auto* duplicateAction = menu.addAction("复制并粘贴", [this]() { duplicateSelectedActions(); });
        duplicateAction->setEnabled(hasSelection);
        auto* saveGroupAction = menu.addAction("保存为动作组...", [this]() { saveSelectedAsActionGroup(); });
        saveGroupAction->setEnabled(hasSelection);
        menu.addSeparator();
        auto* deleteMenuAction = menu.addAction("删除", [this]() { deleteSelectedActions(); });
        deleteMenuAction->setEnabled(hasSelection);
        auto* moveUpAction = menu.addAction("上移", [this]() { moveSelectedUp(); });
        moveUpAction->setEnabled(hasSelection && rows.first() > 0);
        auto* moveDownAction = menu.addAction("下移", [this]() { moveSelectedDown(); });
        moveDownAction->setEnabled(hasSelection && rows.last() < m_actions.size() - 1);
        auto* clearAction = menu.addAction("清空全部", [this]() { clearAllWithConfirm(); });
        clearAction->setEnabled(!m_actions.isEmpty());
        menu.addSeparator();

        QMenu* groupMenu = menu.addMenu("插入动作组");
        const QJsonArray groups = availableActionGroupsArray();
        groupMenu->setEnabled(!groups.isEmpty());
        for (const QJsonValue& groupValue : groups) {
            const QJsonObject group = groupValue.toObject();
            const QString name = group["name"].toString();
            if (!name.isEmpty()) {
                groupMenu->addAction(name, [this, name, insertAfter]() {
                    insertActionGroupRef(name, insertAfter);
                });
            }
        }
        auto* expandGroupAction = menu.addAction(
            groupName.isEmpty() ? "解压动作组引用" : QString("解压动作组引用: %1").arg(groupName),
            [this]() { expandActionGroupRef(m_actionList->currentRow()); });
        expandGroupAction->setEnabled(isGroupRef);
        menu.addSeparator();
        auto* debugAction = menu.addAction("调试此动作", [this]() {
            int row = m_actionList->currentRow();
            if (row >= 0) {
                emit executeSingle(row);
            }
        });
        debugAction->setEnabled(m_actionList->currentRow() >= 0);
        menu.exec(QCursor::pos());
    });

    connect(m_actionList, &QListWidget::currentRowChanged, this, &ScriptEditor::onItemClicked);
    connect(m_actionList, &QListWidget::itemDoubleClicked, this, [this](QListWidgetItem* item) {
        Q_UNUSED(item);
        int row = m_actionList->currentRow();
        if (row >= 0) onItemDoubleClicked(row);
    });

    auto* scrollLayout = new QVBoxLayout(scrollContent);
    scrollLayout->setContentsMargins(0, 0, 0, 0);
    scrollLayout->setSpacing(0);
    scrollLayout->addWidget(m_actionList);

    scrollArea->setWidget(scrollContent);
    actionPageLayout->addWidget(scrollArea, 1);
    m_viewStack->addWidget(m_actionPage);

    // ===== Action groups page (matching Python: Pivot groups view) =====
    m_groupPage = new QWidget(this);
    auto* groupPageLayout = new QVBoxLayout(m_groupPage);
    groupPageLayout->setContentsMargins(0, 0, 0, 0);
    groupPageLayout->setSpacing(0);

    auto* groupsScrollArea = new ScrollArea();
    groupsScrollArea->setWidgetResizable(true);
    groupsScrollArea->setFrameShape(QFrame::NoFrame);
    groupsScrollArea->setStyleSheet("QScrollArea { border: none; background: transparent; }");

    auto* groupsContent = new QWidget();
    groupsContent->setStyleSheet("background: transparent;");
    m_groupsLayout = new QVBoxLayout(groupsContent);
    m_groupsLayout->setContentsMargins(0, 0, 0, 0);
    m_groupsLayout->setSpacing(10);
    m_groupsLayout->setAlignment(Qt::AlignTop);

    m_emptyGroupsLabel = new BodyLabel("暂无保存的动作组\n\n在脚本列表中右键选择动作，\n点击\"保存为动作组...\"即可创建");
    m_emptyGroupsLabel->setAlignment(Qt::AlignCenter);
    m_emptyGroupsLabel->setWordWrap(true);
    m_emptyGroupsLabel->setMinimumHeight(180);
    m_emptyGroupsLabel->setStyleSheet("color: #666; background: transparent;");
    m_groupsLayout->addWidget(m_emptyGroupsLabel);

    groupsScrollArea->setWidget(groupsContent);
    groupPageLayout->addWidget(groupsScrollArea, 1);
    m_viewStack->addWidget(m_groupPage);

    m_viewPivot->setCurrentItem("actions");
    m_viewStack->setCurrentIndex(0);

    addNewTab();
}

void ScriptEditor::addNewTab(const QString& name)
{
    saveCurrentTabState();

    ++m_tabCounter;
    ScriptTabState state;
    state.routeKey = QString("tab_%1").arg(m_tabCounter);
    state.title = name.isEmpty() ? QString("任务 %1").arg(m_tabCounter) : name;
    m_tabs.append(state);
    const int newIndex = static_cast<int>(m_tabs.size()) - 1;

    m_ignoreTabSignals = true;
    m_tabBar->addTab(state.routeKey, state.title);
    m_tabBar->setCurrentIndex(newIndex);
    m_ignoreTabSignals = false;

    loadTabState(newIndex);
}

void ScriptEditor::closeTab(int index)
{
    if (m_tabs.size() <= 1 || index < 0 || index >= m_tabs.size()) {
        return;
    }

    saveCurrentTabState();
    if (!m_tabs[index].actions.isEmpty()) {
        const QString title = m_tabs[index].title;
        if (QMessageBox::question(
                this,
                "关闭标签",
                QString("关闭 \"%1\"？未保存的动作不会自动写入文件。").arg(title))
            != QMessageBox::Yes) {
            return;
        }
    }

    const bool closingCurrent = index == m_currentTabIndex;
    m_tabs.removeAt(index);

    m_ignoreTabSignals = true;
    m_tabBar->removeTab(index);
    const int nextIndex = closingCurrent
        ? std::min(index, static_cast<int>(m_tabs.size()) - 1)
        : (m_currentTabIndex > index ? m_currentTabIndex - 1 : m_currentTabIndex);
    m_tabBar->setCurrentIndex(nextIndex);
    m_ignoreTabSignals = false;

    loadTabState(nextIndex);
}

void ScriptEditor::switchToTab(int index)
{
    if (m_ignoreTabSignals || index < 0 || index >= m_tabs.size() || index == m_currentTabIndex) {
        return;
    }

    stopPreview();
    saveCurrentTabState();
    loadTabState(index);
}

void ScriptEditor::saveCurrentTabState()
{
    if (m_currentTabIndex < 0 || m_currentTabIndex >= m_tabs.size()) {
        return;
    }

    ScriptTabState& state = m_tabs[m_currentTabIndex];
    state.actions = m_actions;
    state.clipboard = m_clipboard;
    state.localGroupsJson = getLocalActionGroupsJson();
}

void ScriptEditor::loadTabState(int index)
{
    if (index < 0 || index >= m_tabs.size()) {
        return;
    }

    m_currentTabIndex = index;
    const ScriptTabState& state = m_tabs[index];
    m_actions = state.actions;
    m_clipboard = state.clipboard;
    setLocalActionGroupsJson(state.localGroupsJson);
    refreshList();
    refreshGroupList();

    if (m_tabBar && m_tabBar->currentIndex() != index) {
        m_ignoreTabSignals = true;
        m_tabBar->setCurrentIndex(index);
        m_ignoreTabSignals = false;
    }

    emit tabChanged(state.title, index);
    if (!m_actions.isEmpty()) {
        m_actionList->setCurrentRow(0);
    }
}

void ScriptEditor::notifyActionsChanged()
{
    if (m_previewTimer && m_previewTimer->isActive()) {
        stopPreview();
    }
    saveCurrentTabState();
    if (m_viewPivot && m_viewPivot->currentRouteKey() == "groups") {
        refreshGroupList();
    }
    emit actionsChanged();
}

void ScriptEditor::refreshGroupList()
{
    if (!m_groupsLayout) {
        return;
    }

    while (m_groupsLayout->count() > 0) {
        QLayoutItem* item = m_groupsLayout->takeAt(0);
        if (QWidget* widget = item->widget()) {
            if (widget != m_emptyGroupsLabel) {
                widget->deleteLater();
            }
        }
        delete item;
    }

    const QJsonArray groups = availableActionGroupsArray();
    if (groups.isEmpty()) {
        m_groupsLayout->addWidget(m_emptyGroupsLabel);
        m_emptyGroupsLabel->show();
        m_groupsLayout->addStretch();
        return;
    }

    m_emptyGroupsLabel->hide();
    for (const QJsonValue& value : groups) {
        const QJsonObject group = value.toObject();
        if (!group["name"].toString().isEmpty()) {
            addGroupCard(group);
        }
    }
    m_groupsLayout->addStretch();
}

void ScriptEditor::addGroupCard(const QJsonObject& group)
{
    const QString name = group["name"].toString();
    const QString description = group["description"].toString();
    const QJsonArray actions = group["actions"].toArray();
    const int actionCount = static_cast<int>(actions.size());
    const bool isLocal = group.value("is_local").toBool(true);

    auto* card = new SimpleCardWidget();
    card->setBorderRadius(6);
    card->setClickEnabled(false);

    auto* layout = new QVBoxLayout(card);
    layout->setContentsMargins(14, 12, 14, 12);
    layout->setSpacing(8);

    auto* header = new QHBoxLayout();
    header->setSpacing(8);
    auto* groupIcon = new IconWidget(FIT::LIBRARY, card);
    groupIcon->setFixedSize(20, 20);
    header->addWidget(groupIcon);
    auto* nameLabel = new StrongBodyLabel(name);
    header->addWidget(nameLabel, 1);

    auto* countLabel = new BodyLabel(QString("%1 个动作").arg(actionCount));
    countLabel->setStyleSheet("color: #666; background: transparent;");
    header->addWidget(countLabel);
    auto* sourceLabel = new BodyLabel(isLocal ? "本地" : "全局");
    sourceLabel->setStyleSheet("color: #666; background: transparent;");
    header->addWidget(sourceLabel);

    auto* insertBtn = new PrimaryPushButton("插入", FIT::ADD_TO);
    insertBtn->setFixedHeight(28);
    connect(insertBtn, &QPushButton::clicked, this, [this, name]() {
        insertActionGroupRef(name, m_actionList ? m_actionList->currentRow() : m_actions.size() - 1);
        if (m_viewPivot) {
            m_viewPivot->setCurrentItem("actions");
        }
    });
    header->addWidget(insertBtn);

    auto* editBtn = new TransparentToolButton(FIT::EDIT);
    editBtn->setFixedSize(28, 28);
    editBtn->setToolTip("编辑");
    connect(editBtn, &QToolButton::clicked, this, [this, name]() { editActionGroup(name); });
    header->addWidget(editBtn);

    auto* deleteBtn = new TransparentToolButton(FIT::DELETE);
    deleteBtn->setFixedSize(28, 28);
    deleteBtn->setToolTip("删除");
    connect(deleteBtn, &QToolButton::clicked, this, [this, name]() { deleteActionGroup(name); });
    header->addWidget(deleteBtn);

    layout->addLayout(header);

    if (!description.isEmpty()) {
        auto* descLabel = new BodyLabel(description);
        descLabel->setWordWrap(true);
        descLabel->setStyleSheet("color: #555; background: transparent;");
        layout->addWidget(descLabel);
    }

    const int previewCount = std::min(3, actionCount);
    for (int i = 0; i < previewCount; ++i) {
        const QJsonObject action = actions.at(i).toObject();
        QString desc = action["description"].toString();
        if (desc.isEmpty()) {
            desc = action["action_type"].toString();
        }
        auto* actionLabel = new BodyLabel(QString("%1. %2").arg(i + 1).arg(desc));
        actionLabel->setWordWrap(true);
        actionLabel->setStyleSheet("color: #666; background: transparent; padding-left: 8px;");
        layout->addWidget(actionLabel);
    }
    if (actionCount > previewCount) {
        auto* moreLabel = new BodyLabel(QString("还有 %1 个动作...").arg(actionCount - previewCount));
        moreLabel->setStyleSheet("color: #888; background: transparent; padding-left: 8px;");
        layout->addWidget(moreLabel);
    }

    m_groupsLayout->addWidget(card);
}

QJsonObject ScriptEditor::localActionGroupByName(const QString& name) const
{
    for (const QJsonValue& value : availableActionGroupsArray()) {
        const QJsonObject group = value.toObject();
        if (group["name"].toString() == name) {
            return group;
        }
    }
    return {};
}

void ScriptEditor::editActionGroup(const QString& name)
{
    QJsonObject group = localActionGroupByName(name);
    if (group.isEmpty()) {
        QMessageBox::warning(this, "编辑失败", QString("动作组 \"%1\" 不存在").arg(name));
        return;
    }
    const bool isLocalGroup = group.value("is_local").toBool(true);

    QDialog dialog(this);
    dialog.setWindowTitle(QString("编辑动作组: %1").arg(name));
    dialog.resize(760, 560);

    auto* root = new QVBoxLayout(&dialog);
    root->setContentsMargins(16, 16, 16, 16);
    root->setSpacing(10);

    auto* form = new QFormLayout();
    auto* nameEdit = new LineEdit();
    nameEdit->setText(group["name"].toString());
    nameEdit->setClearButtonEnabled(true);
    auto* descEdit = new LineEdit();
    descEdit->setText(group["description"].toString());
    descEdit->setClearButtonEnabled(true);
    form->addRow("名称", nameEdit);
    form->addRow("描述", descEdit);
    root->addLayout(form);

    root->addWidget(new BodyLabel("动作列表"));
    auto* list = new ListWidget();
    list->setSelectionMode(QAbstractItemView::ExtendedSelection);
    list->setStyleSheet(FluentTheme::flowListStyle());
    root->addWidget(list, 1);

    QList<QString> editedActions;
    QList<QString> clipboard;
    for (const QJsonValue& value : group["actions"].toArray()) {
        if (value.isObject()) {
            editedActions.append(QString::fromUtf8(QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact)));
        }
    }

    auto selectedDialogRows = [list, &editedActions]() {
        QList<int> rows;
        const auto items = list->selectedItems();
        for (QListWidgetItem* item : items) {
            const int row = list->row(item);
            if (row >= 0 && row < editedActions.size()) {
                rows.append(row);
            }
        }
        if (rows.isEmpty()) {
            const int row = list->currentRow();
            if (row >= 0 && row < editedActions.size()) {
                rows.append(row);
            }
        }
        std::sort(rows.begin(), rows.end());
        rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
        return rows;
    };

    auto refreshDialogList = [list, &editedActions]() {
        list->clear();
        for (int i = 0; i < editedActions.size(); ++i) {
            QJsonDocument doc = QJsonDocument::fromJson(editedActions[i].toUtf8());
            const QJsonObject obj = doc.object();
            QString desc = obj["description"].toString();
            if (desc.isEmpty()) {
                desc = obj["action_type"].toString();
            }
            list->addItem(QString("%1. %2").arg(i + 1).arg(desc));
        }
    };

    auto selectDialogRows = [list](const QList<int>& rows, int currentRow = -1) {
        list->clearSelection();
        for (int row : rows) {
            if (row >= 0 && row < list->count()) {
                list->item(row)->setSelected(true);
            }
        }
        if (currentRow < 0 && !rows.isEmpty()) {
            currentRow = rows.last();
        }
        if (currentRow >= 0 && currentRow < list->count()) {
            list->setCurrentRow(currentRow);
        }
    };

    refreshDialogList();

    auto* buttons = new QHBoxLayout();
    auto* addSelectedBtn = new PushButton(QStringLiteral("\u4ece\u811a\u672c\u9009\u4e2d\u8ffd\u52a0"), FIT::ADD_TO);
    auto* upBtn = new PushButton(QStringLiteral("\u4e0a\u79fb"), FIT::UP);
    auto* downBtn = new PushButton(QStringLiteral("\u4e0b\u79fb"), FIT::DOWN);
    auto* copyBtn = new PushButton(QStringLiteral("\u590d\u5236"), FIT::COPY);
    auto* pasteBtn = new PushButton(QStringLiteral("\u7c98\u8d34"), FIT::PASTE);
    auto* deleteBtn = new PushButton(QStringLiteral("\u5220\u9664"), FIT::DELETE);
    buttons->addWidget(addSelectedBtn);
    buttons->addStretch();
    buttons->addWidget(upBtn);
    buttons->addWidget(downBtn);
    buttons->addWidget(copyBtn);
    buttons->addWidget(pasteBtn);
    buttons->addWidget(deleteBtn);
    root->addLayout(buttons);

    connect(addSelectedBtn, &QPushButton::clicked, &dialog, [&]() {
        const QList<int> rows = selectedRows();
        QList<int> insertedRows;
        for (int row : rows) {
            if (row >= 0 && row < m_actions.size()) {
                editedActions.append(m_actions[row]);
                insertedRows.append(editedActions.size() - 1);
            }
        }
        refreshDialogList();
        selectDialogRows(insertedRows);
    });

    connect(upBtn, &QPushButton::clicked, &dialog, [&]() {
        QList<int> rows = selectedDialogRows();
        if (rows.isEmpty() || rows.first() <= 0) {
            return;
        }
        for (int row : rows) {
            editedActions.swapItemsAt(row, row - 1);
        }
        for (int& row : rows) {
            --row;
        }
        refreshDialogList();
        selectDialogRows(rows, rows.first());
    });

    connect(downBtn, &QPushButton::clicked, &dialog, [&]() {
        QList<int> rows = selectedDialogRows();
        if (rows.isEmpty() || rows.last() >= editedActions.size() - 1) {
            return;
        }
        for (int i = rows.size() - 1; i >= 0; --i) {
            const int row = rows[i];
            editedActions.swapItemsAt(row, row + 1);
            rows[i] = row + 1;
        }
        refreshDialogList();
        selectDialogRows(rows, rows.last());
    });

    connect(copyBtn, &QPushButton::clicked, &dialog, [&]() {
        clipboard.clear();
        for (int row : selectedDialogRows()) {
            clipboard.append(editedActions[row]);
        }
    });

    connect(pasteBtn, &QPushButton::clicked, &dialog, [&]() {
        if (clipboard.isEmpty()) {
            return;
        }
        int insertAt = list->currentRow() + 1;
        if (insertAt < 0 || insertAt > editedActions.size()) {
            insertAt = editedActions.size();
        }
        QList<int> pastedRows;
        for (const QString& action : clipboard) {
            editedActions.insert(insertAt, action);
            pastedRows.append(insertAt);
            ++insertAt;
        }
        refreshDialogList();
        selectDialogRows(pastedRows);
    });

    connect(deleteBtn, &QPushButton::clicked, &dialog, [&]() {
        QList<int> rows = selectedDialogRows();
        if (rows.isEmpty()) {
            return;
        }
        const int nextRow = rows.first();
        for (int i = rows.size() - 1; i >= 0; --i) {
            editedActions.removeAt(rows[i]);
        }
        refreshDialogList();
        if (!editedActions.isEmpty()) {
            list->setCurrentRow(std::min(nextRow, static_cast<int>(editedActions.size()) - 1));
        }
    });

    auto* dialogButtons = new QDialogButtonBox(QDialogButtonBox::Save | QDialogButtonBox::Cancel);
    dialogButtons->button(QDialogButtonBox::Save)->setText("保存");
    dialogButtons->button(QDialogButtonBox::Cancel)->setText("取消");
    connect(dialogButtons, &QDialogButtonBox::accepted, &dialog, &QDialog::accept);
    connect(dialogButtons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    root->addWidget(dialogButtons);

    if (dialog.exec() != QDialog::Accepted) {
        return;
    }

    const QString newName = nameEdit->text().trimmed();
    if (newName.isEmpty()) {
        QMessageBox::warning(this, "保存失败", "动作组名称不能为空");
        return;
    }
    if (editedActions.isEmpty()) {
        QMessageBox::warning(this, "保存失败", "动作组必须包含至少一个动作");
        return;
    }

    QJsonArray arr;
    for (const QString& action : editedActions) {
        QJsonDocument doc = QJsonDocument::fromJson(action.toUtf8());
        if (doc.isObject()) {
            arr.append(doc.object());
        }
    }
    const QString actionsJson = QString::fromUtf8(QJsonDocument(arr).toJson(QJsonDocument::Compact));

    if (newName != name) {
        if (isLocalGroup) {
            action_group_manager_delete_group(m_groupManager, name.toUtf8().constData());
        } else {
            global_action_group_manager_delete_group(name.toUtf8().constData());
        }
    }

    const int saved = isLocalGroup
        ? action_group_manager_save_group(
            m_groupManager,
            newName.toUtf8().constData(),
            descEdit->text().trimmed().toUtf8().constData(),
            actionsJson.toUtf8().constData())
        : global_action_group_manager_save_group(
            newName.toUtf8().constData(),
            descEdit->text().trimmed().toUtf8().constData(),
            actionsJson.toUtf8().constData());
    if (!saved) {
        QMessageBox::warning(this, "保存失败", "无法保存动作组，请检查动作内容");
        if (newName != name) {
            const QJsonArray originalActions = group["actions"].toArray();
            const QString originalJson = QString::fromUtf8(QJsonDocument(originalActions).toJson(QJsonDocument::Compact));
            if (isLocalGroup) {
                action_group_manager_save_group(
                    m_groupManager,
                    name.toUtf8().constData(),
                    group["description"].toString().toUtf8().constData(),
                    originalJson.toUtf8().constData());
            } else {
                global_action_group_manager_save_group(
                    name.toUtf8().constData(),
                    group["description"].toString().toUtf8().constData(),
                    originalJson.toUtf8().constData());
            }
        }
        return;
    }

    notifyActionsChanged();
    refreshGroupList();
}

void ScriptEditor::deleteActionGroup(const QString& name)
{
    if (name.isEmpty()) {
        return;
    }

    if (QMessageBox::question(this, "确认删除", QString("确定要删除动作组 \"%1\" 吗?").arg(name))
        != QMessageBox::Yes) {
        return;
    }

    if (!action_group_manager_delete_group(m_groupManager, name.toUtf8().constData())
        && !global_action_group_manager_delete_group(name.toUtf8().constData())) {
        QMessageBox::warning(this, "删除失败", QString("动作组 \"%1\" 不存在").arg(name));
        return;
    }

    notifyActionsChanged();
}

void ScriptEditor::startPreview()
{
    if (m_actions.isEmpty()) {
        return;
    }

    if (m_viewPivot) {
        m_viewPivot->setCurrentItem("actions");
    }

    m_previewIndex = 0;
    m_previewPaused = false;
    if (m_previewBtn) {
        m_previewBtn->setVisible(false);
    }
    if (m_pausePreviewBtn) {
        m_pausePreviewBtn->setText("暂停");
        m_pausePreviewBtn->setVisible(true);
    }
    if (m_stopPreviewBtn) {
        m_stopPreviewBtn->setVisible(true);
    }

    auto* overlay = PreviewOverlay::get_instance(this);
    overlay->setAutoHideDuration(1200);
    highlightAction(m_previewIndex);
    showActionPreview(m_previewIndex);
    m_previewTimer->start();
}

void ScriptEditor::togglePausePreview()
{
    if (m_previewIndex < 0 || !m_previewTimer) {
        return;
    }

    auto* overlay = PreviewOverlay::get_instance(this);
    if (m_previewTimer->isActive()) {
        m_previewTimer->stop();
        overlay->hidePreview();
        m_previewPaused = true;
        if (m_pausePreviewBtn) {
            m_pausePreviewBtn->setText("继续");
        }
        return;
    }

    m_previewPaused = false;
    if (m_pausePreviewBtn) {
        m_pausePreviewBtn->setText("暂停");
    }
    highlightAction(m_previewIndex);
    showActionPreview(m_previewIndex);
    m_previewTimer->start();
}

void ScriptEditor::stopPreview()
{
    if (m_previewTimer) {
        m_previewTimer->stop();
    }
    m_previewIndex = -1;
    m_previewPaused = false;
    clearHighlights();
    PreviewOverlay::get_instance(this)->hidePreview();

    if (m_previewBtn) {
        m_previewBtn->setVisible(true);
    }
    if (m_pausePreviewBtn) {
        m_pausePreviewBtn->setText("暂停");
        m_pausePreviewBtn->setVisible(false);
    }
    if (m_stopPreviewBtn) {
        m_stopPreviewBtn->setVisible(false);
    }
}

void ScriptEditor::previewNextAction()
{
    if (m_previewPaused) {
        return;
    }

    if (m_actions.isEmpty()) {
        stopPreview();
        return;
    }

    ++m_previewIndex;
    if (m_previewIndex >= m_actions.size()) {
        stopPreview();
        return;
    }

    highlightAction(m_previewIndex);
    showActionPreview(m_previewIndex);
}

void ScriptEditor::highlightAction(int index)
{
    if (!m_actionList) {
        return;
    }

    clearHighlights();
    if (index < 0 || index >= m_actionList->count()) {
        return;
    }

    QListWidgetItem* item = m_actionList->item(index);
    if (auto* row = qobject_cast<ActionListRow*>(m_actionList->itemWidget(item))) {
        row->setRunning(true);
    } else {
        item->setBackground(QColor(0, 120, 212, 36));
        item->setForeground(QColor(0, 76, 140));
        QFont font = item->font();
        font.setBold(true);
        item->setFont(font);
    }
    m_actionList->setCurrentRow(index);
    m_actionList->scrollToItem(item, QAbstractItemView::PositionAtCenter);
}

void ScriptEditor::clearHighlights()
{
    if (!m_actionList) {
        return;
    }

    for (int i = 0; i < m_actionList->count(); ++i) {
        QListWidgetItem* item = m_actionList->item(i);
        if (auto* row = qobject_cast<ActionListRow*>(m_actionList->itemWidget(item))) {
            row->reset();
        } else {
            item->setBackground(QBrush());
            item->setForeground(QBrush());
            QFont font = item->font();
            font.setBold(false);
            item->setFont(font);
        }
    }
}

void ScriptEditor::showActionPreview(int index)
{
    if (index < 0 || index >= m_actions.size()) {
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(m_actions[index].toUtf8());
    if (!doc.isObject()) {
        return;
    }

    const QJsonObject action = doc.object();
    const QJsonObject params = action["params"].toObject();
    const QString type = action["action_type"].toString();
    auto* overlay = PreviewOverlay::get_instance(this);
    overlay->setAutoHideDuration(1200);

    auto intParam = [&params](const QString& key, int fallback = 0) {
        return params.contains(key) ? params.value(key).toInt(fallback) : fallback;
    };
    auto strParam = [&params](const QString& key, const QString& fallback = QString()) {
        return params.contains(key) ? params.value(key).toString(fallback) : fallback;
    };

    if (type == "mouse_click" || type == "mouse_double_click" || type == "mouse_right_click"
        || type == "mouse_click_relative") {
        QString label = "点击";
        if (type == "mouse_double_click") {
            label = "双击";
        } else if (type == "mouse_right_click") {
            label = "右键";
        }
        overlay->showClickPosition(intParam("x"), intParam("y"), label);
        return;
    }

    if (type == "mouse_move" || type == "mouse_move_relative") {
        overlay->showClickPosition(intParam("x"), intParam("y"), "移动");
        return;
    }

    if (type == "mouse_drag") {
        overlay->showDragLine(intParam("start_x"), intParam("start_y"), intParam("end_x"), intParam("end_y"));
        return;
    }

    if (type == "mouse_scroll") {
        overlay->showScrollPosition(intParam("x"), intParam("y"), intParam("clicks"));
        return;
    }

    if (type == "image_click" || type == "image_wait_click" || type == "image_check") {
        if (params.contains("x") || params.contains("y")) {
            overlay->showImagePreview(strParam("image_path"), intParam("x"), intParam("y"));
        } else {
            overlay->showImageMatch(strParam("image_path"), params.value("confidence").toDouble(0.9));
        }
        return;
    }

    if (type == "key_type") {
        overlay->showTextPreview(strParam("text"), "输入文本");
        return;
    }

    if (type == "hotkey") {
        QStringList keys;
        for (const QJsonValue& key : params["keys"].toArray()) {
            keys << key.toString();
        }
        overlay->showHotkeyPreview(keys);
        return;
    }

    if (type == "key_press" || type == "wait" || type == "screenshot") {
        QString title = action["description"].toString(type);
        QString detail;
        if (type == "key_press") {
            title = "按键";
            detail = strParam("key");
        } else if (type == "wait") {
            title = "等待";
            detail = QString("%1 秒").arg(params.value("seconds").toDouble(params.value("duration").toDouble(0.0)));
        } else if (type == "screenshot") {
            title = "截图";
            detail = strParam("save_path");
        }
        overlay->showTextPreview(detail.isEmpty() ? action["description"].toString(type) : detail, title);
        return;
    }

    if (type == "action_group_ref") {
        const QString groupName = strParam("group_name");
        const QJsonObject group = localActionGroupByName(groupName);
        overlay->showActionGroupPreview(groupName, group["actions"].toArray().size(), group["description"].toString());
    }
}

QString ScriptEditor::getCurrentActionsJson() const
{
    QJsonArray arr;
    for (const QString& action : m_actions) {
        QJsonDocument doc = QJsonDocument::fromJson(action.toUtf8());
        if (doc.isObject()) {
            arr.append(doc.object());
        }
    }
    return QString::fromUtf8(QJsonDocument(arr).toJson());
}

void ScriptEditor::addAction(const QString& actionJson)
{
    m_actions.append(actionJson);
    refreshList();
    notifyActionsChanged();
}

void ScriptEditor::removeAction(int index)
{
    if (index >= 0 && index < m_actions.size()) {
        m_actions.removeAt(index);
        refreshList();
        notifyActionsChanged();
    }
}

void ScriptEditor::clearActions()
{
    m_actions.clear();
    refreshList();
    notifyActionsChanged();
}

void ScriptEditor::setActions(const QString& json)
{
    m_actions.clear();
    QJsonDocument doc = QJsonDocument::fromJson(json.toUtf8());
    if (doc.isArray()) {
        for (const QJsonValue& val : doc.array()) {
            m_actions.append(QString::fromUtf8(QJsonDocument(val.toObject()).toJson()));
        }
    }
    refreshList();
    notifyActionsChanged();
}

void ScriptEditor::updateAction(int index, const QString& actionJson)
{
    if (index < 0 || index >= m_actions.size()) {
        return;
    }

    m_actions[index] = actionJson;
    QSignalBlocker blocker(m_actionList);
    refreshList();
    m_actionList->setCurrentRow(index);
    notifyActionsChanged();
}

int ScriptEditor::selectedActionIndex() const
{
    return m_actionList ? m_actionList->currentRow() : -1;
}

int ScriptEditor::actionCount() const
{
    return m_actions.size();
}

void ScriptEditor::setActionRunning(int index)
{
    if (m_previewIndex >= 0) {
        stopPreview();
    }
    highlightAction(index);
}

void ScriptEditor::clearAllRunning()
{
    clearHighlights();
}

QString ScriptEditor::getLocalActionGroupsJson() const
{
    if (!m_groupManager) {
        return "{}";
    }

    char* json = action_group_manager_to_json(m_groupManager);
    if (!json) {
        return "{}";
    }

    QString result = QString::fromUtf8(json);
    action_free_string(json);
    return result.isEmpty() ? "{}" : result;
}

void ScriptEditor::setLocalActionGroupsJson(const QString& json)
{
    if (!m_groupManager) {
        return;
    }

    action_group_manager_load_json(m_groupManager, json.toUtf8().constData());
    refreshGroupList();
}

QString ScriptEditor::currentTabName() const
{
    if (m_currentTabIndex < 0 || m_currentTabIndex >= m_tabs.size()) {
        return {};
    }
    return m_tabs[m_currentTabIndex].title;
}

void ScriptEditor::setCurrentTabName(const QString& name)
{
    const QString trimmed = name.trimmed();
    if (trimmed.isEmpty() || m_currentTabIndex < 0 || m_currentTabIndex >= m_tabs.size()) {
        return;
    }

    m_tabs[m_currentTabIndex].title = trimmed;
    if (m_tabBar) {
        m_tabBar->setTabText(m_currentTabIndex, trimmed);
    }
    emit tabChanged(trimmed, m_currentTabIndex);
}

void ScriptEditor::keyPressEvent(QKeyEvent* event)
{
    if (event->matches(QKeySequence::Copy)) {
        copySelectedActions();
        event->accept();
        return;
    }
    if (event->matches(QKeySequence::Paste)) {
        pasteActionsAfterCurrent();
        event->accept();
        return;
    }

    if (event->key() == Qt::Key_Delete) {
        deleteSelectedActions();
        event->accept();
        return;
    }

    if (event->modifiers() & Qt::ControlModifier) {
        if (event->key() == Qt::Key_Up) {
            moveSelectedUp();
            event->accept();
            return;
        }
        if (event->key() == Qt::Key_Down) {
            moveSelectedDown();
            event->accept();
            return;
        }
    }

    QWidget::keyPressEvent(event);
}

void ScriptEditor::refreshList()
{
    m_actionList->clear();
    for (int i = 0; i < m_actions.size(); ++i) {
        auto* item = new QListWidgetItem();
        item->setData(Qt::UserRole, i);
        m_actionList->addItem(item);

        auto* row = new ActionListRow(m_actions[i], i, true, true, m_actionList);
        item->setSizeHint(row->sizeHint() + QSize(0, 4));
        m_actionList->setItemWidget(item, row);

        connect(row, &ActionListRow::actionClicked, this, [this](int index) {
            if (index >= 0 && index < m_actions.size()) {
                m_actionList->setCurrentRow(index);
                emit actionSelected(m_actions[index], index);
            }
        });
        connect(row, &ActionListRow::deleteRequested, this, [this, row]() {
            for (int idx = 0; idx < m_actionList->count(); ++idx) {
                if (m_actionList->itemWidget(m_actionList->item(idx)) == row) {
                    removeAction(idx);
                    return;
                }
            }
        });
    }
    m_statusLabel->setText(QString("%1 个步骤").arg(m_actions.size()));
}

void ScriptEditor::onItemClicked(int row)
{
    if (row >= 0 && row < m_actions.size()) {
        emit actionSelected(m_actions[row], row);
    }
}

void ScriptEditor::onItemDoubleClicked(int row)
{
    if (row >= 0 && row < m_actions.size()) {
        emit executeSingle(row);
    }
}

void ScriptEditor::deleteAction(int index)
{
    removeAction(index);
}

QList<int> ScriptEditor::selectedRows() const
{
    QList<int> rows;
    if (!m_actionList) {
        return rows;
    }

    const auto items = m_actionList->selectedItems();
    for (QListWidgetItem* item : items) {
        const int row = m_actionList->row(item);
        if (row >= 0 && row < m_actions.size()) {
            rows.append(row);
        }
    }

    if (rows.isEmpty()) {
        const int row = m_actionList->currentRow();
        if (row >= 0 && row < m_actions.size()) {
            rows.append(row);
        }
    }

    std::sort(rows.begin(), rows.end());
    rows.erase(std::unique(rows.begin(), rows.end()), rows.end());
    return rows;
}

void ScriptEditor::selectRows(const QList<int>& rows, int currentRow)
{
    if (!m_actionList || rows.isEmpty()) {
        return;
    }

    m_actionList->clearSelection();
    for (int row : rows) {
        if (row >= 0 && row < m_actionList->count()) {
            m_actionList->item(row)->setSelected(true);
        }
    }

    if (currentRow < 0) {
        currentRow = rows.last();
    }
    if (currentRow >= 0 && currentRow < m_actionList->count()) {
        m_actionList->setCurrentRow(currentRow);
    }
}

void ScriptEditor::copySelectedActions()
{
    const QList<int> rows = selectedRows();
    if (rows.isEmpty()) {
        return;
    }

    m_clipboard.clear();
    for (int row : rows) {
        m_clipboard.append(m_actions[row]);
    }
}

void ScriptEditor::pasteActionsAfterCurrent()
{
    if (m_clipboard.isEmpty()) {
        return;
    }

    int insertAt = m_actionList ? m_actionList->currentRow() + 1 : m_actions.size();
    if (insertAt < 0 || insertAt > m_actions.size()) {
        insertAt = m_actions.size();
    }

    QList<int> pastedRows;
    for (const QString& action : m_clipboard) {
        m_actions.insert(insertAt, action);
        pastedRows.append(insertAt);
        ++insertAt;
    }

    refreshList();
    selectRows(pastedRows);
    notifyActionsChanged();
}

void ScriptEditor::duplicateSelectedActions()
{
    copySelectedActions();
    pasteActionsAfterCurrent();
}

void ScriptEditor::moveSelectedUp()
{
    QList<int> rows = selectedRows();
    if (rows.isEmpty() || rows.first() <= 0) {
        return;
    }

    for (int row : rows) {
        m_actions.swapItemsAt(row, row - 1);
    }

    for (int& row : rows) {
        --row;
    }

    refreshList();
    selectRows(rows, rows.first());
    notifyActionsChanged();
}

void ScriptEditor::moveSelectedDown()
{
    QList<int> rows = selectedRows();
    if (rows.isEmpty() || rows.last() >= m_actions.size() - 1) {
        return;
    }

    for (int i = rows.size() - 1; i >= 0; --i) {
        const int row = rows[i];
        m_actions.swapItemsAt(row, row + 1);
        rows[i] = row + 1;
    }

    refreshList();
    selectRows(rows, rows.last());
    notifyActionsChanged();
}

void ScriptEditor::deleteSelectedActions()
{
    QList<int> rows = selectedRows();
    if (rows.isEmpty()) {
        return;
    }

    const int nextRow = rows.first();
    for (int i = rows.size() - 1; i >= 0; --i) {
        m_actions.removeAt(rows[i]);
    }

    refreshList();
    if (!m_actions.isEmpty()) {
        m_actionList->setCurrentRow(std::min(nextRow, static_cast<int>(m_actions.size()) - 1));
    }
    notifyActionsChanged();
}

QJsonArray ScriptEditor::localActionGroupsArray() const
{
    if (!m_groupManager) {
        return {};
    }

    char* json = action_group_manager_get_all_json(m_groupManager);
    if (!json) {
        return {};
    }

    QJsonDocument doc = QJsonDocument::fromJson(QByteArray(json));
    action_free_string(json);
    return doc.isArray() ? doc.array() : QJsonArray();
}

QJsonArray ScriptEditor::availableActionGroupsArray() const
{
    QJsonArray merged;
    QSet<QString> localNames;

    for (const QJsonValue& value : localActionGroupsArray()) {
        QJsonObject group = value.toObject();
        const QString name = group["name"].toString();
        if (name.isEmpty()) {
            continue;
        }
        group["is_local"] = true;
        merged.append(group);
        localNames.insert(name);
    }

    char* json = global_action_group_manager_get_all_json();
    if (!json) {
        return merged;
    }
    QJsonDocument doc = QJsonDocument::fromJson(QByteArray(json));
    action_free_string(json);
    if (!doc.isArray()) {
        return merged;
    }

    for (const QJsonValue& value : doc.array()) {
        QJsonObject group = value.toObject();
        const QString name = group["name"].toString();
        if (name.isEmpty() || localNames.contains(name)) {
            continue;
        }
        group["is_local"] = false;
        merged.append(group);
    }
    return merged;
}

QString ScriptEditor::selectedActionsJson(const QList<int>& rows) const
{
    QJsonArray arr;
    for (int row : rows) {
        if (row < 0 || row >= m_actions.size()) {
            continue;
        }
        QJsonDocument doc = QJsonDocument::fromJson(m_actions[row].toUtf8());
        if (doc.isObject()) {
            arr.append(doc.object());
        }
    }
    return QString::fromUtf8(QJsonDocument(arr).toJson(QJsonDocument::Compact));
}

bool ScriptEditor::currentActionIsGroupRef(int row, QString* groupName) const
{
    if (row < 0 || row >= m_actions.size()) {
        return false;
    }

    QJsonDocument doc = QJsonDocument::fromJson(m_actions[row].toUtf8());
    if (!doc.isObject()) {
        return false;
    }

    const QJsonObject obj = doc.object();
    if (obj["action_type"].toString() != "action_group_ref") {
        return false;
    }

    if (groupName) {
        *groupName = obj["params"].toObject()["group_name"].toString();
    }
    return true;
}

void ScriptEditor::saveSelectedAsActionGroup()
{
    const QList<int> rows = selectedRows();
    if (rows.isEmpty()) {
        return;
    }

    bool ok = false;
    const QString name = QInputDialog::getText(
        this,
        "动作组名称",
        "名称",
        QLineEdit::Normal,
        "",
        &ok).trimmed();
    if (!ok || name.isEmpty()) {
        return;
    }

    const QString description = QInputDialog::getText(
        this,
        "动作组描述",
        "描述",
        QLineEdit::Normal,
        "",
        &ok).trimmed();
    if (!ok) {
        return;
    }

    const QString actionsJson = selectedActionsJson(rows);
    const int saved = action_group_manager_save_group(
        m_groupManager,
        name.toUtf8().constData(),
        description.toUtf8().constData(),
        actionsJson.toUtf8().constData());
    if (!saved) {
        QMessageBox::warning(this, "保存失败", "无法保存动作组，请检查名称和动作内容");
        return;
    }

    QMessageBox::information(this, "保存成功", QString("动作组 \"%1\" 已保存").arg(name));
    notifyActionsChanged();
}

void ScriptEditor::insertActionGroupRef(const QString& name, int index)
{
    if (name.isEmpty()) {
        return;
    }

    QJsonObject params;
    params["group_name"] = name;

    QJsonObject obj;
    obj["action_type"] = "action_group_ref";
    obj["params"] = params;
    obj["description"] = QString("动作组引用: %1").arg(name);
    obj["delay_before"] = 0.0;
    obj["delay_after"] = 0.0;
    obj["window_title"] = QJsonValue::Null;
    obj["use_relative_coords"] = false;
    obj["background_mode"] = false;
    obj["name"] = "";
    obj["condition"] = "";
    obj["repeat_count"] = 1;

    int insertAt = index + 1;
    if (insertAt < 0 || insertAt > m_actions.size()) {
        insertAt = m_actions.size();
    }

    m_actions.insert(insertAt, QString::fromUtf8(QJsonDocument(obj).toJson(QJsonDocument::Compact)));
    refreshList();
    m_actionList->setCurrentRow(insertAt);
    notifyActionsChanged();
}

void ScriptEditor::expandActionGroupRef(int index)
{
    QString groupName;
    if (!currentActionIsGroupRef(index, &groupName) || groupName.isEmpty()) {
        return;
    }

    char* json = action_group_manager_get_group_actions_json(
        m_groupManager,
        groupName.toUtf8().constData());
    if (!json) {
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(QByteArray(json));
    action_free_string(json);
    if (!doc.isArray() || doc.array().isEmpty()) {
        char* globalJson = global_action_group_manager_get_group_actions_json(groupName.toUtf8().constData());
        if (globalJson) {
            doc = QJsonDocument::fromJson(QByteArray(globalJson));
            action_free_string(globalJson);
        }
    }
    if (!doc.isArray() || doc.array().isEmpty()) {
        QMessageBox::warning(this, "解压失败", QString("动作组 \"%1\" 不存在或没有动作").arg(groupName));
        return;
    }

    m_actions.removeAt(index);
    QList<int> insertedRows;
    int insertAt = index;
    for (const QJsonValue& value : doc.array()) {
        if (!value.isObject()) {
            continue;
        }
        m_actions.insert(insertAt, QString::fromUtf8(QJsonDocument(value.toObject()).toJson(QJsonDocument::Compact)));
        insertedRows.append(insertAt);
        ++insertAt;
    }

    refreshList();
    selectRows(insertedRows, insertedRows.isEmpty() ? index : insertedRows.first());
    notifyActionsChanged();
}

void ScriptEditor::clearAllWithConfirm()
{
    if (m_actions.isEmpty()) {
        return;
    }

    if (QMessageBox::question(this, "确认清空", "确定要清空所有动作吗?") != QMessageBox::Yes) {
        return;
    }

    clearActions();
}
