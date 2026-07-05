#pragma once

#include <QString>
#include "Theme.h"

namespace FluentTheme {

inline bool isDark() { return Theme::isDark(); }
inline QString textPrimary() { return isDark() ? "#FFFFFF" : "#1A1A1A"; }
inline QString textSecondary() { return isDark() ? "rgba(255,255,255,0.72)" : "rgba(0,0,0,0.62)"; }
inline QString textMuted() { return isDark() ? "rgba(255,255,255,0.50)" : "rgba(0,0,0,0.45)"; }
inline QString accentColor() { return Theme::themeColor().name(); }
inline QString successColor() { return isDark() ? "#4ADE80" : "#16A34A"; }
inline QString panelBorderColor() { return isDark() ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.10)"; }
inline QString panelBgColor() { return isDark() ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)"; }
inline QString canvasBgColor() { return isDark() ? "rgba(255,255,255,0.07)" : "#FAFAFA"; }

inline QString panelTitleStyle() {
    return "color: " + textSecondary() + "; font-size: 12px; font-weight: 600; background: transparent; border: none; padding: 0;";
}
inline QString mutedLabelStyle() { return "color: " + textSecondary() + ";"; }
inline QString mutedCaptionStyle() { return "color: " + textMuted() + ";"; }

inline QString automatePanelStyle(bool canvas = false) {
    QString bg = canvas ? canvasBgColor() : panelBgColor();
    QString border = panelBorderColor();
    return "QWidget#automatePanel { background-color: " + bg + "; border: 1px solid " + border + "; border-radius: 8px; }"
           "QWidget#automatePanel QWidget#automatePanelHeader { background: transparent; border: none; }"
           "QWidget#automatePanel QLabel { background: transparent; border: none; }";
}

inline QString automateToolbarStyle() {
    QString bg = panelBgColor();
    QString border = panelBorderColor();
    QString sec = textSecondary();
    return "QWidget#automateToolbar { background-color: " + bg + "; border: 1px solid " + border + "; border-radius: 4px; }"
           "QWidget#automateToolbar > QLabel { color: " + sec + "; }";
}

inline QString compactSpinStyle() {
    QString fg = textPrimary();
    QString accent = accentColor();
    QString bg = isDark() ? "rgba(255,255,255,0.08)" : "#FFFFFF";
    QString border = panelBorderColor();
    return "QDoubleSpinBox, QSpinBox { color: " + fg + "; background-color: " + bg + "; border: 1px solid " + border + "; border-radius: 6px; min-height: 28px; max-height: 28px; padding: 0 4px; }"
           "QDoubleSpinBox:hover, QSpinBox:hover { border-color: " + accent + "; }"
           "QDoubleSpinBox QLineEdit, QSpinBox QLineEdit { color: " + fg + "; background: transparent; border: none; padding: 2px 4px; min-height: 22px; }";
}

inline QString listItemCardStyle() {
    QString border = panelBorderColor();
    QString bg = isDark() ? "rgba(255,255,255,0.04)" : "#FFFFFF";
    QString hover = isDark() ? "rgba(255,255,255,0.08)" : "#F5F7FA";
    QString accent = accentColor();
    return "QWidget { background-color: " + bg + "; border: 1px solid " + border + "; border-radius: 8px; }"
           "QWidget:hover { border-color: " + accent + "; background-color: " + hover + "; }";
}

inline QString settingFormStyle() {
    QString border = panelBorderColor();
    QString bg = isDark() ? "rgba(255,255,255,0.05)" : "#FFFFFF";
    return "QWidget { background-color: " + bg + "; border: 1px solid " + border + "; border-radius: 10px; }";
}

inline QString flowListStyle() {
    QString fg = textPrimary();
    return "QListWidget { border: none; background: transparent; outline: none; color: " + fg + "; }"
           "QListWidget::item { background: transparent; border: none; margin: 3px 0; padding: 0; }"
           "QListWidget::item:selected { background: transparent; border: none; }";
}

inline QString statusBarStyle() {
    QString border = panelBorderColor();
    QString bg = panelBgColor();
    return "QWidget#statusBar { background-color: " + bg + "; border-top: 1px solid " + border + "; }"
           "QWidget#statusBar QLabel { color: " + textSecondary() + "; }";
}

inline QString scrollBorderStyle() {
    return "QScrollArea { border: 1px solid " + panelBorderColor() + "; border-radius: 8px; background: transparent; }";
}

} // namespace FluentTheme
