import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collection_compiler_service.services.multimodal_service import multimodal_service

test_dir = Path(__file__).parent
images = [str(p) for p in test_dir.glob('*.jpg')] + [str(p) for p in test_dir.glob('*.png')]

result = asyncio.run(multimodal_service.extract_id_card_info(images))
print(result)
