# astrbot_plugin_keyword_filter

AstrBot 插件：对话输入的敏感词过滤。在调用 LLM 之前检查用户消息，命中屏蔽词则终止本次对话并回复提示语。管理员和显式白名单不受影响。

## 安装

**方式一：WebUI 插件市场**

在 AstrBot WebUI 的插件市场搜索「关键词屏蔽」安装。

**方式二：下载 ZIP 直接用**

[astrbot_plugin_keyword_filter_v1.0.1.zip](https://github.com/efk36/astrbot-plugin-keyword-filter/releases/download/v1.0.1/astrbot_plugin_keyword_filter_v1.0.1.zip)

下载后解压，把 `astrbot_plugin_keyword_filter` 目录放进 AstrBot 的 `data/plugins/` 下，重启 AstrBot。

**方式三：从仓库安装**

```bash
cd /AstrBot/data/plugins
git clone https://github.com/efk36/astrbot-plugin-keyword-filter.git
```

`metadata.yaml` 在仓库根目录，重启 AstrBot 后生效。

## 功能

- 多关键词屏蔽，命中任意一个即拦截
- 匹配前做文本归一化，忽略大小写、全角/半角差异，以及空格和常见分隔符（`色 情`、`色-情`、`ｃolor` 都视为同一个词）
- 支持按 QQ 号和按群号豁免
- 可配置是否终止对话、是否回复提示语、提示语内容
- 命中时在日志中记录发送者、群号和命中的词
- `/屏蔽词` 命令：管理员查看当前生效的屏蔽词数量

## 配置

在 AstrBot WebUI 的插件配置页面设置：

| 配置项 | 类型 | 说明 |
|---|---|---|
| `enabled` | bool | 是否启用拦截 |
| `block_keywords` | list | 屏蔽词列表 |
| `bypass_user_ids` | list | 豁免 QQ 号（管理员已自动豁免） |
| `bypass_group_ids` | list | 豁免群号，填了整群放行 |
| `ignore_separators` | bool | 匹配时是否忽略分隔符 |
| `block_action.stop_event` | bool | 命中后是否终止对话 |
| `block_action.reply` | bool | 命中后是否回复提示 |
| `block_action.reply_text` | text | 提示语 |
| `log_hit` | bool | 是否记录命中日志 |

## 更新日志

### 1.0.1

修复命中提示发送失败的问题。`event.send()` 只接受 `MessageChain`，此前直接传字符串会在 aiocqhttp 平台适配器里抛 `AttributeError: 'str' object has no attribute 'chain'`。改为 `event.send(event.plain_result(text))`。

## 兼容性

需要 AstrBot >= 4.0.0。在 aiocqhttp (OneBot v11) 平台上测试通过。