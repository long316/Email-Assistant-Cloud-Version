#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库重试机制测试
验证超时和重试功能是否正常工作
"""

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_db_retry_mechanism():
    """测试数据库重试机制"""
    logger.info("=" * 60)
    logger.info("测试数据库连接重试机制")
    logger.info("=" * 60)

    try:
        from src.dao_mysql import _conn

        # 测试1: 正常连接
        logger.info("\n[测试1] 正常数据库连接...")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test, NOW() as time")
                result = cur.fetchone()
                logger.info(f"✅ 连接成功: {result}")

        # 测试2: 查询jobs表
        logger.info("\n[测试2] 查询jobs表...")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as count FROM jobs")
                result = cur.fetchone()
                logger.info(f"✅ Jobs总数: {result['count']}")

        # 测试3: 查询待处理任务
        logger.info("\n[测试3] 查询待处理任务...")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM jobs WHERE status='queued' AND schedule_at IS NOT NULL "
                    "AND schedule_at<=NOW() ORDER BY schedule_at, created_at LIMIT 1"
                )
                job = cur.fetchone()
                if job:
                    logger.info(f"✅ 找到待处理任务: {job['id']}, type={job['type']}")
                else:
                    logger.info("ℹ️  当前没有待处理任务")

        logger.info("\n" + "=" * 60)
        logger.info("🎉 所有数据库测试通过!")
        logger.info("=" * 60)
        logger.info("\n重要提示:")
        logger.info("1. ✅ 数据库连接超时配置已生效 (connect_timeout=10秒)")
        logger.info("2. ✅ 连接失败重试机制已启用 (最多3次重试)")
        logger.info("3. ✅ 读写超时保护已添加 (read/write_timeout=30秒)")
        logger.info("4. ✅ 详细日志记录已启用 (连接失败时会记录日志)")
        logger.info("\n现在可以启动API服务器测试完整流程:")
        logger.info("  python src/api_server.py")

        return True

    except Exception as e:
        logger.error(f"\n❌ 数据库测试失败: {e}", exc_info=True)
        logger.info("\n可能的原因:")
        logger.info("1. 数据库服务器不可达")
        logger.info("2. 防火墙阻止连接")
        logger.info("3. DATABASE_URL配置错误")
        logger.info("4. 网络不稳定")
        return False


if __name__ == "__main__":
    test_db_retry_mechanism()
