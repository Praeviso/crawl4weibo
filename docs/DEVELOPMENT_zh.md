# Crawl4Weibo 开发文档

[English](DEVELOPMENT.md) | [中文](DEVELOPMENT_zh.md)

## 目录
- [开发环境设置](#开发环境设置)
- [项目结构](#项目结构)
- [开发工作流](#开发工作流)
- [测试指南](#测试指南)
- [代码质量](#代码质量)

## 开发环境设置

### 环境要求
- Python 3.9+
- uv (推荐的包管理工具)

### 快速开始
```bash
# 克隆项目
git clone https://github.com/Kritoooo/crawl4weibo.git
cd crawl4weibo

# 安装开发依赖
uv sync --dev

# 运行测试确保环境正常
uv run pytest tests/ -v
```

### 开发依赖说明
```toml
[dependency-groups]
dev = [
    "pytest>=7.4.4",    # 测试框架
    "pytest-cov>=4.1.0", # 测试覆盖率
    "ruff>=0.14.0",      # 现代化的快速linter和formatter
]
```

## 项目结构

```
crawl4weibo/
├── crawl4weibo/           # 主包
│   ├── __init__.py
│   ├── core/              # 核心功能
│   │   ├── __init__.py
│   │   └── client.py      # WeiboClient主要实现
│   ├── models/            # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py        # User模型
│   │   └── post.py        # Post模型
│   ├── utils/             # 工具模块
│   │   ├── __init__.py
│   │   ├── logger.py      # 日志工具
│   │   └── parser.py      # 解析工具
│   └── exceptions/        # 自定义异常
│       ├── __init__.py
│       └── base.py        # 基础异常类
├── tests/                 # 测试文件
│   ├── __init__.py
│   ├── test_models.py     # 模型单元测试
│   ├── test_client.py     # 客户端单元测试
│   └── test_integration.py # 集成测试
├── docs/                  # 文档
├── examples/              # 示例代码
├── .github/workflows/     # GitHub Actions配置
├── pyproject.toml         # 项目配置
├── pytest.ini            # 测试配置
└── README.md
```

## 开发工作流

### 分支策略
- `main` - 主分支,稳定版本
- `develop` - 开发分支
- `feature/*` - 功能分支
- `hotfix/*` - 热修复分支

### 功能开发流程
```bash
# 1. 从main创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. 开发过程中持续测试
uv run pytest tests/ -m unit  # 快速单元测试

# 3. 提交前完整检查
uv run ruff check crawl4weibo --fix  # 检查并自动修复问题
uv run ruff format crawl4weibo       # 格式化代码
uv run pytest tests/                 # 运行所有测试

# 4. 提交代码
git add .
git commit -m "feat: add your feature description"

# 5. 推送并创建PR
git push origin feature/your-feature-name
# 然后在GitHub创建Pull Request
```

### 提交信息规范
使用约定式提交格式:
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整(不影响功能)
refactor: 重构代码
test: 添加测试
chore: 构建或工具相关
```

## 测试指南

### 测试类型
项目包含两种类型的测试:

#### 单元测试 (`@pytest.mark.unit`)
- 测试单个函数或类的功能
- 不依赖外部API或服务
- 运行快速,适合开发过程中频繁运行

```bash
# 只运行单元测试
uv run pytest tests/ -m unit -v
```

#### 集成测试 (`@pytest.mark.integration`)
- 测试与真实微博API的交互
- 验证API返回数据结构的正确性
- 运行较慢,适合完整验证

```bash
# 只运行集成测试
uv run pytest tests/ -m integration -v
```

### 运行测试
```bash
# 运行所有测试
uv run pytest tests/ -v

# 带覆盖率报告
uv run pytest tests/ --cov=crawl4weibo --cov-report=html

# 运行特定测试文件
uv run pytest tests/test_models.py -v

# 运行特定测试方法
uv run pytest tests/test_models.py::TestUser::test_user_creation -v
```

### 编写测试

#### 单元测试示例
```python
import pytest
from crawl4weibo.models.user import User

@pytest.mark.unit
class TestUser:
    def test_user_creation(self):
        user = User(id="123", screen_name="TestUser")
        assert user.id == "123"
        assert user.screen_name == "TestUser"
```

#### 集成测试示例
```python
import pytest
from crawl4weibo import WeiboClient

@pytest.mark.integration
class TestWeiboClientIntegration:
    def test_get_user_by_uid_returns_data(self):
        client = WeiboClient()
        try:
            user = client.get_user_by_uid("2656274875")
            assert user is not None
            assert hasattr(user, 'screen_name')
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
```

## 代码质量

### 代码风格
项目使用 **Ruff** 作为统一的代码质量工具,提供极快的linting和formatting:

#### Ruff - 统一的代码质量工具
```bash
# 代码检查
uv run ruff check crawl4weibo

# 自动修复问题
uv run ruff check crawl4weibo --fix

# 代码格式化
uv run ruff format crawl4weibo

# 检查格式(不修改)
uv run ruff format crawl4weibo --check
```

### 配置文件
Ruff配置在 `pyproject.toml` 中:
```toml
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "F",     # pyflakes
    "I",     # isort
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "C4",    # flake8-comprehensions
    "SIM",   # flake8-simplify
]

[tool.ruff.format]
quote-style = "double"
```

## 开发最佳实践

### 提交前检查
推送代码前的完整检查流程:
```bash
# 1. 安装依赖
uv sync --dev

# 2. 代码质量检查和修复
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo

# 3. 运行测试
uv run pytest tests/ -v

# 4. 构建包验证(可选)
uv build
```

## 常见问题

### 测试失败
```bash
# 查看详细错误信息
uv run pytest tests/ -v --tb=long

# 运行单个失败测试
uv run pytest tests/test_file.py::test_function -v
```

### 代码格式问题
```bash
# 使用ruff自动修复
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo
```

### 依赖问题
```bash
# 重新安装依赖
rm -rf .venv
uv venv
uv sync --dev
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 确保所有检查通过
5. 创建Pull Request
6. 响应Code Review反馈

### Code Review检查点
- 代码功能正确性
- 测试覆盖率
- 代码风格一致性(通过ruff检查)
- 性能影响
- 向后兼容性

欢迎贡献代码!如有问题请创建Issue讨论。
