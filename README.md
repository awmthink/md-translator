# md-translator

Using LLM as a translator for markdown files

## Requirements

- Python 3.10+
- html2text
- tqdm
- OpenAI python SDK
- OpenAI / Doubao API key

## Usage

### HTML to Markdown Conversion

Convert HTML files to Markdown format:

```bash
python html2md.py <input> <output>
```

Options:
- `<input>`: Path to HTML file or directory containing HTML files
- `<output>`: Path to output Markdown file or directory

Examples:
```bash
# Convert a single HTML file
python html2md.py input.html output.md

# Convert all HTML files in a directory
python html2md.py ./html_files ./markdown_files
```

### Markdown Translation

Translate English Markdown files to Chinese:

```bash
python translate_md.py <input> <output> [--api-key API_KEY]
```

Options:
- `<input>`: Path to Markdown file or directory containing Markdown files
- `<output>`: Path to output translated file or directory
- `--api-key`: Optional OpenAI API key (can also be set via ARK_API_KEY environment variable)

Examples:
```bash
# Translate a single file
python translate_md.py input.md output.md

# Translate all Markdown files in a directory
python translate_md.py ./english_docs ./chinese_docs

# Specify API key
python translate_md.py input.md output.md --api-key your_api_key
```
