"""自定义异常类和统一错误处理"""
import logging
import sys

# ============= 日志配置 =============

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str = "INFO"):
    """初始化全局日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("writer")


# ============= 自定义异常 =============

class AppError(Exception):
    """应用基础异常"""
    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class LLMError(AppError):
    """LLM 调用异常"""
    def __init__(self, message: str = "AI服务暂时不可用", detail: str = ""):
        super().__init__(message, status_code=503, detail=detail)


class FileValidationError(AppError):
    """文件校验异常"""
    def __init__(self, message: str = "文件校验失败", detail: str = ""):
        super().__init__(message, status_code=400, detail=detail)


class OpenVikingError(AppError):
    """OpenViking 服务异常"""
    def __init__(self, message: str = "上下文服务暂时不可用", detail: str = ""):
        super().__init__(message, status_code=503, detail=detail)


class DocxGenerationError(AppError):
    """文档生成异常"""
    def __init__(self, message: str = "文档生成失败", detail: str = ""):
        super().__init__(message, status_code=500, detail=detail)
