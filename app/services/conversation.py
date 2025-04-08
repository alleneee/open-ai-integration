"""处理会话历史记录的服务。"""

import json
import logging
from typing import List, Optional

import redis # 导入 redis

from app.core.config import settings
from app.schemas.schemas import Message

logger = logging.getLogger(__name__)

class ConversationService:
    """使用 Redis 管理会话历史记录的服务。"""
    def __init__(self):
        try:
            # 从 settings 中获取 Redis URL
            self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.redis.ping() # 检查连接
            logger.info(f"成功连接到 Redis: {settings.redis_url}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"无法连接到 Redis: {e}")
            # 可以在此处理错误，例如引发异常或使用备用存储
            self.redis = None # 标记为不可用
        except AttributeError:
            logger.error("配置中未找到 redis_url")
            self.redis = None
            
        # 默认会话过期时间（秒），例如 24 小时
        self.ttl = 60 * 60 * 24 

    def _get_key(self, session_id: str) -> str:
        """生成用于 Redis 的键。"""
        return f"conversation:{session_id}"

    def get_history(self, session_id: str) -> List[Message]:
        """从 Redis 检索会话历史记录。"""
        if not self.redis:
            logger.warning("Redis 不可用，无法获取历史记录。")
            return []
            
        try:
            key = self._get_key(session_id)
            data = self.redis.get(key)
            if not data:
                logger.debug(f"会话 {session_id} 没有历史记录。")
                return []
                
            # 解析 JSON 字符串回 Pydantic 模型列表
            history_data = json.loads(data)
            messages = [Message(**msg) for msg in history_data]
            logger.debug(f"成功检索到会话 {session_id} 的 {len(messages)} 条消息。")
            return messages
        except json.JSONDecodeError as e:
            logger.error(f"解析会话 {session_id} 的历史记录时出错: {e}")
            return [] # 返回空列表以避免错误
        except redis.exceptions.RedisError as e:
            logger.error(f"与 Redis 交互时出错 (获取历史记录): {e}")
            return []
        except Exception as e:
            logger.error(f"获取会话 {session_id} 历史记录时发生意外错误: {e}")
            return []

    def add_message(self, session_id: str, message: Message):
        """向会话历史记录添加新消息。"""
        if not self.redis:
            logger.warning("Redis 不可用，无法添加消息。")
            return
            
        try:
            history = self.get_history(session_id) # 获取当前历史
            history.append(message) # 添加新消息
            
            key = self._get_key(session_id)
            # 将 Pydantic 模型列表序列化为 JSON 字符串
            history_json = json.dumps([msg.dict() for msg in history])
            
            # 使用 SETEX 设置键和过期时间
            self.redis.setex(key, self.ttl, history_json)
            logger.debug(f"成功向会话 {session_id} 添加了消息。")
        except redis.exceptions.RedisError as e:
            logger.error(f"与 Redis 交互时出错 (添加消息): {e}")
        except Exception as e:
            logger.error(f"添加消息到会话 {session_id} 时发生意外错误: {e}")

    def clear_history(self, session_id: str):
        """清除特定会话的历史记录。"""
        if not self.redis:
            logger.warning("Redis 不可用，无法清除历史记录。")
            return
            
        try:
            key = self._get_key(session_id)
            deleted_count = self.redis.delete(key)
            if deleted_count > 0:
                logger.info(f"成功清除了会话 {session_id} 的历史记录。")
            else:
                logger.debug(f"尝试清除会话 {session_id} 的历史记录，但未找到该键。")
        except redis.exceptions.RedisError as e:
            logger.error(f"与 Redis 交互时出错 (清除历史记录): {e}")
        except Exception as e:
             logger.error(f"清除会话 {session_id} 历史记录时发生意外错误: {e}")

# 创建服务实例 (可选，可以根据需要创建)
conversation_service = ConversationService() 