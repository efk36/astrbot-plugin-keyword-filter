import re

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

# 匹配前统一剔除的字符：空白 + 常见分隔/替换符。
# 目的是让「色 情」「色-情」「ｃolor」这类绕过写法落回同一个词。
_SEPARATORS = re.compile(r"[\s\-_·.,，。、~～!！?？*+/\\|]+")

# 全角 -> 半角，覆盖 ａ-ｚ 0-9 以及部分常见符号
_FULLWIDTH_OFFSET = 0xFEE0


def _normalize(text: str, ignore_separators: bool) -> str:
    """把文本归一化，降低绕过手法的成功率。"""
    if not text:
        return ""
    # 全角转半角
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:  # 全角空格
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - _FULLWIDTH_OFFSET))
        else:
            out.append(ch)
    normalized = "".join(out).lower()
    if ignore_separators:
        normalized = _SEPARATORS.sub("", normalized)
    return normalized


class KeywordFilterPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    # ---------- 配置读取 ----------

    def _keywords(self) -> list[str]:
        return [str(k) for k in (self.config.get("block_keywords") or []) if str(k).strip()]

    def _ignore_separators(self) -> bool:
        return bool(self.config.get("ignore_separators", True))

    def _bypass_user_ids(self) -> set[str]:
        return {str(u).strip() for u in (self.config.get("bypass_user_ids") or []) if str(u).strip()}

    def _bypass_group_ids(self) -> set[str]:
        return {str(g).strip() for g in (self.config.get("bypass_group_ids") or []) if str(g).strip()}

    # ---------- 豁免判断 ----------

    def _is_exempt(self, event: AstrMessageEvent) -> bool:
        """管理员和显式白名单不受屏蔽影响。"""
        try:
            if event.is_admin():
                return True
        except Exception:  # 个别平台可能不提供 role
            pass
        if event.get_sender_id() in self._bypass_user_ids():
            return True
        group_id = event.get_group_id()
        if group_id and group_id in self._bypass_group_ids():
            return True
        return False

    # ---------- 匹配 ----------

    def _find_hit(self, text: str) -> str | None:
        """返回第一个命中的屏蔽词，未命中返回 None。"""
        normalized = _normalize(text, self._ignore_separators())
        for keyword in self._keywords():
            needle = _normalize(keyword, self._ignore_separators())
            if needle and needle in normalized:
                return keyword
        return None

    # ---------- 拦截入口 ----------

    @filter.on_waiting_llm_request()
    async def on_waiting_llm(self, event: AstrMessageEvent) -> None:
        """在调用 LLM 之前拦截，命中则终止本次对话。"""
        if not self.config.get("enabled", True):
            return
        if self._is_exempt(event):
            return

        hit = self._find_hit(event.message_str or "")
        if hit is None:
            return

        if self.config.get("log_hit", True):
            logger.warning(
                "[keyword_filter] blocked sender=%s group=%s hit=%s",
                event.get_sender_id(),
                event.get_group_id() or "-",
                hit,
            )

        action = self.config.get("block_action", {}) or {}
        if action.get("reply", True):
            text = action.get("reply_text") or "这个话题就不聊了，换一个吧。"
            # send() 只接受 MessageChain，直接传字符串会在平台适配器里报
            # AttributeError: 'str' object has no attribute 'chain'
            await event.send(event.plain_result(text))

        if action.get("stop_event", True):
            event.stop_event()

    @filter.command("屏蔽词")
    async def show_keywords(self, event: AstrMessageEvent):
        """查看当前生效的屏蔽词数量。仅管理员可用。"""
        if not event.is_admin():
            yield event.plain_result("只有管理员可以查看屏蔽词配置。")
            return
        count = len(self._keywords())
        if count == 0:
            yield event.plain_result("当前没有配置任何屏蔽词，插件处于放行状态。")
            return
        yield event.plain_result(f"当前生效 {count} 个屏蔽词，请在 WebUI 插件配置中查看具体内容。")
