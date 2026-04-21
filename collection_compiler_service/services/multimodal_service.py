from ollama import chat


class MultimodalService:

    def __init__(self, model: str = "qwen2.5vl:latest"):
        self._model = model

    async def extract_id_card_info(self, file_paths: list[str]) -> dict:
        """识别多张图片，找出身份证并提取信息"""
        import json
        prompt = """
                判断这张图片是否含有居民身份信息，只输出，
                如果没有，输出：不含身份信息，
                如果含有身份信息，按照行政区域划分，输出：|姓名|户籍地|省份（直辖市或自治区）|地级行政区（市、地区或州）
                """

        results = {}
        for file_path in file_paths:
            resp = chat(
                model=self._model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [file_path]
                }]
            )
            results[file_path] = resp.message.content
        return results


multimodal_service = MultimodalService()
