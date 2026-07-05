#include "command_panel.h"
#include <QFileDialog>
#include <QFrame>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMessageBox>
#include <QProcess>
#include <QVBoxLayout>

#include "QFluent/IconWidget.h"
#include "Theme.h"

using FIT = Fluent::IconType;

CommandManagerWidget::CommandManagerWidget(QWidget* parent)
    : QWidget(parent)
    , m_manager(command_manager_new())
    , m_testTimer(new QTimer(this))
    , m_testProcess(nullptr)
    , m_testSeconds(0.0)
{
    setupUI();
    m_testTimer->setInterval(100);
    connect(m_testTimer, &QTimer::timeout, this, [this]() {
        m_testSeconds += 0.1;
        if (m_testBtn) {
            m_testBtn->setText(QStringLiteral("\u505c\u6b62 %1s").arg(m_testSeconds, 0, 'f', 1));
        }
    });
    loadCommands();
}

CommandManagerWidget::~CommandManagerWidget()
{
    if (m_testProcess) {
        m_testProcess->terminate();
        m_testProcess->deleteLater();
        m_testProcess = nullptr;
    }
    command_manager_free(m_manager);
}

void CommandManagerWidget::setupUI()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(16, 12, 16, 12);
    layout->setSpacing(12);

    auto* header = new QHBoxLayout();
    auto* titleCol = new QVBoxLayout();
    titleCol->setSpacing(2);

    auto* titleLabel = new TitleLabel(QStringLiteral("\u542f\u52a8\u547d\u4ee4"));
    titleCol->addWidget(titleLabel);

    auto* subtitleLabel = new CaptionLabel(QStringLiteral("\u7ba1\u7406\u5e38\u7528\u7a0b\u5e8f\u4e0e\u7a97\u53e3\u7684\u5feb\u901f\u542f\u52a8"));
    subtitleLabel->setStyleSheet(FluentTheme::mutedCaptionStyle());
    titleCol->addWidget(subtitleLabel);

    header->addLayout(titleCol);
    header->addStretch();

    auto* addBtn = new PrimaryPushButton(QStringLiteral("\u6dfb\u52a0"), FIT::ADD);
    addBtn->setFixedHeight(32);
    connect(addBtn, &QPushButton::clicked, this, &CommandManagerWidget::showAddForm);
    header->addWidget(addBtn);
    layout->addLayout(header);

    m_formCard = new QWidget();
    m_formCard->setStyleSheet(QString(
        "background: %1; border: 1px solid %2; border-radius: 10px;")
        .arg(FluentTheme::panelBgColor(), FluentTheme::panelBorderColor()));
    m_formCard->setVisible(false);
    auto* formLayout = new QVBoxLayout(m_formCard);
    formLayout->setContentsMargins(20, 16, 20, 16);
    formLayout->setSpacing(14);

    m_formTitle = new SubtitleLabel(QStringLiteral("\u6dfb\u52a0\u65b0\u547d\u4ee4"));
    formLayout->addWidget(m_formTitle);

    m_nameEdit = new LineEdit();
    m_nameEdit->setPlaceholderText(QStringLiteral("\u547d\u4ee4\u540d\u79f0\uff0c\u5982\uff1a\u8bb0\u4e8b\u672c"));
    m_nameEdit->setClearButtonEnabled(true);
    m_nameEdit->setMinimumHeight(32);
    formLayout->addWidget(m_nameEdit);

    m_commandEdit = new LineEdit();
    m_commandEdit->setPlaceholderText(QStringLiteral("\u542f\u52a8\u547d\u4ee4\u6216\u8def\u5f84\uff0c\u5982\uff1anotepad.exe"));
    m_commandEdit->setClearButtonEnabled(true);
    m_commandEdit->setMinimumHeight(32);
    formLayout->addWidget(m_commandEdit);

    m_patternEdit = new LineEdit();
    m_patternEdit->setPlaceholderText(QStringLiteral("\u7a97\u53e3\u6807\u9898\u5173\u952e\u5b57\uff08\u68c0\u6d4b\u662f\u5426\u5df2\u542f\u52a8\uff09"));
    m_patternEdit->setClearButtonEnabled(true);
    m_patternEdit->setMinimumHeight(32);
    formLayout->addWidget(m_patternEdit);

    m_descriptionEdit = new LineEdit();
    m_descriptionEdit->setPlaceholderText(QStringLiteral("\u63cf\u8ff0\uff08\u53ef\u9009\uff09"));
    m_descriptionEdit->setClearButtonEnabled(true);
    m_descriptionEdit->setMinimumHeight(32);
    formLayout->addWidget(m_descriptionEdit);

    m_delaySpin = new DoubleSpinBox();
    m_delaySpin->setRange(0, 300);
    m_delaySpin->setValue(0);
    m_delaySpin->setSuffix("s");
    m_delaySpin->setSingleStep(0.5);
    m_delaySpin->setFixedWidth(96);
    m_delaySpin->setFixedHeight(32);
    formLayout->addWidget(m_delaySpin);

    auto* btnRow = new QHBoxLayout();
    m_testBtn = new PushButton(QStringLiteral("\u6d4b\u8bd5\u8ba1\u65f6"), FIT::PLAY);
    m_testBtn->setFixedHeight(32);
    connect(m_testBtn, &QPushButton::clicked, this, &CommandManagerWidget::testCommand);
    btnRow->addWidget(m_testBtn);
    btnRow->addStretch();
    auto* saveBtn = new PrimaryPushButton(QStringLiteral("\u4fdd\u5b58"), FIT::SAVE);
    saveBtn->setFixedHeight(32);
    connect(saveBtn, &QPushButton::clicked, this, &CommandManagerWidget::saveCommand);
    btnRow->addWidget(saveBtn);
    auto* cancelBtn = new PushButton(QStringLiteral("\u53d6\u6d88"), FIT::CANCEL);
    cancelBtn->setFixedHeight(32);
    connect(cancelBtn, &QPushButton::clicked, this, &CommandManagerWidget::hideForm);
    btnRow->addWidget(cancelBtn);
    formLayout->addLayout(btnRow);

    layout->addWidget(m_formCard);

    auto* scrollArea = new ScrollArea();
    scrollArea->setWidgetResizable(true);
    scrollArea->setFrameShape(QFrame::NoFrame);
    scrollArea->setStyleSheet("QScrollArea { border: none; background: transparent; }");

    auto* scrollContent = new QWidget();
    scrollContent->setStyleSheet("background: transparent;");
    m_listLayout = new QVBoxLayout(scrollContent);
    m_listLayout->setContentsMargins(0, 4, 0, 8);
    m_listLayout->setSpacing(8);

    m_emptyWidget = new QWidget();
    m_emptyWidget->setStyleSheet("background: transparent;");
    auto* emptyLayout = new QVBoxLayout(m_emptyWidget);
    emptyLayout->setContentsMargins(24, 48, 24, 48);
    emptyLayout->setSpacing(12);
    auto* emptyTitle = new SubtitleLabel(QStringLiteral("\u6682\u65e0\u542f\u52a8\u547d\u4ee4"));
    emptyTitle->setAlignment(Qt::AlignCenter);
    emptyLayout->addWidget(emptyTitle);
    auto* emptyDesc = new CaptionLabel(QStringLiteral("\u70b9\u51fb\u201c\u6dfb\u52a0\u201d\u521b\u5efa\u547d\u4ee4\uff0c\u7528\u4e8e\u5feb\u901f\u542f\u52a8\u5e38\u7528\u7a0b\u5e8f"));
    emptyDesc->setAlignment(Qt::AlignCenter);
    emptyDesc->setStyleSheet(FluentTheme::mutedCaptionStyle());
    emptyLayout->addWidget(emptyDesc);
    m_listLayout->addWidget(m_emptyWidget);
    m_listLayout->addStretch();

    scrollArea->setWidget(scrollContent);
    layout->addWidget(scrollArea, 1);
}

