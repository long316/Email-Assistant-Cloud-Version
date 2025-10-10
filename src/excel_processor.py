"""
Excel文件处理模块
负责读取、过滤和更新Excel文件中的邮箱数据
"""
import logging
import pandas as pd
from typing import List, Dict, Any, Set
from pathlib import Path
from src.template_manager import TemplateManager

class ExcelProcessor:
    """Excel文件处理器"""

    def __init__(self, template_dir: str = "template"):
        """
        初始化Excel处理器

        Args:
            template_dir: 模板目录路径
        """
        self.logger = logging.getLogger(__name__)
        self.template_manager = TemplateManager(template_dir)
        self.required_columns = [
            "邮箱", "合作次数", "回复次数", "跟进次数", "跟进方式", "是否已邮箱建联", "语言"
        ]

    def validate_excel_file(self, file_path: str) -> bool:
        """
        验证Excel文件是否包含必需的列

        Args:
            file_path: Excel文件路径

        Returns:
            文件是否有效
        """
        try:
            df = pd.read_excel(file_path)

            # 检查必需的列是否存在
            missing_columns = []
            for col in self.required_columns:
                if col not in df.columns:
                    missing_columns.append(col)

            if missing_columns:
                self.logger.error(f"Excel文件缺少必需的列: {missing_columns}")
                return False

            self.logger.info(f"Excel文件验证成功: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Excel文件验证失败: {e}")
            return False

    def read_excel_data(self, file_path: str) -> pd.DataFrame:
        """
        读取Excel文件数据

        Args:
            file_path: Excel文件路径

        Returns:
            数据DataFrame，失败时返回空DataFrame
        """
        try:
            df = pd.read_excel(file_path)
            self.logger.info(f"成功读取Excel文件: {file_path}, 共 {len(df)} 行数据")
            return df
        except Exception as e:
            self.logger.error(f"读取Excel文件失败: {e}")
            return pd.DataFrame()

    def filter_email_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据指定条件过滤邮箱列表
        筛选条件："邮箱"!=NULL & "合作次数"==0 & "回复次数"==0 & "跟进次数"==1 & "跟进方式"!="手动"

        Args:
            df: 原始数据DataFrame

        Returns:
            过滤后的DataFrame
        """
        try:
            # 应用过滤条件
            filtered_df = df[
                (df["邮箱"].notna()) &  # 邮箱不为空
                (df["邮箱"] != "") &     # 邮箱不为空字符串
                (df["合作次数"] == 0) &  # 合作次数为0
                (df["回复次数"] == 0) &  # 回复次数为0
                (df["跟进次数"] == 1) &  # 跟进次数为1
                (df["跟进方式"] != "手动")  # 跟进方式不是手动
            ].copy()

            self.logger.info(f"过滤后的邮箱数量: {len(filtered_df)}")

            # 显示过滤后的邮箱列表
            if len(filtered_df) > 0:
                email_list = filtered_df["邮箱"].tolist()
                self.logger.info(f"待发送邮箱列表: {email_list[:10]}{'...' if len(email_list) > 10 else ''}")

            return filtered_df

        except Exception as e:
            self.logger.error(f"邮箱列表过滤失败: {e}")
            return pd.DataFrame()

    def update_email_status(self, file_path: str, email: str, status: int) -> bool:
        """
        更新Excel文件中特定邮箱的建联状态

        Args:
            file_path: Excel文件路径
            email: 邮箱地址
            status: 状态值 (1: 成功, -1: 失败)

        Returns:
            是否更新成功
        """
        try:
            # 读取当前文件
            df = pd.read_excel(file_path)

            # 查找对应的邮箱行
            mask = df["邮箱"] == email
            if not mask.any():
                self.logger.warning(f"未找到邮箱: {email}")
                return False

            # 更新状态
            df.loc[mask, "是否已邮箱建联"] = status

            # 保存文件
            df.to_excel(file_path, index=False)

            status_text = "成功" if status == 1 else "失败"
            self.logger.info(f"邮箱状态更新{status_text}: {email}")
            return True

        except Exception as e:
            self.logger.error(f"更新邮箱状态失败: {e}")
            return False

    def batch_update_status(self, file_path: str, email_status_dict: Dict[str, int]) -> Dict[str, bool]:
        """
        批量更新邮箱状态

        Args:
            file_path: Excel文件路径
            email_status_dict: 邮箱状态字典 {email: status}

        Returns:
            更新结果字典 {email: success}
        """
        results = {}

        try:
            # 读取当前文件
            df = pd.read_excel(file_path)

            # 批量更新
            for email, status in email_status_dict.items():
                mask = df["邮箱"] == email
                if mask.any():
                    df.loc[mask, "是否已邮箱建联"] = status
                    results[email] = True
                else:
                    results[email] = False
                    self.logger.warning(f"未找到邮箱: {email}")

            # 保存文件
            df.to_excel(file_path, index=False)
            self.logger.info(f"批量更新完成，成功: {sum(results.values())}, 失败: {len(results) - sum(results.values())}")

        except Exception as e:
            self.logger.error(f"批量更新失败: {e}")
            # 如果批量更新失败，将所有结果标记为失败
            for email in email_status_dict.keys():
                results[email] = False

        return results

    def get_pending_emails(self, file_path: str) -> List[str]:
        """
        获取待发送的邮箱列表

        Args:
            file_path: Excel文件路径

        Returns:
            待发送的邮箱列表
        """
        try:
            df = self.read_excel_data(file_path)
            if df.empty:
                return []

            filtered_df = self.filter_email_list(df)
            if filtered_df.empty:
                return []

            # 进一步筛选：排除已经处理过的邮箱（状态为1或-1）
            pending_df = filtered_df[
                (filtered_df["是否已邮箱建联"].isna()) |  # 状态为空
                (filtered_df["是否已邮箱建联"] == 0)      # 状态为0
            ]

            email_list = pending_df["邮箱"].tolist()
            self.logger.info(f"待发送邮箱数量: {len(email_list)}")

            return email_list

        except Exception as e:
            self.logger.error(f"获取待发送邮箱列表失败: {e}")
            return []

    def get_statistics(self, file_path: str) -> Dict[str, Any]:
        """
        获取Excel文件的统计信息

        Args:
            file_path: Excel文件路径

        Returns:
            统计信息字典
        """
        try:
            df = self.read_excel_data(file_path)
            if df.empty:
                return {}

            filtered_df = self.filter_email_list(df)

            # 统计各种状态的邮箱数量
            total_count = len(df)
            filtered_count = len(filtered_df)

            if filtered_count > 0:
                success_count = len(filtered_df[filtered_df["是否已邮箱建联"] == 1])
                failed_count = len(filtered_df[filtered_df["是否已邮箱建联"] == -1])
                pending_count = len(filtered_df[
                    (filtered_df["是否已邮箱建联"].isna()) |
                    (filtered_df["是否已邮箱建联"] == 0)
                ])
            else:
                success_count = failed_count = pending_count = 0

            stats = {
                "总邮箱数": total_count,
                "符合条件邮箱数": filtered_count,
                "发送成功数": success_count,
                "发送失败数": failed_count,
                "待发送数": pending_count
            }

            self.logger.info(f"统计信息: {stats}")
            return stats

        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}

    def validate_templates_for_excel(self, file_path: str) -> Dict[str, Any]:
        """
        验证Excel文件中的模板参数兼容性

        Args:
            file_path: Excel文件路径

        Returns:
            验证结果字典
        """
        try:
            df = self.read_excel_data(file_path)
            if df.empty:
                return {"valid": False, "error": "无法读取Excel文件"}

            # 获取所有列名
            data_columns = df.columns.tolist()

            # 获取所有唯一的语言
            if "语言" in df.columns:
                unique_languages = df["语言"].dropna().unique().tolist()
            else:
                unique_languages = ["English"]  # 默认英语

            validation_results = {
                "overall_valid": True,
                "data_columns": data_columns,
                "languages_found": unique_languages,
                "validation_details": {}
            }

            # 验证每种语言的模板
            for language in unique_languages:
                lang_validation = self.template_manager.validate_templates_for_data(
                    data_columns, language
                )

                validation_results["validation_details"][language] = lang_validation["languages"].get(language, {})

                if not lang_validation.get("overall_valid", False):
                    validation_results["overall_valid"] = False

            return validation_results

        except Exception as e:
            self.logger.error(f"验证模板兼容性失败: {e}")
            return {"valid": False, "error": str(e)}

    def get_template_parameters_from_data(self, file_path: str) -> Set[str]:
        """
        从Excel数据中获取可用的模板参数

        Args:
            file_path: Excel文件路径

        Returns:
            可用参数的集合
        """
        try:
            df = self.read_excel_data(file_path)
            if df.empty:
                return set()

            # 返回除了一些系统列之外的所有列名
            system_columns = {"是否已邮箱建联"}
            available_params = set(df.columns.tolist()) - system_columns

            self.logger.info(f"可用模板参数: {available_params}")
            return available_params

        except Exception as e:
            self.logger.error(f"获取模板参数失败: {e}")
            return set()

    def get_filtered_data_with_language(self, file_path: str) -> pd.DataFrame:
        """
        获取过滤后的数据，包含语言信息

        Args:
            file_path: Excel文件路径

        Returns:
            过滤后的DataFrame，包含所有需要的列
        """
        try:
            df = self.read_excel_data(file_path)
            if df.empty:
                return pd.DataFrame()

            # 应用基本过滤条件
            filtered_df = self.filter_email_list(df)
            if filtered_df.empty:
                return pd.DataFrame()

            # 进一步筛选：排除已经处理过的邮箱（状态为1或-1）
            pending_df = filtered_df[
                (filtered_df["是否已邮箱建联"].isna()) |  # 状态为空
                (filtered_df["是否已邮箱建联"] == 0)      # 状态为0
            ].copy()

            # 如果没有语言列，添加默认语言
            if "语言" not in pending_df.columns:
                pending_df["语言"] = "English"
            else:
                # 处理语言列的空值
                pending_df["语言"] = pending_df["语言"].fillna("English")

            self.logger.info(f"获取到 {len(pending_df)} 条待处理的数据记录")
            return pending_df

        except Exception as e:
            self.logger.error(f"获取过滤数据失败: {e}")
            return pd.DataFrame()