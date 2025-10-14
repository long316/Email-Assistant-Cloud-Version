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

 Date: 11/10/2025 15:56:17
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for stores
-- ----------------------------
DROP TABLE IF EXISTS `stores`;
CREATE TABLE `stores`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `store_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '店铺ID',
  `store_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '店铺名称',
  `master_user_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '所属主账号ID',
  `is_default` tinyint(1) NULL DEFAULT 0 COMMENT '是否默认店铺',
  `is_active` tinyint(1) NULL DEFAULT 1 COMMENT '是否激活',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL COMMENT '店铺描述',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_store_id`(`store_id`, `master_user_id`) USING BTREE,
  INDEX `idx_master_user_id`(`master_user_id`) USING BTREE,
  INDEX `idx_store_master`(`store_id`, `master_user_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '店铺表' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
