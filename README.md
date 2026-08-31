# FoodArena Meal-Ranking Model

面向 **foodarena-ai** 的可解释选餐排序基线。它先执行预算、辣度、素食、过敏原和忌口等硬约束，再用一个成对逻辑回归线性模型对剩余菜品排序。

> 当前 `v0.1.0` 仅用于打通产品流程。训练数据是固定随机种子的合成偏好，指标不能代表真实用户效果。尤其不要把推荐结果作为过敏安全保证；食材、加工过程和交叉接触风险仍须向商家核实。

## 功能

- 硬约束优先：不会为了凑够结果而放宽预算、过敏原、素食或辣度限制
- 无匹配时返回 `no_match`，并保留排除原因
- 输出每个排序特征的贡献，便于解释和调试
- 可复现训练：固定种子、数据摘要、留出集指标和版本化模型文件
- 零第三方依赖：本地预测、训练和 HTTP API 只使用 Python 标准库
- 配有单元测试、端到端 API 测试、Docker 和 GitHub Actions

## 快速开始

需要 Python 3.10 或更新版本。在仓库根目录运行：

```bash
python -m unittest discover -s tests -v
python -m foodarena.predict
python -m foodarena.api
```

服务默认只监听 `127.0.0.1:8000`：

```bash
python examples/client.py
curl http://127.0.0.1:8000/health
```

也可以使用容器：

```bash
docker compose up --build
```

## API

`POST /recommend`，请求体上限 256 KiB。最小请求如下，省略 `dishes` 时使用演示菜单：

```json
{
  "profile": {
    "budget": 18,
    "max_spice": 1,
    "preferred_spice": 0,
    "vegetarian": false,
    "allergens": ["花生"],
    "disliked_ingredients": [],
    "preferred_cuisines": ["中式"]
  },
  "top_k": 3
}
```

foodarena-ai 只需把它的用户条件和实时菜单填入同一结构。每道菜必须提供 `allergens_verified`；当用户声明过敏原而菜品信息未核实时，模型会直接排除该菜。

## 重新训练

合成数据训练只用于验证管线：

```bash
python -m foodarena.train
```

使用真实数据时，传入一个偏好对 JSON 数组：

```bash
python -m foodarena.train --data data/private/preferences.json
```

每条记录包含 `profile`、`left`、`right` 和取值为 `left` 或 `right` 的 `preferred`。仓库默认忽略 `data/private/`，避免误传用户数据。正式实验应按用户和时间切分训练/验证集，并评估不同预算区间、饮食偏好群体的覆盖率、约束违规率和排序质量。

## 项目结构

```text
foodarena/          排序、训练、命令行预测和 HTTP API
models/             版本化模型文件
data/               仅含合成演示菜单
examples/           请求与客户端示例
tests/              约束、校验、训练和 API 测试
reports/            当前演示模型指标
MODEL_CARD.md        适用范围、限制和评估说明
SECURITY.md          漏洞报告和部署注意事项
```

## 数据与隐私

只收集改进模型必需的明确偏好；取得用户同意后再记录，设置保存期限，并允许删除。不要提交姓名、联系方式、精确位置、健康诊断、登录凭据或原始请求日志。用于过敏过滤的信息可能具有健康敏感性，生产系统应加密、限制访问并做隐私审查。

## 许可证

[MIT](LICENSE)
