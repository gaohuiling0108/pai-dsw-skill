#!/usr/bin/env python3
"""
Rate Limiter - API 限流处理模块

功能：
- 自动重试机制（指数退避）
- 请求限速（令牌桶算法）
- 限流状态监控
- 可配置的限流策略

Usage:
    from rate_limiter import with_retry, RateLimiter, retry_api_call
    
    # 方式1: 使用装饰器
    @with_retry(max_retries=3, backoff_factor=2.0)
    def my_api_call():
        return client.some_method()
    
    # 方式2: 直接调用
    result = retry_api_call(
        lambda: client.list_instances(request),
        max_retries=3
    )
    
    # 方式3: 使用全局限速器
    limiter = RateLimiter(rate_limit=10, period=1.0)  # 每秒10个请求
    with limiter:
        result = client.some_method()
"""

import time
import random
import functools
import threading
from typing import Callable, Any, Optional, TypeVar, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys

# 类型变量
T = TypeVar('T')


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"           # 固定间隔
    LINEAR = "linear"         # 线性递增
    EXPONENTIAL = "exponential"  # 指数退避（默认）
    JITTERED = "jittered"     # 带抖动的指数退避


@dataclass
class RateLimitConfig:
    """限流配置"""
    # 重试配置
    max_retries: int = 3              # 最大重试次数
    retry_strategy: RetryStrategy = RetryStrategy.JITTERED  # 重试策略
    base_delay: float = 1.0           # 基础延迟（秒）
    max_delay: float = 60.0            # 最大延迟（秒）
    backoff_factor: float = 2.0       # 退避因子
    
    # 限速配置
    rate_limit: int = 20              # 时间窗口内最大请求数
    period: float = 1.0                # 时间窗口（秒）
    
    # 可重试的错误码
    retryable_status_codes: List[int] = field(default_factory=lambda: [
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ])
    
    # 可重试的异常类型
    retryable_exceptions: List[type] = field(default_factory=lambda: [
        ConnectionError,
        TimeoutError,
    ])


