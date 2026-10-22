"""应用配置模块。

所有可变配置统一从环境变量 / .env 读取，禁止在代码中硬编码密钥。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# 中文友好的递归切分分隔符（从粗到细，最后允许按字符切分）
CHUNK_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", " ", ""]


class Settings(BaseSettings):
    """项目配置项，字段与 .env.example 一一对应。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用基础信息
    app_name: str = "企业客服知识库系统"
    secret_key: str = "dev-only-secret-key-please-change"
    access_token_expire_minutes: int = 1440

    # 数据库
    database_url: str = "sqlite:///./data/app.db"

    # 大模型（DeepSeek，OpenAI 兼容协议）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 向量化（可选通义，默认本地 bge）
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    # 文件与检索参数
    upload_dir: str = "./data/uploads"
    vector_store_dir: str = "./data/vector_store"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 4

    @property
    def is_sqlite(self) -> bool:
        """当前是否使用 SQLite（开发环境默认）。"""
        return self.database_url.startswith("sqlite")

    @property
    def llm_configured(self) -> bool:
        """是否已配置大模型密钥。"""
        return bool(self.deepseek_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局唯一配置实例（带缓存，避免重复解析 .env）。"""
    return Settings()
