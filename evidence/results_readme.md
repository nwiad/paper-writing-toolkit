# 结果数据使用说明

填写状态：待填写。有数值结果的项目应在起草效果陈述前填清；没有数值结果时注明“不适用”并指向实际论据材料。

## 数据与来源

- 数值唯一来源：[RESULT_FILE_OR_NOT_APPLICABLE]（默认可用 `evidence/main_results.csv`）
- 作者原表/原材料位置：[ORIGINAL_SOURCE_LOCATION]
- 表中的一行代表什么：[ROW_DEFINITION]
- 条件、指标和设置 ID 的显示标签：[ID_LABEL_MAPPING]
- 数据版本与作者说明位置：[DATA_VERSION_AND_AUTHOR_SOURCE]

初始 CSV 只有以下中性表头，没有结果。可以换成实际项目需要的结构；所有读表、图表与文字必须遵循修改后的字段定义。

| 初始列 | 待定义的含义 |
|---|---|
| `result_id` | 每条结果的稳定标识 |
| `setting_id` | 数据、样本或研究设置标识 |
| `condition_id` | 所比较的条件/方法/组别标识 |
| `metric` | 指标名称及其完整定义 |
| `value` | 作者提供的显示值，不含虚构或示例结果 |
| `unit` | 单位；比例、百分数等须明确 |
| `split` | 数据划分或评估集合；不适用时明确标注 |
| `statistic` | 显示的统计量；未知不能自行写成均值 |
| `repeat_count` | 与定义对应的真实重复次数；未知不补数字 |
| `source_id` | 对应 `source_map.md` 的来源 ID |

## 统计与测量定义

- 每个比较条件实际评估的对象/终点：[EVALUATED_OBJECTS]
- 指标方向和单位范围：[DIRECTION_AND_UNIT_RANGE]
- 显示统计量及聚合层级：[STATISTIC_AND_AGGREGATION]
- 重复单位与实际次数，是否各单元相同：[REPETITION_UNIT_AND_COVERAGE]
- 缺失值、不适用项和失败如何表示：[MISSINGNESS_AND_FAILURES]
- 舍入及小数位规则：[ROUNDING_RULES]
- 已提供的误差/区间/统计检验及具体来源（若无写“未提供”）：[UNCERTAINTY_AND_TESTS]
- 是否提供成本或过程测量（若无写“未提供”）：[COST_OR_PROCESS_DATA]

## 可支持的写法

- 已有结果直接支持的观察：[SUPPORTED_OBSERVATIONS]
- 未改善、反例和覆盖边界：[EXCEPTIONS_AND_SCOPE]
- 不得据当前材料推出的更强结论：[UNSUPPORTED_CLAIMS]
- 允许的显示转换或派生量（如适用，明确公式与用途）：[AUTHORIZED_TRANSFORMATIONS_OR_NONE]
- 仍需澄清的实质冲突：[CONFLICTS_OR_NONE]

保留作者提供的数值，不自行重跑、挑选或重算。不因表内有数字就推定均值、标准差、显著性、稳定性、因果性或等预算。允许检查表、定义与文字的一致性；矛盾需定位到具体字段。是否追加分析由作者决定，缺失的可选统计信息不自动阻止其他写作。