void CommandManagerWidget::loadCommands()
{
    char* json = command_manager_get_all_json(m_manager);
    if (!json) return;

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(json).toUtf8());
    action_free_string(json);

    QJsonArray arr = doc.array();
    m_emptyWidget->setVisible(arr.isEmpty());

    for (int i = 0; i < arr.size(); ++i) {
        QJsonObject obj = arr[i].toObject();
        const QString commandId = obj["id"].toString();

        auto* card = new QWidget();
        card->setProperty("commandId", commandId);
        card->setStyleSheet(QString(
            "background: %1; border: 1px solid %2; border-radius: 8px;")
            .arg(FluentTheme::panelBgColor(), FluentTheme::panelBorderColor()));
        card->setMinimumHeight(64);
        card->setMaximumHeight(86);
        auto* cardLayout = new QHBoxLayout(card);
        cardLayout->setContentsMargins(14, 10, 12, 10);
        cardLayout->setSpacing(12);

        auto* icon = new IconWidget(FIT::APPLICATION, card);
        icon->setFixedSize(28, 28);
        cardLayout->addWidget(icon);

        auto* infoLayout = new QVBoxLayout();
        infoLayout->setSpacing(2);
        infoLayout->addWidget(new StrongBodyLabel(obj["name"].toString()));

        auto* cmdLabel = new CaptionLabel(obj["command"].toString());
        cmdLabel->setStyleSheet(FluentTheme::mutedCaptionStyle());
        infoLayout->addWidget(cmdLabel);

        QStringList metaParts;
        if (!obj["window_title_pattern"].toString().isEmpty()) {
            metaParts << obj["window_title_pattern"].toString();
        }
        if (!obj["description"].toString().isEmpty()) {
            metaParts << obj["description"].toString();
        }
        if (obj["delay_after_launch"].toDouble() > 0.0) {
            metaParts << QStringLiteral("\u5ef6\u8fdf %1s").arg(obj["delay_after_launch"].toDouble(), 0, 'g', 4);
        }
        if (obj["use_count"].toInt() > 0) {
            metaParts << QStringLiteral("\u4f7f\u7528 %1 \u6b21").arg(obj["use_count"].toInt());
        }
        if (!metaParts.isEmpty()) {
            auto* metaLabel = new CaptionLabel(metaParts.join(QStringLiteral(" | ")));
            metaLabel->setStyleSheet(FluentTheme::mutedCaptionStyle());
            infoLayout->addWidget(metaLabel);
        }

        cardLayout->addLayout(infoLayout, 1);

        auto* runBtn = new PrimaryPushButton(QStringLiteral("\u542f\u52a8"), FIT::PLAY);
        runBtn->setFixedHeight(28);
        connect(runBtn, &QPushButton::clicked, this, [this, commandId]() {
            runCommand(commandId);
        });
        cardLayout->addWidget(runBtn);

        auto* editBtn = new PushButton(QStringLiteral("\u7f16\u8f91"), FIT::EDIT);
        editBtn->setFixedHeight(28);
        editBtn->setFixedWidth(74);
        connect(editBtn, &QPushButton::clicked, this, [this, obj]() {
            showEditForm(obj);
        });
        cardLayout->addWidget(editBtn);

        auto* delBtn = new PushButton(QStringLiteral("\u5220\u9664"), FIT::DELETE);
        delBtn->setFixedHeight(28);
        delBtn->setFixedWidth(74);
        connect(delBtn, &QPushButton::clicked, this, [this, commandId]() {
            deleteCommand(commandId);
        });
        cardLayout->addWidget(delBtn);

        int insertPos = m_listLayout->count() - 1;
        m_listLayout->insertWidget(insertPos, card);
    }
}

