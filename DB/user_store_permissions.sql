/*
 Navicat Premium Data Transfer

 Source Server         : cloud_yh
 Source Server Type    : MySQL
 Source Server Version : 80043
 Source Host           : 120.25.232.16:3306
 Source Schema         : test

 Target Server Type    : MySQL
 Target Server Version : 80043
 File Encoding         : 65001

 Date: 11/10/2025 15:56:26
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for user_store_permissions
-- ----------------------------
DROP TABLE IF EXISTS `user_store_permissions`;
CREATE TABLE `user_store_permissions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '用户ID(可以是主账号或子账号)',
  `store_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '店铺ID',
  `master_user_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '主账号ID',
  `permission_level` enum('owner','admin','editor','viewer') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT 'viewer' COMMENT '权限级别',
  `can_read` tinyint(1) NULL DEFAULT 1 COMMENT '可读',
  `can_write` tinyint(1) NULL DEFAULT 0 COMMENT '可写',
  `can_delete` tinyint(1) NULL DEFAULT 0 COMMENT '可删除',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_user_store`(`user_id`, `store_id`) USING BTREE,
  INDEX `idx_store_id`(`store_id`) USING BTREE,
  INDEX `idx_master_user_id`(`master_user_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 17 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户店铺权限表' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
