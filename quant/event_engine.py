"""
============================================
量化事件引擎 (参考 vnpy EventEngine)
Quantitative Event Engine (Based on vnpy EventEngine)
============================================
"""

from datetime import datetime
from queue import Queue, Empty
from threading import Thread
from typing import Any, Callable
from collections import defaultdict


# 事件类型定义 (参考 vnpy)
EVENT_TICK = "eTick"
EVENT_BAR = "eBar"
EVENT_SIGNAL = "eSignal"
EVENT_ANALYSIS = "eAnalysis"
EVENT_TIMER = "eTimer"
EVENT_LOG = "eLog"


class Event:
    """事件对象"""
    
    def __init__(self, type: str, data: Any = None):
        self.type = type
        self.data = data
        self.timestamp = datetime.now()


class QuantEventEngine:
    """
    量化事件引擎 (参考 vnpy.event.EventEngine)
    
    核心功能：
    - 事件队列管理
    - 事件分发
    - 多线程处理
    """
    
    def __init__(self):
        self._queue = Queue()
        self._active = False
        self._thread = Thread(target=self._run)
        self._handlers = defaultdict(list)
        self._general_handlers = []
        
    def _run(self):
        """事件处理主循环"""
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                self._process(event)
            except Empty:
                pass
    
    def _process(self, event: Event):
        """处理事件"""
        # 调用该事件类型的所有处理函数
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"事件处理错误 {event.type}: {e}")
        
        # 调用通用处理函数
        for handler in self._general_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"通用事件处理错误: {e}")
    
    def start(self):
        """启动事件引擎"""
        self._active = True
        self._thread.start()
    
    def stop(self):
        """停止事件引擎"""
        self._active = False
        self._thread.join()
    
    def register(self, type: str, handler: Callable):
        """注册事件处理函数"""
        handler_list = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)
    
    def unregister(self, type: str, handler: Callable):
        """注销事件处理函数"""
        handler_list = self._handlers[type]
        if handler in handler_list:
            handler_list.remove(handler)
    
    def register_general(self, handler: Callable):
        """注册通用处理函数"""
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)
    
    def unregister_general(self, handler: Callable):
        """注销通用处理函数"""
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)
    
    def put(self, event: Event):
        """推送事件"""
        self._queue.put(event)
    
    def emit(self, type: str, data: Any = None):
        """发送事件"""
        event = Event(type, data)
        self.put(event)
