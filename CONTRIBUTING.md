# Contributing

1. 从 `main` 创建短分支。
2. 修改模型行为时同步更新测试和 `MODEL_CARD.md`。
3. 运行 `python -m unittest discover -s tests -v` 和 `python -m foodarena.predict`。
4. 不得提交真实用户偏好、凭据、日志或其他个人信息。
5. Pull Request 说明问题、行为变化、验证方法和模型/数据风险。

涉及过敏原硬约束的改动必须包含失败关闭（fail closed）的测试；无匹配时不得静默放宽约束。
