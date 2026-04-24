# 世界书生成器

一个给开发者使用的独立 WebUI 工具，用来把原始设定素材整理成 Xuqi 风格世界书 JSON。

## 启动

直接双击：

- `启动webui.bat`

它会自动检查 Python、创建 `.venv`、安装依赖，并在默认浏览器中打开：

- `http://127.0.0.1:8017`

## 当前功能

- 大输入框粘贴原始素材
- 配置云端 API
- 检测 `/models` 和 `chat/completions` 是否可用
- 调用模型生成世界书格式 JSON
- 预览当前词条模块
- 保存当前草稿

## 手动运行

```powershell
cd "E:\AI chat 项目\世界书生成器"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8017
```