@dataclass
class RetryStats:
    """重试统计"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_retries: int = 0
    total_wait_time: float = 0.0
    last_error: Optional[str] = None
    last_retry_time: Optional[datetime] = None


class RateLimiter:
    """
    令牌桶限速器
    
    使用令牌桶算法实现请求限速，支持并发调用。
    """
    
    def __init__(self, rate_limit: int = 20, period: float = 1.0):
        """
        初始化限速器
        
        Args:
            rate_limit: 时间窗口内允许的最大请求数
            period: 时间窗口（秒）
        """
        self.rate_limit = rate_limit
        self.period = period
        self._tokens = rate_limit
        self._last_refill = time.time()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self._last_refill
        if elapsed >= self.period:
            # 按经过的完整周期补充令牌
            periods = int(elapsed / self.period)
            self._tokens = min(self.rate_limit, self._tokens + periods * self.rate_limit)
            self._last_refill = now - (elapsed % self.period)
    
    def acquire(self, timeout: float = None) -> bool:
        """
        获取一个令牌
        
        Args:
            timeout: 超时时间（秒），None 表示无限等待
        
        Returns:
            是否成功获取令牌
        """
        start_time = time.time()
        
        with self._condition:
            while True:
                self._refill()
                
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
                
                # 计算需要等待的时间
                wait_time = self.period - (time.time() - self._last_refill)
                
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                    wait_time = min(wait_time, timeout - elapsed)
                
                self._condition.wait(wait_time)
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class RetryHandler:
    """
    重试处理器
    
    处理 API 调用的自动重试，支持多种重试策略。
    """
    
    def __init__(self, config: RateLimitConfig = None):
        """
        初始化重试处理器
        
        Args:
            config: 限流配置，None 则使用默认配置
        """
        self.config = config or RateLimitConfig()
        self.stats = RetryStats()
        self._rate_limiter = RateLimiter(
            rate_limit=self.config.rate_limit,
            period=self.config.period
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟
        
        Args:
            attempt: 当前尝试次数（从1开始）
        
        Returns:
            延迟时间（秒）
        """
        strategy = self.config.retry_strategy
        
        if strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        
        elif strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_factor ** (attempt - 1))
        
        elif strategy == RetryStrategy.JITTERED:
            # 指数退避 + 随机抖动
            base_delay = self.config.base_delay * (self.config.backoff_factor ** (attempt - 1))
            # 添加 0-50% 的随机抖动
            jitter = base_delay * random.uniform(0, 0.5)
            delay = base_delay + jitter
        
        else:
            delay = self.config.base_delay
        
        return min(delay, self.config.max_delay)
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        判断错误是否可重试
        
        Args:
            error: 异常对象
        
        Returns:
            是否可重试
        """
        # 检查异常类型
        for exc_type in self.config.retryable_exceptions:
            if isinstance(error, exc_type):
                return True
        
        # 检查 SDK 特定错误
        error_str = str(error).lower()
        retryable_keywords = [
            'throttl',      # throttling
            'rate limit',
            'too many',
            'timeout',
            'connection',
            'temporarily unavailable',
            'service unavailable',
            'internal error',
            'bad gateway',
            'gateway timeout',
        ]
        
        for keyword in retryable_keywords:
            if keyword in error_str:
                return True
        
        # 检查 TeaError（阿里云 SDK 错误）
        if hasattr(error, 'status_code'):
            if error.status_code in self.config.retryable_status_codes:
                return True
        
        return False
    
    def execute(self, func: Callable[[], T]) -> T:
        """
        执行带重试的函数调用
        
        Args:
            func: 要执行的函数
        
        Returns:
            函数返回值
        
        Raises:
            最后一次调用产生的异常
        """
        self.stats.total_calls += 1
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # 获取限速令牌
                self._rate_limiter.acquire()
                
                # 执行调用
                result = func()
                
                self.stats.successful_calls += 1
                return result
                
            except Exception as e:
                last_error = e
                self.stats.last_error = str(e)
                
                # 检查是否可重试
                if attempt < self.config.max_retries and self._is_retryable_error(e):
                    self.stats.total_retries += 1
                    delay = self._calculate_delay(attempt + 1)
                    self.stats.total_wait_time += delay
                    self.stats.last_retry_time = datetime.now()
                    
                    # 输出重试信息
                    print(f"⚠️ API 调用失败，{delay:.1f}秒后重试 (尝试 {attempt + 2}/{self.config.max_retries + 1}): {e}", file=sys.stderr)
                    
                    time.sleep(delay)
                else:
                    # 不可重试或达到最大重试次数
                    self.stats.failed_calls += 1
                    raise
        
        # 理论上不会到达这里
        self.stats.failed_calls += 1
        raise last_error


# 全局默认配置
_default_config = RateLimitConfig()
_default_handler = RetryHandler(_default_config)


def with_retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.JITTERED,
    rate_limit: int = 20,
    period: float = 1.0,
) -> Callable:
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        strategy: 重试策略
        rate_limit: 时间窗口内最大请求数
        period: 时间窗口（秒）
    
    Returns:
        装饰器函数
    
    Example:
        @with_retry(max_retries=3, backoff_factor=2.0)
        def call_api():
            return client.some_method()
    """
    def decorator(func: Callable[[], T]) -> Callable[[], T]:
        config = RateLimitConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            base_delay=base_delay,
            max_delay=max_delay,
            retry_strategy=strategy,
            rate_limit=rate_limit,
            period=period,
        )
        handler = RetryHandler(config)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return handler.execute(lambda: func(*args, **kwargs))
        
        # 附加处理器实例供外部访问
        wrapper._retry_handler = handler
        
        return wrapper
    
    return decorator


def retry_api_call(
    func: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.JITTERED,
    rate_limit: int = 20,
    period: float = 1.0,
) -> T:
    """
    执行带重试的 API 调用
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        strategy: 重试策略
        rate_limit: 时间窗口内最大请求数
        period: 时间窗口（秒）
    
    Returns:
        函数返回值
    
    Example:
        result = retry_api_call(
            lambda: client.list_instances(request),
            max_retries=3
        )
    """
    config = RateLimitConfig(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_strategy=strategy,
        rate_limit=rate_limit,
        period=period,
    )
    handler = RetryHandler(config)
    return handler.execute(func)


def get_retry_stats() -> RetryStats:
    """
    获取全局重试统计
    
    Returns:
        RetryStats 实例
    """
    return _default_handler.stats


