import os
import glob
import pandas as pd
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
import re

# ==================== 配置日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def detect_date_column(df):
    """动态检测日期列"""
    date_keywords = ["日期", "时间", "结算日期", "day", "date", "time"]
    for col in df.columns:
        cleaned_col = str(col).strip().lower().replace(" ", "").replace("_", "")
        if any(keyword in cleaned_col for keyword in date_keywords):
            logger.info(f"检测到日期列: {col}")
            return col
    logger.warning("未找到日期列，请检查列名是否正确")
    return None


def insert_excel_to_database_fixed_advertiser():
    """主函数：将媒体结算表数据导入数据库"""

    # ========== 1. 配置参数 ==========
    FIXED_ADVERTISER_NAME = "美数"  # 固定广告主名称
    DOWNLOAD_DIR = r"D:\\"
    FILE_PATTERN = "广告位分天报表*.xlsx"

    DB_CONFIG = {
        'host': '192.168.100.27',
        'user': 'zmonv',
        'password': 'rpa@2025',
        'database': 'zmonv_rpa',
        'charset': 'utf8mb4',
        'port': 3306,
        'autocommit': False
    }

    # ========== 2. 查找匹配的 Excel 文件 ==========
    logger.info(f"正在查找目录: {DOWNLOAD_DIR}")
    logger.info(f"匹配模式: {FILE_PATTERN}")

    pattern = os.path.join(DOWNLOAD_DIR, FILE_PATTERN)
    excel_files = glob.glob(pattern)

    if not excel_files:
        logger.warning("未找到匹配的 Excel 文件")
        return

    logger.info(f"找到 {len(excel_files)} 个文件：")
    for f in excel_files:
        logger.info(f"    {os.path.basename(f)}")

    # ========== 3. 连接数据库 ==========
    connection = None
    cursor = None

    try:
        logger.info("正在连接数据库...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        logger.info("数据库连接成功")

        # ========== 4. 查询广告主 ID ==========
        query_advertiser = "SELECT advertiser_id FROM ad_sync_data_base WHERE advertiser = %s"
        cursor.execute(query_advertiser, (FIXED_ADVERTISER_NAME,))
        result = cursor.fetchone()

        if result:
            advertiser_id = result[0]
            logger.info(f"已找到广告主 ID: {advertiser_id} (广告主: {FIXED_ADVERTISER_NAME})")
        else:
            logger.error(f"广告主 '{FIXED_ADVERTISER_NAME}' 不存在，终止任务")
            return

        # ========== 5. 处理每个文件 ==========
        for file_path in excel_files:
            try:
                logger.info(f"正在处理文件: {os.path.basename(file_path)}")
                df = pd.read_excel(file_path, engine='openpyxl')

                if df.empty:
                    logger.warning("文件为空，跳过。")
                    continue

                logger.info(f"共 {len(df)} 行数据，开始清洗...")
                logger.info(f"Excel列名: {[str(col) for col in df.columns]}")

                # 动态检测日期列
                date_column = detect_date_column(df)
                if not date_column:
                    logger.error(f"文件 {os.path.basename(file_path)} 缺少日期列，跳过")
                    continue

                # 标准化列名（去除空格、下划线，转小写）
                df.columns = [str(col).strip().lower().replace(" ", "").replace("_", "") for col in df.columns]
                logger.info(f"标准化后的列名: {list(df.columns)}")

                data_to_insert = []
                for index, row in df.iterrows():
                    try:
                        # 提取日期
                        date_col_std = date_column.strip().lower().replace(" ", "").replace("_", "")
                        date_field = row.get(date_col_std)
                        if pd.isna(date_field):
                            logger.warning(f"第 {index + 3} 行日期为空，跳过")
                            continue
                        try:
                            date = pd.to_datetime(date_field).strftime('%Y-%m-%d')
                        except Exception as e:
                            logger.error(f"第 {index + 3} 行日期格式错误: {e}，跳过")
                            continue

                        # 提取展现数（适配实际列名“展现数”）
                        impressions = row.get("曝光数")  # 关键修改：使用实际列名
                        if pd.isna(impressions):
                            logger.warning(f"第 {index + 3} 行展现数为空，跳过")
                            continue
                        # 处理可能的字符串格式数字（如带千分符）
                        if isinstance(impressions, str):
                            impressions = impressions.replace(",", "").strip()
                        impressions = int(impressions)

                        # 提取广告位ID（适配列名“广告位id”）
                        ad_position_id = row.get("媒体ID")  # 标准化后列名匹配
                        if pd.isna(ad_position_id):
                            logger.warning(f"第 {index + 3} 行广告位ID为空，跳过")
                            continue
                        ad_position_id = str(ad_position_id).strip()
                        if ad_position_id.lower() == "nan":
                            ad_position_id = ""

                        # 提取广告位名称
                        ad_position = row.get("流量源名称")
                        if pd.isna(ad_position):
                            ad_position = ""
                        else:
                            ad_position = str(ad_position).strip()

                        # 提取点击数（适配列名“点击数”）
                        clicks = row.get("点击数")  # 关键修改：使用实际列名
                        if pd.isna(clicks):
                            logger.warning(f"第 {index + 3} 行点击数为空，跳过")
                            continue
                        # 处理可能的字符串格式数字
                        if isinstance(clicks, str):
                            clicks = clicks.replace(",", "").strip()
                        clicks = int(clicks)

                        # 提取收入（适配列名“收入(元)”）
                        income = row.get("收入")  # 标准化后列名匹配
                        if pd.isna(income):
                            logger.warning(f"第 {index + 3} 行收入为空，跳过")
                            continue
                        # 处理可能的字符串格式金额
                        if isinstance(income, str):
                            income = income.replace(",", "").replace("元", "").strip()
                        try:
                            income = float(income)
                        except ValueError:
                            logger.warning(f"第 {index + 3} 行收入格式错误，跳过")
                            continue

                        # 构建记录
                        record = {
                            "advertiser_id": advertiser_id,
                            "advertiser": FIXED_ADVERTISER_NAME,
                            "date": date,
                            "jht_id": None,
                            "ad_position_id": ad_position_id,
                            "ad_position": ad_position,
                            "impressions": impressions,
                            "clicks": clicks,
                            "income": income
                        }
                        data_to_insert.append(record)

                    except Exception as e:
                        logger.error(f"第 {index + 3} 行解析失败: {e}，跳过")
                        continue

                # ========== 6. 批量插入数据库 ==========
                if data_to_insert:
                    insert_query = """
                    INSERT IGNORE INTO ad_sync_data 
                    (advertiser_id, advertiser, date, jht_id, ad_position_id, ad_position, 
                     impressions, clicks, income)
                    VALUES 
                    (%(advertiser_id)s, %(advertiser)s, %(date)s, %(jht_id)s, %(ad_position_id)s, 
                     %(ad_position)s, %(impressions)s, %(clicks)s, %(income)s)
                    """
                    cursor.executemany(insert_query, data_to_insert)
                    connection.commit()
                    logger.info(f"成功插入 {len(data_to_insert)} 条数据到 ad_sync_data 表")
                else:
                    logger.warning("没有有效数据可插入。")
                    continue

                # ========== 7. 删除原文件（按需启用） ==========
                os.remove(file_path)
                # logger.info(f"已删除文件: {os.path.basename(file_path)}")

            except Exception as e:
                logger.error(f"处理文件失败 {os.path.basename(file_path)}: {e}")
                continue

    except Error as db_err:
        logger.critical(f"数据库连接错误: {db_err}")
    except Exception as e:
        logger.critical(f"发生未知错误: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            logger.info("数据库连接已关闭")


if __name__ == "__main__":
    logger.info("开始执行广告数据导入任务...")
    insert_excel_to_database_fixed_advertiser()
    logger.info("任务执行完毕。")