void CommandManagerWidget::showAddForm()
{
    m_editingCommandId.clear();
    m_formTitle->setText(QStringLiteral("\u6dfb\u52a0\u65b0\u547d\u4ee4"));
    m_formCard->setVisible(true);
    m_nameEdit->clear();
    m_commandEdit->clear();
    m_patternEdit->clear();
    m_descriptionEdit->clear();
    m_delaySpin->setValue(0);
    m_nameEdit->setFocus();
}

void CommandManagerWidget::showEditForm(const QJsonObject& command)
{
    m_editingCommandId = command["id"].toString();
    if (m_editingCommandId.isEmpty()) {
        return;
    }
    m_formTitle->setText(QStringLiteral("\u7f16\u8f91\u542f\u52a8\u547d\u4ee4"));
    m_formCard->setVisible(true);
    m_nameEdit->setText(command["name"].toString());
    m_commandEdit->setText(command["command"].toString());
    m_patternEdit->setText(command["window_title_pattern"].toString());
    m_descriptionEdit->setText(command["description"].toString());
    m_delaySpin->setValue(command["delay_after_launch"].toDouble(0.0));
    m_nameEdit->setFocus();
}

void CommandManagerWidget::hideForm()
{
    m_formCard->setVisible(false);
    m_editingCommandId.clear();
}

void CommandManagerWidget::saveCommand()
{
    QString name = m_nameEdit->text().trimmed();
    QString command = m_commandEdit->text().trimmed();
    QString pattern = m_patternEdit->text().trimmed();
    QString description = m_descriptionEdit->text().trimmed();

    if (name.isEmpty() || command.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u540d\u79f0\u548c\u547d\u4ee4\u4e0d\u80fd\u4e3a\u7a7a"));
        return;
    }

    if (m_editingCommandId.isEmpty()) {
        char* result = command_manager_add_command(
            m_manager, name.toUtf8().constData(), command.toUtf8().constData(),
            pattern.toUtf8().constData(), description.toUtf8().constData(), m_delaySpin->value());
        if (result) action_free_string(result);
    } else {
        QJsonObject updates;
        updates["name"] = name;
        updates["command"] = command;
        updates["window_title_pattern"] = pattern;
        updates["description"] = description;
        updates["delay_after_launch"] = m_delaySpin->value();
        const QByteArray json = QJsonDocument(updates).toJson(QJsonDocument::Compact);
        if (!command_manager_update_command(
                m_manager,
                m_editingCommandId.toUtf8().constData(),
                json.constData())) {
            QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u66f4\u65b0\u547d\u4ee4\u5931\u8d25"));
            return;
        }
    }

    hideForm();
    refreshList();
}

