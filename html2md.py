# 本脚本用于将 html 文件转换为 markdown 格式的文件

import os
import html2text
import argparse

def convert_html_to_markdown(input_file, output_file):
    """
    将HTML文件转换为Markdown格式
    
    Args:
        input_file (str): HTML文件的路径
        output_file (str): 输出Markdown文件的路径
    """
    # 创建html2text转换器
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_tables = False
    
    # 读取HTML文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"读取HTML文件时出错: {e}")
        return False
        
    # 转换为Markdown
    markdown_content = converter.handle(html_content)
    
    # 写入Markdown文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"成功将 {input_file} 转换为 {output_file}")
        return True
    except Exception as e:
        print(f"写入Markdown文件时出错: {e}")
        return False

def batch_convert(input_folder, output_folder):
    """
    批量转换文件夹中的所有HTML文件为Markdown格式
    
    Args:
        input_folder (str): 输入HTML文件夹路径
        output_folder (str): 输出Markdown文件夹路径
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 获取所有HTML文件
    html_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    success_count = 0
    existing_names = set()
    
    for html_file in html_files:
        input_path = html_file
        # 使用最后一层目录名作为文件名
        dir_name = os.path.basename(os.path.dirname(html_file))
        output_filename = f"{dir_name}.md"
        counter = 1
        
        # 如果文件名已存在,添加数字后缀
        while output_filename in existing_names:
            output_filename = f"{dir_name}_{counter}.md"
            counter += 1
            
        existing_names.add(output_filename)
        output_path = os.path.join(output_folder, output_filename)
        
        if convert_html_to_markdown(input_path, output_path):
            success_count += 1
            
    print(f"转换完成！成功转换 {success_count}/{len(html_files)} 个文件。")

if __name__ == "__main__":
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='将HTML文件或目录转换为Markdown格式')
    parser.add_argument('input', help='输入的HTML文件路径或目录路径')
    parser.add_argument('output', help='输出的Markdown文件路径或目录路径')
    
    args = parser.parse_args()
    
    # 判断输入是文件还是目录
    if os.path.isfile(args.input):
        # 如果输入是文件，直接转换单个文件
        if os.path.isdir(args.output):
            # 如果输出是目录，使用原文件名
            output_file = os.path.join(args.output, 
                os.path.splitext(os.path.basename(args.input))[0] + '.md')
        else:
            output_file = args.output
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        if convert_html_to_markdown(args.input, output_file):
            print("文件转换成功！")
        else:
            print("文件转换失败！")
    else:
        # 如果输入是目录，使用批量转换
        batch_convert(args.input, args.output)
