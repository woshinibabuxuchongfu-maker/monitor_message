#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置包
包含系统配置、数据库配置等
"""

from .system_config import Config
from .database_config import DatabaseConfig

__all__ = ['Config', 'DatabaseConfig']
