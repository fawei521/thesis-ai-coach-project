# 维护档案（git 追踪，不进发布包）

这里放**记账类文档的历史正文**：版本史的早期详情、PROJECT_PLAN 的逐版叙事、e2e 用例台账的老用例。

- **为什么单独一个目录**：`DEVELOPMENT.md` 定死“逐版变更只有 `CHANGELOG.md` 一个来源”，而学生包不该背着
  逐年累积的记账本跑（v1.82 时 CHANGELOG 154KB + PROJECT_PLAN 69KB + e2e-test 117KB，多数内容 AI 一辈子读不到一次）。
  所以正文移到这里、`.gitattributes` 用 `export-ignore` 把它排除在 `git archive` 之外——
  **git 里一行没少，包里不再携带**，两件事同时成立。
- **留在包内的部分**：`CHANGELOG.md` 保留全量版本索引表 + 近期详情；`PROJECT_PLAN.md` 只留定位/架构/清单/规格；
  `tests/e2e-test.md` 保留全量编号索引 + 近期用例。三处都写着“更早的正文在维护档案”的指针。
- **规矩**：这里的内容是历史快照，只进不改；不参与 `consistency_check`（不是给学生的口径）与 `size_ratchet`
  （档案本性就长）。用例编号是跨文档锚点，搬动时编号体系一律不动。
