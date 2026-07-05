#include "action_panel.h"
#include <QFont>
#include <QHeaderView>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QTreeWidgetItem>
#include <QVBoxLayout>
#include "QFluent/Label.h"
#include "QFluent/LineEdit.h"
#include "fluent_theme.h"

ActionPanel::ActionPanel(QWidget* parent)
    : QWidget(parent)
{
    setupUI();
    loadActions();
}

void ActionPanel::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(8);

    m_search = new SearchLineEdit();
    m_search->setPlaceholderText(QStringLiteral("\u641c\u7d22\u64cd\u4f5c..."));
    connect(m_search, &QLineEdit::textChanged, this, &ActionPanel::rebuildTree);
    layout->addWidget(m_search);

    m_actionTree = new QTreeWidget();
    m_actionTree->setHeaderHidden(true);
    m_actionTree->setRootIsDecorated(true);
    m_actionTree->setUniformRowHeights(true);
    m_actionTree->setIndentation(16);
    m_actionTree->header()->setSectionResizeMode(QHeaderView::Stretch);
    m_actionTree->setStyleSheet(
        "QTreeWidget { border: 1px solid " + FluentTheme::panelBorderColor() + "; border-radius: 8px; "
        "background: transparent; outline: none; color: " + FluentTheme::textPrimary() + "; }"
        "QTreeWidget::item { min-height: 30px; padding: 3px 6px; border-radius: 5px; }"
        "QTreeWidget::item:hover { background: " + FluentTheme::panelBgColor() + "; }"
        "QTreeWidget::item:selected { background: " + FluentTheme::panelBgColor() + "; color: " + FluentTheme::textPrimary() + "; }"
        "QTreeWidget::branch { background: transparent; }");
    connect(m_actionTree, &QTreeWidget::itemDoubleClicked, this, &ActionPanel::onItemDoubleClicked);
    layout->addWidget(m_actionTree, 1);

    auto* tip = new CaptionLabel(QStringLiteral("\u53cc\u51fb\u6dfb\u52a0\u5230\u6d41\u7a0b"));
    tip->setAlignment(Qt::AlignCenter);
    tip->setStyleSheet(FluentTheme::mutedCaptionStyle());
    layout->addWidget(tip);
}