def reset_retry_stats():
    """重置全局重试统计"""
    global _default_handler
    _default_handler.stats = RetryStats()


def set_global_config(
    max_retries: int = None,
    backoff_factor: float = None,
    base_delay: float = None,
    max_delay: float = None,
    strategy: RetryStrategy = None,
    rate_limit: int = None,
    period: float = None,
):
    """
    设置全局限流配置
    
    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        base_delay: 基础延迟
        max_delay: 最大延迟
        strategy: 重试策略
        rate_limit: 时间窗口内最大请求数
        period: 时间窗口
    """
    global _default_config, _default_handler
    
    if max_retries is not None:
        _default_config.max_retries = max_retries
    if backoff_factor is not None:
        _default_config.backoff_factor = backoff_factor
    if base_delay is not None:
        _default_config.base_delay = base_delay
    if max_delay is not None:
        _default_config.max_delay = max_delay
    if strategy is not None:
        _default_config.retry_strategy = strategy
    if rate_limit is not None:
        _default_config.rate_limit = rate_limit
    if period is not None:
        _default_config.period = period
    
    _default_handler = RetryHandler(_default_config)


# 便捷类：带限流的 API 客户端包装器
class RateLimitedClient:
    """
    带限流的 API 客户端包装器
    
    自动为所有方法调用添加重试和限流功能。
    
    Example:
        from alibabacloud_pai_dsw20220101.client import Client
        
        base_client = Client(config)
        client = RateLimitedClient(base_client, max_retries=3)
        
        # 所有调用自动带重试和限流
        response = client.list_instances(request)
    """
    
    def __init__(
        self,
        client: Any,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.JITTERED,
        rate_limit: int = 20,
        period: float = 1.0,
    ):
        """
        初始化限流客户端
        
        Args:
            client: 原始客户端对象
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            base_delay: 基础延迟
            max_delay: 最大延迟
            strategy: 重试策略
            rate_limit: 时间窗口内最大请求数
            period: 时间窗口
        """
        self._client = client
        self._config = RateLimitConfig(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            base_delay=base_delay,
            max_delay=max_delay,
            retry_strategy=strategy,
            rate_limit=rate_limit,
            period=period,
        )
        self._handler = RetryHandler(self._config)
    
    def __getattr__(self, name: str) -> Any:
        """
        代理所有方法调用，添加重试和限流
        """
        attr = getattr(self._client, name)
        
        if callable(attr):
            @functools.wraps(attr)
            def wrapper(*args, **kwargs):
                return self._handler.execute(lambda: attr(*args, **kwargs))
            return wrapper
        
        return attr
    
    @property
    def stats(self) -> RetryStats:
        """获取重试统计"""
        return self._handler.stats


# 命令行入口（用于测试）
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Rate Limiter Test')
    parser.add_argument('--test', choices=['basic', 'stress', 'retry'], default='basic',
                        help='Test mode')
    parser.add_argument('--rate-limit', type=int, default=5,
                        help='Requests per period')
    parser.add_argument('--period', type=float, default=1.0,
                        help='Period in seconds')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Max retries')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Rate Limiter Test")
    print("=" * 50)
    
    if args.test == 'basic':
        print(f"\n测试基本限流: {args.rate_limit} 请求/{args.period}秒\n")
        limiter = RateLimiter(rate_limit=args.rate_limit, period=args.period)
        
        for i in range(10):
            start = time.time()
            with limiter:
                elapsed = time.time() - start
                print(f"请求 {i+1}: 等待 {elapsed:.3f}s 后执行")
    
    elif args.test == 'retry':
        print(f"\n测试重试机制: 最大重试 {args.max_retries} 次\n")
        
        call_count = [0]
        
        @with_retry(max_retries=args.max_retries)
        def flaky_function():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("模拟连接失败")
            return "成功!"
        
        try:
            result = flaky_function()
            print(f"结果: {result}, 总调用: {call_count[0]}")
        except Exception as e:
            print(f"失败: {e}")
        
        stats = flaky_function._retry_handler.stats
        print(f"\n统计:")
        print(f"  总调用: {stats.total_calls}")
        print(f"  成功: {stats.successful_calls}")
        print(f"  重试: {stats.total_retries}")
        print(f"  总等待时间: {stats.total_wait_time:.2f}s")
    
    print("\n测试完成!")