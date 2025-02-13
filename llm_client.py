import os
from openai import OpenAI
from typing import Dict, Tuple

# 模型配置
DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "ep-20250213103332-tcdqx"

# 价格配置 (RMB /1K token)
INPUT_PRICE = 0.0008
OUTPUT_PRICE = 0.002


class LLMClient:

    def __init__(
        self,
        api_key: str = None,
        base_url: str = DEFAULT_BASE_URL,
    ):
        """初始化LLM客户端"""
        self.client = OpenAI(
            api_key=api_key or os.environ.get("ARK_API_KEY"),
            base_url=base_url,
        )

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str = None,
        model: str = DEFAULT_MODEL,
    ) -> Tuple[str, Dict]:
        """
        生成LLM补全
        返回: (生成的内容, 使用统计)
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )

            usage_stats = {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
                "prompt_cost": (completion.usage.prompt_tokens / 1000) * INPUT_PRICE,
                "completion_cost": (completion.usage.completion_tokens / 1000)
                * OUTPUT_PRICE,
            }
            usage_stats["total_cost"] = (
                usage_stats["prompt_cost"] + usage_stats["completion_cost"]
            )

            return completion.choices[0].message.content, usage_stats
        except Exception as e:
            print(f"LLM调用出错: {e}")
            return None, None

    def format_usage_stats(self, stats: Dict) -> str:
        """格式化使用统计信息"""
        if not stats:
            return ""

        return f"""
=== Token 使用统计 ===
输入token数: {stats['prompt_tokens']:,}
输出token数: {stats['completion_tokens']:,}
输入token费用: ¥{stats['prompt_cost']:.4f}
输出token费用: ¥{stats['completion_cost']:.4f}
总费用: ¥{stats['total_cost']:.4f}"""
