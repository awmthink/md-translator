import yt_dlp
import whisper
import os
import torch
import hashlib

def download_audio(url, output_path="temp_audio.mp3"):
    """从视频链接下载音频，如果已存在则直接返回"""
    # 为URL创建唯一的缓存目录
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_dir = os.path.join("audio_cache", url_hash)
    os.makedirs(cache_dir, exist_ok=True)
    
    output_path = os.path.join(cache_dir, "audio.mp3")
    
    # 检查音频文件是否已存在
    if os.path.exists(output_path):
        print(f"音频文件已存在: {output_path}")
        return output_path
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path.replace('.mp3', ''),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return output_path
        except Exception as e:
            print(f"下载音频时出错: {str(e)}")
            return None

def generate_subtitle(audio_path, output_path="subtitle.srt"):
    """使用whisper生成字幕，自动检测语言，流式输出"""
    try:
        # 加载whisper模型，优先使用GPU
        model = whisper.load_model("turbo", device="cuda" if torch.cuda.is_available() else "cpu")
        
        # 打开输出文件
        with open(output_path, 'w', encoding='utf-8') as f:
            # 使用流式转录
            print("开始转录音频...")
            segments = []
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
                
                # 实时显示进度
                progress = (segment["end"] / result["segments"][-1]["end"]) * 100
                print(f"\r转录进度: {progress:.1f}%", end="", flush=True)
                
            print("\n转录完成!")
        return output_path
        
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

def extract_subtitle(video_url, audio_path="temp_audio.mp3", subtitle_path="subtitle.srt"):
    """主函数：从视频提取字幕"""
    # 下载音频
    audio_file = download_audio(video_url)
    if not audio_file:
        return None
    
    # 生成字幕
    subtitle_file = generate_subtitle(audio_file, subtitle_path)
    
    return subtitle_file

if __name__ == "__main__":
    # 示例使用
    video_url = input("请输入视频URL: ")
    result = extract_subtitle(video_url)
    if result:
        print(f"字幕文件已生成: {result}")
    else:
        print("字幕提取失败")
