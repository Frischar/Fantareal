# 世界书生成器

一个独立的本地 WebUI 工具，用来把自然语言设定素材整理成 Xuqi 风格的世界书 JSON。

它面向两类使用场景：
- 制作者批量整理人物、地点、势力、规则、历史等设定
- 玩家或写手在现有词条基础上继续微调和扩写

## 启动

直接双击：

- `启动webui.bat`

脚本会自动：

- 检查 Python 版本
- 创建 `.venv`
- 安装依赖
- 在默认浏览器中打开 `http://127.0.0.1:8017`

## 当前功能

- 粘贴长文本设定并调用兼容 OpenAI 风格的接口生成世界书
- 在工作台里继续手工编辑词条
- 重新预览 JSON，不覆盖已有词条，按增量方式继续生成
- 检查词条完整性，方便继续整理
- 自定义界面背景、透明度、覆盖度和模糊强度

## 目录说明

- `app.py`：FastAPI 入口
- `templates/`：页面模板
- `static/`：样式资源
- `data/`：本地配置和工作草稿
- `启动webui.bat`：一键启动脚本

## 手动运行

```powershell
cd "E:\AI chat 项目\Xuqi_LLM\worldbook maker"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 127.0.0.1 --port 8017
```