void CommandManagerWidget::testCommand()
{
    if (m_testTimer->isActive()) {
        m_testTimer->stop();
        if (m_testProcess) {
            m_testProcess->terminate();
            m_testProcess->deleteLater();
            m_testProcess = nullptr;
        }
        m_delaySpin->setValue(m_testSeconds);
        m_testBtn->setText(QStringLiteral("\u6d4b\u8bd5\u8ba1\u65f6"));
        QMessageBox::information(
            this,
            QStringLiteral("\u63d0\u793a"),
            QStringLiteral("\u5df2\u8bb0\u5f55\u5ef6\u8fdf: %1 \u79d2").arg(m_testSeconds, 0, 'f', 1));
        return;
    }

    const QString command = m_commandEdit->text().trimmed();
    if (command.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u547d\u4ee4\u4e0d\u80fd\u4e3a\u7a7a"));
        return;
    }

    if (m_testProcess) {
        m_testProcess->deleteLater();
    }
    m_testProcess = new QProcess(this);
    connect(m_testProcess, &QProcess::errorOccurred, this, [this](QProcess::ProcessError) {
        if (m_testTimer->isActive()) {
            m_testTimer->stop();
        }
        m_testBtn->setText(QStringLiteral("\u6d4b\u8bd5\u8ba1\u65f6"));
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u6d4b\u8bd5\u547d\u4ee4\u5931\u8d25"));
    });
    m_testSeconds = 0.0;
    m_testProcess->startCommand(command);
    if (!m_testProcess->waitForStarted(1000)) {
        m_testProcess->deleteLater();
        m_testProcess = nullptr;
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u6d4b\u8bd5\u547d\u4ee4\u5931\u8d25"));
        return;
    }
    m_testBtn->setText(QStringLiteral("\u505c\u6b62 0.0s"));
    m_testTimer->start();
}

void CommandManagerWidget::runCommand(const QString& commandId)
{
    if (commandId.isEmpty()) {
        return;
    }

    char* result = command_manager_check_and_launch(m_manager, commandId.toUtf8().constData());
    if (!result) {
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u542f\u52a8\u547d\u4ee4\u5931\u8d25"));
        return;
    }

    QJsonDocument doc = QJsonDocument::fromJson(QString::fromUtf8(result).toUtf8());
    action_free_string(result);

    QJsonObject obj = doc.object();
    const bool success = obj["success"].toBool(false);
    const bool alreadyRunning = obj["already_running"].toBool(false);
    const QString message = obj["message"].toString(success ? QStringLiteral("\u547d\u4ee4\u6267\u884c\u6210\u529f") : QStringLiteral("\u547d\u4ee4\u6267\u884c\u5931\u8d25"));

    if (success) {
        QMessageBox::information(this, QStringLiteral("\u63d0\u793a"), alreadyRunning ? QStringLiteral("\u7a97\u53e3\u5df2\u5728\u8fd0\u884c") : message);
        refreshList();
    } else {
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), message);
    }
}

void CommandManagerWidget::deleteCommand(const QString& commandId)
{
    if (commandId.isEmpty()) {
        return;
    }

    if (QMessageBox::question(this, QStringLiteral("\u786e\u8ba4\u5220\u9664"), QStringLiteral("\u786e\u5b9a\u8981\u5220\u9664\u8fd9\u4e2a\u542f\u52a8\u547d\u4ee4\u5417\uff1f"))
        != QMessageBox::Yes) {
        return;
    }

    if (!command_manager_delete_command(m_manager, commandId.toUtf8().constData())) {
        QMessageBox::warning(this, QStringLiteral("\u9519\u8bef"), QStringLiteral("\u5220\u9664\u547d\u4ee4\u5931\u8d25"));
    }

    refreshList();
}

void CommandManagerWidget::refreshList()
{
    for (int i = m_listLayout->count() - 1; i >= 0; --i) {
        QLayoutItem* item = m_listLayout->itemAt(i);
        QWidget* widget = item ? item->widget() : nullptr;
        if (widget && widget != m_emptyWidget) {
            m_listLayout->removeWidget(widget);
            widget->deleteLater();
        }
    }

    loadCommands();
}
