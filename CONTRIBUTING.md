# 贡献指南

感谢你对 simpleRPA 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 报告 Bug
- 提出新功能建议
- 提交代码改进
- 改进文档
- 分享使用经验

## 行为准则

参与本项目时，请遵守以下准则：

- 尊重所有参与者
- 接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表现出同理心

## 如何贡献

### 报告 Bug

在提交 Bug 报告前，请先检查 [Issues](https://github.com/E7G/simpleRPA/issues) 是否已有类似问题。

提交 Bug 报告时，请包含以下信息：

1. **问题描述** - 清晰描述遇到的问题
2. **复现步骤** - 详细说明如何复现问题
3. **预期行为** - 描述你期望发生的行为
4. **实际行为** - 描述实际发生的行为
5. **环境信息**
   - 操作系统版本
   - Python 版本
   - simpleRPA 版本
6. **截图/日志** - 如有可能，提供相关截图或错误日志

### 提出新功能

在提出新功能前，请先：

1. 检查是否已有类似的功能请求
2. 考虑该功能是否符合项目目标
3. 描述清楚新功能的用途和价值

提交功能请求时，请包含：

1. **功能描述** - 清晰描述新功能
2. **使用场景** - 说明该功能的使用场景
3. **实现建议** - 如有可能，提供实现思路

### 提交代码

#### 开发环境设置

1. Fork 本仓库
2. 克隆你的 Fork

```bash
git clone https://github.com/YOUR_USERNAME/simpleRPA.git
cd simpleRPA
```

3. 创建开发环境

使用 pip：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

或使用 Pixi（推荐）：

```bash
pixi install
pixi shell
```

#### 代码规范

- 遵循 PEP 8 Python 代码风格指南
- 使用有意义的变量和函数名
- 添加必要的注释和文档字符串
- 保持代码简洁和可读性

#### 提交流程

1. 创建新分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

2. 进行开发和测试

```bash
# 运行测试
python -m pytest tests/

# 运行程序测试
python main.py
```

3. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
# 或
git commit -m "fix: 修复问题描述"
```

提交信息格式建议：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

4. 推送到你的 Fork

```bash
git push origin feature/your-feature-name
```

5. 创建 Pull Request

- 在 GitHub 上创建 Pull Request
- 填写 PR 模板
- 等待代码审查

### 改进文档

文档改进同样重要！你可以：

- 修正错误或不清晰的内容
- 添加使用示例
- 翻译文档
- 补充缺失的文档

## Pull Request 指南

### PR 检查清单

提交 PR 前，请确保：

- [ ] 代码符合项目代码风格
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确
- [ ] PR 描述详细说明了更改内容

### PR 审查流程

1. 提交 PR 后，维护者会进行代码审查
2. 可能会要求进行修改
3. 修改后更新 PR
4. 审查通过后，代码将被合并

## 测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_all.py

# 运行特定测试函数
python -m pytest tests/test_all.py::test_function_name

# 显示详细输出
python -m pytest tests/ -v
```

### 添加测试

为新增功能或 Bug 修复添加测试：

- 测试文件放在 `tests/` 目录
- 使用 pytest 框架
- 确保测试独立且可重复运行

## 版本发布

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- 主版本号：不兼容的 API 修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

## 获取帮助

如果在贡献过程中遇到问题：

- 查看 [文档](docs/USER_GUIDE.md)
- 搜索 [Issues](https://github.com/E7G/simpleRPA/issues)
- 创建新的 Issue 提问

## 许可证

贡献的代码将采用与项目相同的 [GPL-3.0 License](LICENSE)。

## 致谢

感谢所有贡献者！你的贡献让 simpleRPA 变得更好。

---

再次感谢你的贡献！🎉