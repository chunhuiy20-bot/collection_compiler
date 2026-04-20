from ollama import chat
# pip install ollama
# 1) 纯文本
resp = chat(
    model='qwen2.5vl:7b',
    messages=[{'role': 'user', 'content': '你好，做个自我介绍'}]
)
print(resp['message']['content'])

# 2) 图像理解/OCR
img_path = '/Users/hdd/Desktop/python-code/墨以数字/collection_compiler_backend/test/08A00101A18I05B10811F53065.jpg'  # 用绝对路径
resp = chat(
    model='qwen2.5vl:7b',
    messages=[{
        'role': 'user',
        'content': '图中是什么？',
        'images': [img_path]
    }]
)
print(resp['message']['content'])
