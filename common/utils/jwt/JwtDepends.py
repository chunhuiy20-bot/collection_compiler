"""
文件名: JwtDepends.py
作者: yangchunhui
创建日期: 2026/2/25
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/25
描述: FastAPI JWT 依赖注入工厂，生成可直接用于路由 Depends 的鉴权依赖函数。
      设计为通用工厂，传入 JwtHandler 实例即可生成对应的依赖函数，适配任意项目。

修改历史:
2026/2/25 - yangchunhui - 初始版本

依赖:
- fastapi: FastAPI 框架
- JwtHandler: JWT 处理器
- JwtPayload: Payload 数据模型

使用示例:
    # 1. 在项目中初始化
    from common.utils.jwt.JwtConfig import JwtConfig
    from common.utils.jwt.JwtHandler import JwtHandler
    from common.utils.jwt.JwtDepends import make_jwt_depends

    jwt_handler = JwtHandler(JwtConfig(secret_key="your-secret"))
    get_current_user = make_jwt_depends(jwt_handler)

    # 2. 在路由中使用
    from fastapi import Depends
    from common.utils.jwt.JwtPayload import JwtPayload

    @router.get("/profile")
    async def get_profile(current_user: JwtPayload = Depends(get_current_user)):
        return {"user_id": current_user.sub}
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from common.utils.jwt.JwtHandler import JwtHandler, TokenExpiredError, TokenInvalidError
from common.utils.jwt.JwtPayload import JwtPayload

_bearer_scheme = HTTPBearer()


def make_jwt_depends(jwt_handler: JwtHandler):
    """
    方法说明: 生成 FastAPI JWT 鉴权依赖函数
    作者: yangchunhui
    创建时间: 2026/2/25
    修改历史:
    2026/2/25 - yangchunhui - 初始版本

    Args:
        jwt_handler: JwtHandler 实例

    Returns:
        可用于 Depends() 的异步依赖函数，解析成功返回 JwtPayload

    Example:
        get_current_user = make_jwt_depends(jwt_handler)

        @router.get("/me")
        async def me(current_user: JwtPayload = Depends(get_current_user)):
            return current_user.sub
    """
    async def _get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    ) -> JwtPayload:
        try:
            return jwt_handler.decode_token(credentials.credentials, expected_type="access")
        except TokenExpiredError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已过期")
        except TokenInvalidError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效")

    return _get_current_user
