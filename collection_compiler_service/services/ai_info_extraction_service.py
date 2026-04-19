import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from collection_compiler_service.config.ServiceConfig import get_service_config

logger = logging.getLogger("collection_compiler_service")


class ExtractedInfo(BaseModel):
    """提取的个人信息"""
    name: Optional[str] = Field(None, description="人名")
    household_address: Optional[str] = Field(None, description="户籍地完整地址")
    province: Optional[str] = Field(None, description="户籍地省份")
    city: Optional[str] = Field(None, description="户籍地城市")


class AiInfoExtractionService:
    """使用 OpenAI API 提取 OCR 文本中的关键信息"""

    def __init__(self):
        config = get_service_config()
        self.client = AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
        self.model = config.openai_model

    async def extract_info(self, ocr_text: str) -> ExtractedInfo:
        """
        从 OCR 文本中提取人名、户籍地、省份、城市

        Args:
            ocr_text: OCR 识别的文本内容

        Returns:
            ExtractedInfo: 提取的信息对象
        """
        try:
            prompt = f"""请从以下 OCR 识别的文本中提取以下信息：
1. 人名
2. 户籍地（完整地址）
3. 户籍地的省份
4. 户籍地的市

OCR 文本：
{ocr_text}

请以 JSON 格式返回，格式如下：
{{
    "name": "张三",
    "household_address": "广东省深圳市南山区某某街道",
    "province": "广东省",
    "city": "深圳市"
}}

如果某个字段无法提取，请返回 null。"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的信息提取助手，擅长从文本中提取结构化信息。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            content = response.choices[0].message.content
            if not content:
                logger.warning("AI 返回空内容")
                return ExtractedInfo()

            import json
            data = json.loads(content)
            return ExtractedInfo(**data)

        except Exception as e:
            logger.error(f"AI 信息提取失败: {e}")
            return ExtractedInfo()

    async def extract_info_from_case(self, case_result: dict) -> dict:
        """
        从案件的所有 OCR 文件中提取信息（异步并发）

        Args:
            case_result: 包含 files 列表的案件结果

        Returns:
            dict: 包含提取信息的字典
        """
        files = case_result.get("files", [])
        if not files:
            return {}

        # 合并所有文件的 OCR 文本
        all_text = "\n\n".join(f.get("ocr_text", "") for f in files)

        # 调用 AI 提取信息
        extracted = await self.extract_info(all_text)

        return {
            "name": extracted.name,
            "household_address": extracted.household_address,
            "province": extracted.province,
            "city": extracted.city
        }


ai_info_extraction_service = AiInfoExtractionService()