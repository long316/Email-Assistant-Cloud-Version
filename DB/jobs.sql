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

 Date: 14/10/2025 11:18:44
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for jobs
-- ----------------------------
DROP TABLE IF EXISTS `jobs`;
CREATE TABLE `jobs`  (
  `id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `master_user_id` bigint NOT NULL,
  `store_id` bigint NOT NULL,
  `type` enum('template','custom') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `sender_email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `template_id` bigint UNSIGNED NULL DEFAULT NULL,
  `subject` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `content` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `html_content` mediumtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `min_interval` int NOT NULL DEFAULT 20,
  `max_interval` int NOT NULL DEFAULT 90,
  `total` int NOT NULL DEFAULT 0,
  `success_count` int NOT NULL DEFAULT 0,
  `failure_count` int NOT NULL DEFAULT 0,
  `status` enum('queued','running','paused','stopped','completed','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'queued',
  `webhook_url` varchar(1024) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `started_at` datetime(6) NULL DEFAULT NULL,
  `completed_at` datetime(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_jobs_tenant`(`master_user_id`, `store_id`) USING BTREE,
  INDEX `idx_jobs_status`(`status`) USING BTREE,
  INDEX `fk_jobs_template`(`template_id`) USING BTREE,
  CONSTRAINT `fk_jobs_template` FOREIGN KEY (`template_id`) REFERENCES `templates` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
