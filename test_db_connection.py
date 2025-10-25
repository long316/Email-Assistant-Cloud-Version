#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
用于验证数据库超时和重试机制
"""

import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_database_connection():
    """测试数据库连接"""
    logger.info("开始测试数据库连接...")

    try:
        from src.dao_mysql import _conn

        # 测试连接
        logger.info("尝试建立数据库连接...")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test")
                result = cur.fetchone()
                logger.info(f"✅ 数据库连接成功! 测试查询结果: {result}")

        # 测试查询jobs表
        logger.info("尝试查询jobs表...")
        from src.dao_mysql import get_next_queued_job
        job = get_next_queued_job()
        if job:
            logger.info(f"✅ 找到待处理任务: {job['id']}")
        else:
            logger.info("ℹ️  当前没有待处理任务")

        return True

    except Exception as e:
        logger.error(f"❌ 数据库连接测试失败: {e}", exc_info=True)
        return False


def test_job_runner():
    """测试JobRunner启动"""
    logger.info("\n开始测试JobRunner...")

    try:
        from src.job_runner import JobRunner

        logger.info("创建JobRunner实例...")
        runner = JobRunner(interval_sec=2)

        logger.info("启动JobRunner...")
        runner.start()

        import time
        logger.info("等待5秒观察JobRunner运行情况...")
        time.sleep(5)

        logger.info("停止JobRunner...")
        runner.stop()

        logger.info("✅ JobRunner测试完成")
        return True

    except Exception as e:
        logger.error(f"❌ JobRunner测试失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("邮件助手 - 数据库连接和JobRunner测试")
    logger.info("=" * 60)

    # 测试1: 数据库连接
    db_ok = test_database_connection()

    # 测试2: JobRunner
    runner_ok = test_job_runner()

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总:")
    logger.info(f"  数据库连接: {'✅ 通过' if db_ok else '❌ 失败'}")
    logger.info(f"  JobRunner:  {'✅ 通过' if runner_ok else '❌ 失败'}")
    logger.info("=" * 60)

    if db_ok and runner_ok:
        logger.info("\n🎉 所有测试通过! 系统已准备就绪")
        sys.exit(0)
    else:
        logger.error("\n⚠️  部分测试失败，请检查日志")
        sys.exit(1)
