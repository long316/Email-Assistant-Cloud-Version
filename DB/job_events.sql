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

 Date: 14/10/2025 11:18:02
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for job_events
-- ----------------------------
DROP TABLE IF EXISTS `job_events`;
CREATE TABLE `job_events`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `job_id` char(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` json NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_je_job`(`job_id`) USING BTREE,
  INDEX `idx_je_event`(`event_type`) USING BTREE,
  CONSTRAINT `fk_je_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
