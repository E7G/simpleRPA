#include "action_list_row.h"
#include "QFluent/IconWidget.h"
#include "QFluent/Label.h"
#include "QFluent/ToolButton.h"

using FIT = Fluent::IconType;

ActionListRow::ActionListRow(const QString& actionJson, int index, bool showDelete, bool allowGroupExpand, QWidget* parent)
    : QWidget(parent)
    , m_actionJson(actionJson)
    , m_index(index)
    , m_showDelete(showDelete)
    , m_allowGroupExpand(allowGroupExpand)
    , m_expanded(false)
    , m_isRunning(false)
    , m_isCompleted(false)
    , m_header(nullptr)
    , m_stepBadge(nullptr)
    , m_expandBtn(nullptr)
    , m_iconWidget(nullptr)
    , m_descLabel(nullptr)
    , m_statusLabel(nullptr)
    , m_deleteBtn(nullptr)
    , m_rootLayout(nullptr)
    , m_headerLayout(nullptr)
{
    setObjectName("ActionListRow");
    setFixedHeight(ROW_HEIGHT);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    parseActionJson();
    setupUI();
    updateStylesheet();
}

void ActionListRow::parseActionJson()
{
    QJsonDocument doc = QJsonDocument::fromJson(m_actionJson.toUtf8());
    if (!doc.isObject()) return;

    QJsonObject obj = doc.object();
    m_actionType = obj["action_type"].toString().toLower();
    m_description = obj["description"].toString();
    if (m_description.isEmpty()) {
        m_description = m_actionType;
    }
}

void ActionListRow::setupUI()
{
    m_rootLayout = new QVBoxLayout(this);
    m_rootLayout->setContentsMargins(0, 0, 0, 0);
    m_rootLayout->setSpacing(0);

    m_header = new QWidget(this);
    m_headerLayout = new QHBoxLayout(m_header);
    m_headerLayout->setContentsMargins(8, 0, 6, 0);
    m_headerLayout->setSpacing(6);

    m_stepBadge = new CaptionLabel(QString::number(m_index + 1), m_header);
    m_stepBadge->setFixedSize(BADGE_SIZE, BADGE_SIZE);
    m_stepBadge->setAlignment(Qt::AlignCenter);
    m_stepBadge->setStyleSheet(stepBadgeStyle());
    m_headerLayout->addWidget(m_stepBadge);

    m_expandBtn = new TransparentToolButton(m_header);
    m_expandBtn->setFixedSize(20, 20);

    if (isGroup() && m_allowGroupExpand) {
        m_expandBtn->setIcon(FIT::CHEVRON_RIGHT_MED);
        m_expandBtn->setToolTip("展开动作组");
        m_expandBtn->setCursor(Qt::PointingHandCursor);
        connect(m_expandBtn, &QToolButton::clicked, this, &ActionListRow::toggleExpand);
        m_headerLayout->addWidget(m_expandBtn);
    } else {
        QWidget* placeholder = new QWidget(m_header);
        placeholder->setFixedSize(20, 20);
        m_headerLayout->addWidget(placeholder);
    }

    m_iconWidget = new IconWidget(actionTypeIcon(m_actionType), m_header);
    m_iconWidget->setFixedSize(16, 16);
    m_headerLayout->addWidget(m_iconWidget);

    QString desc = m_description;
    if (desc.length() > 52) {
        desc = desc.left(49) + "...";
    }
    m_descLabel = new BodyLabel(desc, m_header);
    m_descLabel->setStyleSheet("color: #333; font-size: 13px; background: transparent; border: none;");
    m_headerLayout->addWidget(m_descLabel, 1);

    m_statusLabel = new CaptionLabel("", m_header);
    m_statusLabel->setFixedWidth(44);
    m_statusLabel->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    m_statusLabel->setStyleSheet("color: #666; font-size: 12px; background: transparent; border: none;");
    m_headerLayout->addWidget(m_statusLabel);

    if (m_showDelete) {
        m_deleteBtn = new TransparentToolButton(FIT::DELETE, m_header);
        m_deleteBtn->setFixedSize(22, 22);
        m_deleteBtn->setIconSize(QSize(14, 14));
        m_deleteBtn->setToolTip("删除");
        m_deleteBtn->setCursor(Qt::PointingHandCursor);
        connect(m_deleteBtn, &QToolButton::clicked, this, &ActionListRow::deleteRequested);
        m_headerLayout->addWidget(m_deleteBtn);
    }

    m_header->installEventFilter(this);

    m_rootLayout->addWidget(m_header);
}

