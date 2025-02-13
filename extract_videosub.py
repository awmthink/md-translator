import yt_dlp
import whisper
import os
import torch
import hashlib
import argparse
import signal
import sys

from llm_client import LLMClient


def download_audio(url, cache_dir=".audio_cache"):
    """从视频链接下载音频，如果已存在则直接返回

    Args:
        url: 视频URL
    """
    # 为URL创建唯一的缓存目录
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_dir = os.path.join(cache_dir, url_hash)
    os.makedirs(cache_dir, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": os.path.join(cache_dir, "%(title)s.%(ext)s"),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # 获取视频信息
                info = ydl.extract_info(url, download=True)
                audio_file = os.path.join(cache_dir, f"{info['title']}.mp3")
                return audio_file
            except Exception as e:
                print(f"下载音频时出错: {str(e)}")
                return None
    except KeyboardInterrupt:
        print("\n下载被用户中断")
        raise
    except Exception as e:
        print(f"下载音频时出错: {str(e)}")
        return None


def generate_subtitle(audio_path, output_path="subtitle.srt"):
    """使用whisper生成字幕，自动检测语言，流式输出"""
    try:
        # 加载whisper模型，优先使用GPU
        model = whisper.load_model(
            "turbo", device="cuda" if torch.cuda.is_available() else "cpu"
        )

        # 打开输出文件
        with open(output_path, "w", encoding="utf-8") as f:
            # 使用流式转录
            print("开始转录音频...")
            result = model.transcribe(audio_path, verbose=True)

            # 实时写入字幕
            for i, segment in enumerate(result["segments"], 1):
                start_time = format_timestamp(segment["start"])
                end_time = format_timestamp(segment["end"])
                text = segment["text"].strip()

                # 写入当前片段
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

            print("\n转录完成!")
        return output_path

    except KeyboardInterrupt:
        print("\n转录被用户中断")
        raise
    except Exception as e:
        print(f"生成字幕时出错: {str(e)}")
        return None


def format_timestamp(seconds):
    """将秒数转换为srt时间戳格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"


def generate_notes(subtitle_path: str, api_key: str = None) -> str:
    """将字幕转换为笔记文章"""
    llm_client = LLMClient(api_key=api_key)

    # 读取字幕文件
    with open(subtitle_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 获取视频总时长
    total_duration = 0
    for line in content.split("\n"):
        if " --> " in line:
            time_str = line.split(" --> ")[1]  # 使用结束时间
            hours, minutes, seconds = time_str.split(":")
            total_seconds = (
                int(hours) * 3600 + int(minutes) * 60 + float(seconds.replace(",", "."))
            )
            total_duration = max(total_duration, total_seconds)

    # 如果视频时长小于60分钟，不进行切片
    if total_duration < 3600:  # 3600秒 = 60分钟
        segments = [
            "\n".join(
                [
                    line
                    for line in content.split("\n")
                    if line.strip()
                    and not line.strip().isdigit()
                    and " --> " not in line
                ]
            )
        ]
    else:
        # 按60分钟进行切片
        segments = []
        current_segment = []
        current_time = 0

        for line in content.split("\n"):
            if " --> " in line:
                time_str = line.split(" --> ")[0]
                hours, minutes, seconds = time_str.split(":")
                total_seconds = (
                    int(hours) * 3600
                    + int(minutes) * 60
                    + float(seconds.replace(",", "."))
                )

                if total_seconds - current_time > 3600:  # 60分钟
                    if current_segment:
                        segments.append("\n".join(current_segment))
                    current_segment = []
                    current_time = total_seconds
            elif line.strip() and not line.strip().isdigit():
                current_segment.append(line)

        if current_segment:
            segments.append("\n".join(current_segment))

    # 对每个分段进行润色和修正
    notes_sections = []
    total_stats = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "prompt_cost": 0,
        "completion_cost": 0,
        "total_cost": 0,
    }

    for i, segment in enumerate(segments):
        prompt = f"""请将以下视频字幕内容润色为一段流畅的笔记文章。在润色过程中：
1. 修正可能的错别字和语法错误
2. 调整语序使内容更加连贯
3. 保持专业术语的准确性
4. 添加适当的段落划分
5. 确保文章结构清晰

原始字幕内容：
{segment}"""

        try:
            note_section, usage_stats = llm_client.generate_completion(
                prompt=prompt,
                system_prompt="你是一个专业的内容编辑，擅长将口语内容转换为书面语。",
            )
            if note_section and usage_stats:
                notes_sections.append(f"## 第{i+1}部分\n\n{note_section}")
                for key in total_stats:
                    total_stats[key] += usage_stats[key]
                print(f"第{i+1}部分处理完成:")
                print(llm_client.format_usage_stats(usage_stats))
        except Exception as e:
            print(f"生成笔记时出错: {e}")
            notes_sections.append(f"## 第{i+1}部分\n\n处理失败")

    # 生成完整文章
    final_prompt = f"""请基于以下分段内容，生成一篇完整的文章。要求：
1. 添加合适的标题
2. 优化整体结构
3. 确保各部分之间的过渡自然
4. 添加简要的导言和总结

文章内容：
{''.join(notes_sections)}"""

    try:
        final_article, final_usage = llm_client.generate_completion(
            prompt=final_prompt,
            system_prompt="你是一个专业的文章编辑，擅长组织和优化长篇文章。",
        )

        if final_article and final_usage:
            for key in total_stats:
                total_stats[key] += final_usage[key]

            print("\n最终文章生成完成:")
            print(llm_client.format_usage_stats(final_usage))
            print("\n总计使用统计:")
            print(llm_client.format_usage_stats(total_stats))

            return "\n\n".join(
                [final_article, "\n---\n", llm_client.format_usage_stats(total_stats)]
            )
    except Exception as e:
        print(f"生成最终文章时出错: {e}")
        return "\n\n".join(notes_sections)


def extract_subtitle(video_url):
    """主函数：从视频提取字幕

    Args:
        video_url: 视频URL
    """
    # 下载音频
    audio_file = download_audio(video_url)
    if not audio_file:
        return None

    # 根据音频文件名生成对应的字幕文件名
    base_name = os.path.splitext(audio_file)[0]
    subtitle_path = f"{base_name}.srt"

    # 生成字幕
    subtitle_file = generate_subtitle(audio_file, subtitle_path)
    if not subtitle_file:
        return None

    # 生成笔记
    notes = generate_notes(subtitle_file)
    if notes:
        notes_file = f"{base_name}_notes.md"
        with open(notes_file, "w", encoding="utf-8") as f:
            f.write(notes)
        print(f"笔记文件已生成: {notes_file}")

    return subtitle_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从视频提取字幕并生成笔记")
    parser.add_argument("url", help="视频URL")

    args = parser.parse_args()
    result = extract_subtitle(args.url)

    if result:
        print(f"字幕文件已生成: {result}")
    else:
        print("字幕提取失败")