void ActionPanel::loadActions()
{
    if (char* catalogJson = action_manager_get_catalog_json()) {
        QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(catalogJson).toUtf8());
        action_free_string(catalogJson);
        if (doc.isArray()) {
            m_categories.clear();
            m_actionsByCategory.clear();
            m_actionLabels.clear();
            for (const QJsonValue& value : doc.array()) {
                const QJsonObject obj = value.toObject();
                const QString category = obj["category"].toString();
                if (category.isEmpty()) {
                    continue;
                }
                m_categories.append(category);
                QStringList actions;
                for (const QJsonValue& actionValue : obj["actions"].toArray()) {
                    const QJsonObject actionObj = actionValue.toObject();
                    const QString type = actionObj["type"].toString();
                    if (type.isEmpty()) {
                        continue;
                    }
                    actions.append(type);
                    const QString name = actionObj["name"].toString();
                    if (!name.isEmpty()) {
                        m_actionLabels[type] = name;
                    }
                }
                m_actionsByCategory[category] = actions;
            }
        }
    }

    m_categoryLabels = {
        {"mouse", QStringLiteral("\u9f20\u6807\u64cd\u4f5c")},
        {"keyboard", QStringLiteral("\u952e\u76d8\u64cd\u4f5c")},
        {"control", QStringLiteral("\u63a7\u5236")},
        {"other", QStringLiteral("\u5176\u4ed6")},
        {"window", QStringLiteral("\u7a97\u53e3\u64cd\u4f5c")},
        {"image", QStringLiteral("\u56fe\u50cf\u8bc6\u522b")},
        {"group", QStringLiteral("\u52a8\u4f5c\u7ec4")},
    };

    if (m_categories.isEmpty()) {
        m_categories = {"mouse", "keyboard", "control", "other", "window", "image", "group"};
        m_actionsByCategory["mouse"] = {"mouse_click", "mouse_double_click", "mouse_right_click", "mouse_move", "mouse_drag", "mouse_scroll"};
        m_actionsByCategory["keyboard"] = {"key_press", "key_type", "hotkey"};
        m_actionsByCategory["control"] = {"wait"};
        m_actionsByCategory["other"] = {"screenshot"};
        m_actionsByCategory["window"] = {"mouse_move_relative", "mouse_click_relative"};
        m_actionsByCategory["image"] = {"image_click", "image_wait_click", "image_check"};
        m_actionsByCategory["group"] = {"action_group_ref"};
    }

    const QMap<QString, QString> fallbackActionLabels = {
        {"mouse_click", QStringLiteral("\u9f20\u6807\u5355\u51fb")},
        {"mouse_double_click", QStringLiteral("\u9f20\u6807\u53cc\u51fb")},
        {"mouse_right_click", QStringLiteral("\u9f20\u6807\u53f3\u952e")},
        {"mouse_move", QStringLiteral("\u9f20\u6807\u79fb\u52a8")},
        {"mouse_drag", QStringLiteral("\u9f20\u6807\u62d6\u62fd")},
        {"mouse_scroll", QStringLiteral("\u9f20\u6807\u6eda\u8f6e")},
        {"key_press", QStringLiteral("\u6309\u952e")},
        {"key_type", QStringLiteral("\u8f93\u5165\u6587\u672c")},
        {"hotkey", QStringLiteral("\u5feb\u6377\u952e")},
        {"wait", QStringLiteral("\u7b49\u5f85")},
        {"screenshot", QStringLiteral("\u622a\u56fe")},
        {"mouse_move_relative", QStringLiteral("\u7a97\u53e3\u5185\u9f20\u6807\u79fb\u52a8")},
        {"mouse_click_relative", QStringLiteral("\u7a97\u53e3\u5185\u9f20\u6807\u70b9\u51fb")},
        {"image_click", QStringLiteral("\u56fe\u7247\u70b9\u51fb")},
        {"image_wait_click", QStringLiteral("\u7b49\u5f85\u56fe\u7247\u70b9\u51fb")},
        {"image_check", QStringLiteral("\u68c0\u67e5\u56fe\u7247")},
        {"action_group_ref", QStringLiteral("\u52a8\u4f5c\u7ec4\u5f15\u7528")},
    };
    for (auto it = fallbackActionLabels.constBegin(); it != fallbackActionLabels.constEnd(); ++it) {
        if (!m_actionLabels.contains(it.key())) {
            m_actionLabels[it.key()] = it.value();
        }
    }

    rebuildTree("");
}

void ActionPanel::rebuildTree(const QString& filter)
{
    m_actionTree->clear();
    const QString ft = filter.trimmed();

    for (const QString& category : m_categories) {
        const QStringList actions = m_actionsByCategory.value(category);
        const QString categoryLabel = m_categoryLabels.value(category, category);
        QStringList matchedActions;

        for (const QString& actionType : actions) {
            const QString actionLabel = m_actionLabels.value(actionType, actionType);
            const bool matched = ft.isEmpty()
                || actionType.contains(ft, Qt::CaseInsensitive)
                || actionLabel.contains(ft, Qt::CaseInsensitive)
                || category.contains(ft, Qt::CaseInsensitive)
                || categoryLabel.contains(ft, Qt::CaseInsensitive);
            if (matched) {
                matchedActions.append(actionType);
            }
        }

        if (!ft.isEmpty() && matchedActions.isEmpty()) {
            continue;
        }

        auto* categoryItem = new QTreeWidgetItem(m_actionTree);
        categoryItem->setText(0, categoryLabel);
        categoryItem->setData(0, Qt::UserRole, QString());
        categoryItem->setExpanded(true);
        QFont categoryFont = categoryItem->font(0);
        categoryFont.setBold(true);
        categoryItem->setFont(0, categoryFont);

        const QStringList visibleActions = ft.isEmpty() ? actions : matchedActions;
        for (const QString& actionType : visibleActions) {
            auto* actionItem = new QTreeWidgetItem(categoryItem);
            actionItem->setText(0, QStringLiteral("  ") + m_actionLabels.value(actionType, actionType));
            actionItem->setData(0, Qt::UserRole, actionType);
        }
    }
}

void ActionPanel::onItemDoubleClicked(QTreeWidgetItem* item, int column)
{
    Q_UNUSED(column);
    QString actionType = item->data(0, Qt::UserRole).toString();
    if (actionType.isEmpty()) return;

    char* json = action_new(actionType.toUtf8().constData());
    if (json) {
        emit actionAdded(QString::fromUtf8(json));
        action_free_string(json);
    }
}
