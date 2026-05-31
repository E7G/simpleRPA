"""重置 SimpleRPA 每日定时执行标记，方便调试。

清空配置中的 schedule_last_run_date，使「每天只执行一次」的限制复位，
下次满足条件（到点 / 空闲）时会重新触发。
"""

import json
import os


def main():
    config_path = os.path.join(os.path.expanduser('~'), '.simpleRPA', 'config.json')

    if not os.path.exists(config_path):
        print(f'配置文件不存在: {config_path}')
        print('（应用尚未运行过，无需重置）')
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    old = data.get('schedule_last_run_date', '')
    data['schedule_last_run_date'] = ''

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f'已重置每日执行标记（原值: {old or "空"}）')
    print(f'配置文件: {config_path}')


if __name__ == '__main__':
    main()
