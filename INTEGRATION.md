# 接入 foodarena-ai

本仓库提供独立模型模块，不修改现有 foodarena-ai 仓库。

## Python 直接调用

在仓库根目录运行，或者把本仓库目录添加到应用模块搜索路径：

```python
from foodarena.ranker import recommend

result = recommend({
    "profile": {"budget": 18, "max_spice": 1, "allergens": ["花生"]},
    "top_k": 3,
})
```

生产接入时必须传入实时的 `dishes`，不要使用演示菜单。

## 后端 HTTP 调用

先运行 `python -m foodarena.api`。应用后端向 `POST http://127.0.0.1:8000/recommend` 发送 JSON。
浏览器前端应通过自己的后端调用；示例 API 没有跨域 CORS 或身份验证支持，不应暴露到公网。

## 数据契约

请求只允许 `profile`、`dishes`、`top_k`。`top_k` 为 1–20 的整数。

用户条件：

| 字段 | 要求 |
| --- | --- |
| budget | 必填，0.01–10000 元 |
| max_spice | 0–3，默认 3（不辣/微辣/中辣/重辣） |
| preferred_spice | 0–max_spice，默认等于 max_spice |
| vegetarian | 布尔，默认 false；本演示按蛋奶素语义，纯素需自行扩展 |
| allergens | 需避开的规范化过敏原名称数组 |
| disliked_ingredients | 忌口食材名称数组 |
| preferred_cuisines | 偏好菜系名称数组 |

每道菜必须有以下字段：

```json
{
  "id": "rice-tomato-egg",
  "name": "番茄鸡蛋饭",
  "price": 12,
  "cuisine": "中式",
  "spice": 0,
  "rating": 4.5,
  "wait_minutes": 6,
  "vegetarian": true,
  "available": true,
  "allergens_verified": true,
  "allergens": ["鸡蛋", "大豆"],
  "ingredients": ["米饭", "番茄", "鸡蛋", "大豆"]
}
```

本基线只做去空格、大小写归一后的**精确词项匹配**，不会自动识别“花生/peanut”等同义词。
接入方必须统一菜单和偏好词表，展开复合配料/酱料中的过敏原，未知信息设置 `allergens_verified: false`，不可把未知情况填成已核实的空列表。

## 响应处理

- HTTP 200 + `status: ok`：展示 `recommendations`，分数只用于当前候选排序。
- HTTP 200 + `status: no_match`：展示排除原因，邀请用户主动修改预算或其他可调整条件；不得自动忽略过敏原。
- HTTP 400：数据或字段不合法，应修复输入。
- HTTP 413：请求体超出限制。
- HTTP 415：缺少 `Content-Type: application/json`。
- HTTP 404：路径不存在。

## 与辩论/美食擂台结合

推荐结果可作为“擂台”的候选来源。将特征贡献、价格和排除原因提供给展示层，可生成可核查的选餐理由。
如接入大语言模型润色辩论文案，生成文本不得改变预算/过敏原判断，也不能虚构菜品营养、成分或健康功效。本仓库不包含外部大模型 API 密钥或实际调用。
