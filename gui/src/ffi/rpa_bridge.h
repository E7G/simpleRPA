#ifndef RPA_BRIDGE_H
#define RPA_BRIDGE_H

#include <QString>
#include <QVector>
#include <cstdint>

extern "C" {
#include "simplerpa.h"
}

struct WindowInfo {
    int64_t hwnd;
    QString title;
    int32_t x, y, width, height;
};

class RpaBridge {
public:
    RpaBridge();
    ~RpaBridge();

    // Config
    bool loadConfig();
    void saveConfig();
    double getDefaultSpeed();
    int getDefaultRepeatCount();
    void setDefaultSpeed(double val);
    void setDefaultRepeatCount(int val);
    bool getInfiniteLoop();
    void setInfiniteLoop(bool val);
    double getTimeout();
    void setTimeout(double val);
    bool getMinimizeToTray();
    void setMinimizeToTray(bool val);
    bool getRunWindowOffscreen();
    void setRunWindowOffscreen(bool val);

    // Actions
    void* createAction(int type);
    void destroyAction(void* h);
    QString getActionDescription(void* h);
    QString actionToJson(void* h);
    void* actionFromJson(const QString& json);
    void setActionParamI64(void* h, const char* key, int64_t val);
    void setActionParamF64(void* h, const char* key, double val);
    void setActionParamStr(void* h, const char* key, const char* val);
    void setActionParamBool(void* h, const char* key, bool val);
    void setActionDelayBefore(void* h, double s);
    void setActionDelayAfter(void* h, double s);
    void setActionWindowTitle(void* h, const char* title);
    void setActionUseRelativeCoords(void* h, bool val);
    void setActionBackgroundMode(void* h, bool val);
    void setActionName(void* h, const char* name);
    void setActionCondition(void* h, const char* cond);
    void setActionRepeatCount(void* h, int count);
    QString validateAction(void* h);
    int getActionType(void* h);

    // Player
    void* createPlayer();
    void destroyPlayer(void* h);
    void playerSetSpeed(void* h, double speed);
    void playerSetRepeatCount(void* h, int count);
    void playerSetInfiniteLoop(void* h, bool val);
    void playerSetTimeout(void* h, double seconds);
    void playerSetWindowHwnd(void* h, int64_t hwnd);
    void playerSetWindowTitle(void* h, const char* title);
    void playerSetWindowOffset(void* h, int32_t x, int32_t y);
    void playerSetWindowRunMode(void* h, const char* mode);
    void playerPlay(void* h);
    void playerPause(void* h);
    void playerResume(void* h);
    void playerStop(void* h);
    int playerGetState(void* h);
    int playerGetCurrentIndex(void* h);
    int playerGetCurrentRepeat(void* h);
    int playerGetTotalActions(void* h);

    // Windows
    QVector<WindowInfo> getAllWindows();
    int64_t findWindowByTitle(const QString& title);
    bool activateWindow(int64_t hwnd);

    // Commands
    QString getAllCommandsJson();
    QString addCommand(const QString& name, const QString& cmd, const QString& pattern, const QString& desc);
    bool deleteCommand(const QString& id);
    QString executeCommand(const QString& id);

private:
    void* configHandle = nullptr;
    void* windowUtilsHandle = nullptr;
    void* exporterHandle = nullptr;
    void* commandManagerHandle = nullptr;
};

#endif // RPA_BRIDGE_H
