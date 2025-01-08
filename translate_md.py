import os
import re
from openai import OpenAI
from typing import List, Tuple
from tqdm import tqdm
import argparse

class MarkdownTranslator:
    def __init__(self, api_key: str = None):
        """初始化翻译器"""
        self.client = OpenAI(
            api_key=api_key or os.environ.get("ARK_API_KEY"),
            base_url="https://ark.cn-beijing.volces.com/api/v3",
        )
        self.max_chunk_size = 8192
        # 价格配置 (RMB /1K token)
        self.input_price = 0.0008  
        self.output_price = 0.002
        
    def split_markdown(self, content: str) -> List[Tuple[str, str, int]]:
        """
        将markdown内容按标题层级切分成块
        返回: List[Tuple[标题层级, 内容块, 原始位置]]
        """
        # 按h1/h2/h3分割
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_level = None
        current_pos = 0
        
        for i, line in enumerate(lines):
            header_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            
            if header_match:
                # 保存之前的chunk
                if current_chunk:
                    chunks.append((current_level, '\n'.join(current_chunk), current_pos))
                
                current_level = len(header_match.group(1))
                current_chunk = [line]
                current_pos = i
            else:
                current_chunk.append(line)
                
        # 添加最后一个chunk
        if current_chunk:
            chunks.append((current_level, '\n'.join(current_chunk), current_pos))
            
        # 检查chunk大小,如果超过限制则继续分割
        final_chunks = []
        for level, content, pos in chunks:
            if len(content) > self.max_chunk_size:
                sub_chunks = self._split_large_chunk(content)
                for sub_pos, sub_content in enumerate(sub_chunks):
                    final_chunks.append((level, sub_content, pos + sub_pos))
            else:
                final_chunks.append((level, content, pos))
                
        return final_chunks
    
    def _split_large_chunk(self, content: str) -> List[str]:
        """将大块内容按段落切分"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in content.split('\n\n'):
            if current_size + len(paragraph) > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_size += len(paragraph)
                
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            
        return chunks
    
    def translate_chunk(self, content: str) -> Tuple[str, int, int]:
        """调用OpenAI API翻译内容块"""
        prompt = f"""请将以下Markdown格式的英文内容翻译成中文，保持原有的Markdown格式和标记不变：

{content}

翻译要求：
1. 保持所有Markdown语法标记不变
2. 保持所有链接、图片引用等格式不变
3. 保持代码块内容不变
4. 翻译要准确、通顺、专业"""

        try:
            completion = self.client.chat.completions.create(
                model="ep-20250108123948-xc8vl",
                messages=[
                    {"role": "system", "content": "你是一个专业的技术文档翻译助手。"},
                    {"role": "user", "content": prompt}
                ],
            )
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            return completion.choices[0].message.content, prompt_tokens, completion_tokens
        except Exception as e:
            print(f"翻译出错: {e}")
            return content, 0, 0
            
    def translate_file(self, input_file: str, output_file: str):
        """翻译整个Markdown文件"""
        # 读取文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 分割内容
        chunks = self.split_markdown(content)
        
        # 翻译每个块
        translated_chunks = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        # 使用tqdm创建进度条
        pbar = tqdm(sorted(chunks, key=lambda x: x[2]), 
                   desc=f"翻译文件: {os.path.basename(input_file)}", 
                   unit="chunk")
        
        for level, chunk_content, pos in pbar:
            translated, prompt_tokens, completion_tokens = self.translate_chunk(chunk_content)
            translated_chunks.append(translated)
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            
            # 计算当前花费
            prompt_cost = (total_prompt_tokens / 1000) * self.input_price
            completion_cost = (total_completion_tokens / 1000) * self.output_price
            total_cost = prompt_cost + completion_cost
            
            pbar.set_postfix({
                'input_tokens': total_prompt_tokens,
                'output_tokens': total_completion_tokens,
                'cost': f'¥{total_cost:.4f}'
            })
            
        # 合并翻译结果
        final_content = '\n'.join(translated_chunks)
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        return total_prompt_tokens, total_completion_tokens
            
def translate_markdown_files(input_folder: str, output_folder: str, api_key: str):
    """批量翻译文件夹中的markdown文件"""
    translator = MarkdownTranslator(api_key)
    
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = [f for f in os.listdir(input_folder) if f.endswith('.md')]
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    # 使用tqdm创建进度条
    for file in tqdm(md_files, desc="翻译进度", unit="file"):
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, f"zh_{file}")
        
        prompt_tokens, completion_tokens = translator.translate_file(input_path, output_path)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens

    # 计算总花费
    prompt_cost = (total_prompt_tokens / 1000) * translator.input_price
    completion_cost = (total_completion_tokens / 1000) * translator.output_price
    total_cost = prompt_cost + completion_cost

    print(f"\n翻译完成!")
    print(f"输入token数: {total_prompt_tokens:,}")
    print(f"输出token数: {total_completion_tokens:,}")
    print(f"输入token费用: ¥{prompt_cost:.4f}")
    print(f"输出token费用: ¥{completion_cost:.4f}")
    print(f"总费用: ${total_cost:.4f}")

if __name__ == "__main__":
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='将英文Markdown文件翻译为中文')
    parser.add_argument('input', help='输入的Markdown文件路径或目录路径')
    parser.add_argument('output', help='输出的Markdown文件路径或目录路径')
    parser.add_argument('--api-key', help='OpenAI API密钥', default=None)
    
    args = parser.parse_args()
    
    # 判断输入是文件还是目录
    if os.path.isfile(args.input):
        # 如果输入是文件，直接翻译单个文件
        translator = MarkdownTranslator(args.api_key)
        
        if os.path.isdir(args.output):
            # 如果输出是目录，使用原文件名加前缀
            output_file = os.path.join(args.output, 
                f"zh_{os.path.basename(args.input)}")
        else:
            output_file = args.output
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 翻译文件
        prompt_tokens, completion_tokens = translator.translate_file(args.input, output_file)
        
        # 计算花费
        prompt_cost = (prompt_tokens / 1000) * translator.input_price
        completion_cost = (completion_tokens / 1000) * translator.output_price
        total_cost = prompt_cost + completion_cost
        
        print(f"\n翻译完成!")
        print(f"输入token数: {prompt_tokens:,}")
        print(f"输出token数: {completion_tokens:,}")
        print(f"总费用: ¥{total_cost:.4f}")
    else:
        # 如果输入是目录，使用批量翻译
        translate_markdown_files(args.input, args.output, args.api_key)
