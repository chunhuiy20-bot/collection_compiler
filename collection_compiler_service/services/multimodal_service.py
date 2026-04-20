from ollama import chat


class MultimodalService:

    def __init__(self, model: str = "qwen2.5vl:7b"):
        self._model = model

    async def extract_id_card_info(self, file_paths: list[str]) -> dict:
        """识别多张图片，找出身份证并提取信息"""
        prompt = """请分析这些图片，找出身份证照片，提取以下信息：
- 姓名
- 籍贯（完整地址）
- 籍贯省份
- 籍贯地区

以JSON格式返回：{"name": "...", "household_address": "...", "province": "...", "city": "..."}
如果没有身份证，返回空JSON对象。"""

        resp = chat(
            model=self._model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': file_paths
            }]
        )

        import json
        try:
            return json.loads(resp['message']['content'])
        except:
            return {}


multimodal_service = MultimodalService()
