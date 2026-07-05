#pragma once

#include <QWidget>
#include <QLabel>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QString>
#include <QSize>
#include <QEvent>
#include <QMouseEvent>

#include "simpleRPA_ffi.h"
#include "FluentIcon.h"
#include "QFluent/Label.h"

class IconWidget;
class TransparentToolButton;

class ActionListRow : public QWidget
{
    Q_OBJECT

public:
    explicit ActionListRow(const QString& actionJson, int index, bool showDelete = false, bool allowGroupExpand = true, QWidget* parent = nullptr);

    void setRunning(bool running, int repeat = 0, int subIndex = -1);
    void setCompleted(bool completed);
    void reset();

    bool isExpanded() const { return m_expanded; }
    bool isGroup() const { return m_actionType == "action_group_ref"; }
    int getIndex() const { return m_index; }
    QString getActionJson() const { return m_actionJson; }

    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;

signals:
    void deleteRequested();
    void actionClicked(int index);

protected:
    bool eventFilter(QObject* obj, QEvent* event) override;

private:
    static constexpr int ROW_HEIGHT = 34;
    static constexpr int BADGE_SIZE = 20;
    static constexpr const char* ACCENT_COLOR = "#0078D4";
    static constexpr const char* GREEN_COLOR = "#16A34A";

    void setupUI();
    void parseActionJson();
    void updateStylesheet();
    void toggleExpand();

    Fluent::IconType actionTypeIcon(const QString& type) const;
    QString stepBadgeStyle() const;

    QString m_actionJson;
    int m_index;
    bool m_showDelete;
    bool m_allowGroupExpand;
    bool m_expanded;
    bool m_isRunning;
    bool m_isCompleted;

    QString m_actionType;
    QString m_description;

    QWidget* m_header;
    CaptionLabel* m_stepBadge;
    TransparentToolButton* m_expandBtn;
    IconWidget* m_iconWidget;
    BodyLabel* m_descLabel;
    CaptionLabel* m_statusLabel;
    TransparentToolButton* m_deleteBtn;

    QVBoxLayout* m_rootLayout;
    QHBoxLayout* m_headerLayout;
};
