# 通用辅助脚本

## 快照：保存、校验、恢复

`paper_snapshot.py` 仅使用 Python 标准库，要求 **Python 3.9 或以上、macOS 或 Linux**。不用安装依赖，不执行构建或实验。运行位置不影响项目定位：脚本以自身所在 `scripts/` 的上一级目录为工程根目录，不读取或复制 `project_root` 或 `input_paths` 指向的外部工程。

在工程根目录运行：

```bash
python3 scripts/paper_snapshot.py save --label before-revision --note "本轮修改前"
python3 scripts/paper_snapshot.py verify snapshots/实际快照目录名
python3 scripts/paper_snapshot.py restore snapshots/实际快照目录名 --to /绝对路径/尚不存在的新目录
```

保存前协调其他写入者暂停改文件；保存与 SHA-256 校验成功后再修改。首次准备材料时即使没有论文入口或模板也能保存，只需存在合法的 `project.json`。快照保存在 `snapshots/时间戳_阶段名/`，其中 `project/` 保存文件，`snapshot.json` 记录文件清单、SHA-256、大小、备注和已有成品信息。旧快照不可编辑或覆盖。

## 配置与归档范围

在 `project.json` 中填写：

- `output_paths.paper`、`output_paths.review`、`output_paths.build`：工程内相对目录；省略或为 `null` 时分别使用 `paper`、`review`、`build`。
- `manuscript.entrypoint`、`manuscript.template_path`：稿件入口及模板位置；未接入时可为 `null`。脚本不依赖稿件格式或扩展名。
- `manuscript.expected_output`：希望保存的单个成品文件，使用**相对于工程根目录**的路径，例如 `build/submission.pdf`、`exports/final/article.docx`；未接入时为 `null`。文件尚未生成时仍保存材料。它不是相对于构建目录的路径。

`format`、`template_source_url`、`requirements_url`、`build_command` 可为 `null`，不影响快照。脚本不会执行 `build_command`。相对的 `project_root: "."` 可随整个工程迁移；快照记录原始位置仅用于追溯，不会因此返回原目录读文件。

脚本保存工程内的普通材料文件，包含后续作者自行接入的模板、稿件、图稿、引用、证据、审稿和流程文件。**配置的构建目录只保存 `expected_output` 指向的已有文件**，其余构建内容视为缓存，不归档。构建目录必须专用于产物，不能与 `paper`、`review`、`inputs`、`delivery`、稿件入口、模板或通用材料目录重叠（包含同名、祖先或子目录）；脚本会拒绝这些容易漏收源文件的配置。作者原始材料和交付备份因此不会被误当作构建缓存排除。需要长期保留的日志或其他成品，请放入构建目录外的普通材料目录。

例如 `output_paths.build` 为 `exports`、`expected_output` 为 `exports/final/article.docx` 时，只收录该 DOCX；不要求任何 `.tex` 或固定的 PDF 文件名。成品路径在构建目录以外时也会照常记录。已有成品不保证对应当前源码；需要保存可阅读的完整版本时先完成项目自己的构建。

脚本校验的 `output_paths` 与 `manuscript` 文件/目录路径必须留在工程内，禁止绝对路径和 `..`。`input_paths` 可以引用外部研究目录，但脚本不读取或复制这些外部内容；来源 URL 也不会被抓取。工程树中的符号链接不会被跟随；被选中的符号链接或特殊文件会使保存失败。脚本会跳过任意层级的 `snapshots/`、`restored/`、Git 元数据、虚拟环境、依赖与常见缓存目录，以及 `.pyc`、`.pyo` 文件。不要将需要保留的材料放在这些保留名称下。

## 校验与恢复边界

保存时先登记文件内容，再复制、检查文件是否变化，并完整校验临时快照后建立新的快照目录；发生文件变动或校验失败会中止。`verify` 检查完整文件清单、文件大小和 SHA-256，可发现丢失、新增和篡改的文件。这是完整性校验，不是防恶意修改清单的数字签名。

恢复会先校验快照，再复制和校验，并要求目标目录的父目录已存在、目标本身不存在、目标位于快照之外；即使空目录也不会覆盖。建议恢复到工程外的独立目录；若放在原工程内，使用 `restored/` 下尚不存在的子目录，避免之后的快照重复收录恢复副本。原工程和旧快照保持原样。恢复后的 `project.json` 内容保持原记录，继续工作前检查其中的外部材料路径。

快照只保存在本机；如需异机备份，可另行复制完整的 `snapshots/` 目录。