Fluent::IconType ActionListRow::actionTypeIcon(const QString& type) const
{
    if (type == "mouse_click" || type == "mouse_double_click" || type == "mouse_right_click"
        || type == "mouse_click_relative") {
        return FIT::APPLICATION;
    } else if (type == "mouse_move" || type == "mouse_move_relative" || type == "mouse_drag") {
        return FIT::MOVE;
    } else if (type == "mouse_scroll") {
        return FIT::SCROLL;
    } else if (type == "key_press" || type == "key_type" || type == "hotkey") {
        return FIT::COMMAND_PROMPT;
    } else if (type == "wait") {
        return FIT::STOP_WATCH;
    } else if (type == "screenshot") {
        return FIT::CAMERA;
    } else if (type == "image_click" || type == "image_wait_click" || type == "image_check") {
        return FIT::PHOTO;
    } else if (type == "action_group_ref") {
        return FIT::LIBRARY;
    }
    return FIT::APPLICATION;
}

QString ActionListRow::stepBadgeStyle() const
{
    return QString(
        "QLabel {"
        "  background-color: %1;"
        "  color: white;"
        "  font-size: 10px;"
        "  font-weight: bold;"
        "  border-radius: 10px;"
        "  border: none;"
        "}"
    ).arg(ACCENT_COLOR);
}

void ActionListRow::updateStylesheet()
{
    QString bg;
    if (m_isRunning) {
        bg = QString("rgba(0, 120, 212, 0.12)");
    } else if (m_isCompleted) {
        bg = "rgba(22, 163, 74, 0.08)";
    } else {
        bg = "transparent";
    }

    setStyleSheet(QString(
        "ActionListRow {"
        "  background-color: %1;"
        "  border: none;"
        "  border-radius: 4px;"
        "}"
        "ActionListRow:hover {"
        "  background-color: %2;"
        "}"
    ).arg(bg, m_isRunning ? "rgba(0, 120, 212, 0.16)" : m_isCompleted ? "rgba(22, 163, 74, 0.12)" : "rgba(0, 0, 0, 0.03)"));

    if (m_isRunning) {
        m_stepBadge->setStyleSheet(QString(
            "QLabel {"
            "  background-color: %1;"
            "  color: white;"
            "  font-size: 10px;"
            "  font-weight: bold;"
            "  border-radius: 10px;"
            "  border: none;"
            "}"
        ).arg(ACCENT_COLOR));
    } else if (m_isCompleted) {
        m_stepBadge->setStyleSheet(QString(
            "QLabel {"
            "  background-color: %1;"
            "  color: white;"
            "  font-size: 10px;"
            "  font-weight: bold;"
            "  border-radius: 10px;"
            "  border: none;"
            "}"
        ).arg(GREEN_COLOR));
    } else {
        m_stepBadge->setStyleSheet(stepBadgeStyle());
    }
}

void ActionListRow::setRunning(bool running, int repeat, int subIndex)
{
    m_isRunning = running;
    m_isCompleted = false;

    if (running) {
        m_statusLabel->setText("\u25B6");
        m_statusLabel->setStyleSheet(QString("color: %1; font-weight: bold; background: transparent; border: none;").arg(ACCENT_COLOR));
    } else {
        m_statusLabel->setText("");
        m_statusLabel->setStyleSheet("color: #666; background: transparent; border: none;");
    }

    updateStylesheet();
}

void ActionListRow::setCompleted(bool completed)
{
    m_isCompleted = completed;
    m_isRunning = false;

    if (completed) {
        m_statusLabel->setText("\u2713");
        m_statusLabel->setStyleSheet(QString("color: %1; font-weight: bold; background: transparent; border: none;").arg(GREEN_COLOR));
    } else {
        m_statusLabel->setText("");
        m_statusLabel->setStyleSheet("color: #666; background: transparent; border: none;");
    }

    updateStylesheet();
}

void ActionListRow::reset()
{
    m_isRunning = false;
    m_isCompleted = false;
    m_statusLabel->setText("");
    m_statusLabel->setStyleSheet("color: #666; background: transparent; border: none;");
    updateStylesheet();
}

void ActionListRow::toggleExpand()
{
    if (!isGroup() || !m_allowGroupExpand) return;

    m_expanded = !m_expanded;
    m_expandBtn->setIcon(m_expanded ? FIT::CHEVRON_DOWN_MED : FIT::CHEVRON_RIGHT_MED);
}

bool ActionListRow::eventFilter(QObject* obj, QEvent* event)
{
    if (event->type() == QEvent::MouseButtonRelease) {
        QMouseEvent* mouseEvent = static_cast<QMouseEvent*>(event);
        if (mouseEvent->button() == Qt::LeftButton) {
            if (obj == m_header) {
                emit actionClicked(m_index);
                return true;
            }
        }
    }
    return QWidget::eventFilter(obj, event);
}

QSize ActionListRow::sizeHint() const
{
    return QSize(-1, ROW_HEIGHT);
}

QSize ActionListRow::minimumSizeHint() const
{
    return QSize(100, ROW_HEIGHT);
}
