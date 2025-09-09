import os
import glob
import pandas as pd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_xls_to_xlsx_and_replace():
    """将 .xls 文件转换为 .xlsx"""
    DOWNLOAD_DIR = r"D:\\"
    FILE_PATTERN = "广告位分天报表*.xls"

    search_pattern = os.path.join(DOWNLOAD_DIR, FILE_PATTERN)
    xls_files = glob.glob(search_pattern)

    if not xls_files:
        logger.warning(f"未找到匹配的文件：{search_pattern}")
        return

    logger.info(f"找到 {len(xls_files)} 个 .xls 文件，开始转换...")

    for file_path in xls_files:
        try:
            logger.info(f"正在读取: {file_path}")

            df = pd.read_excel(file_path, engine='xlrd')

            if df.empty:
                logger.warning(f"文件为空，跳过: {file_path}")
                continue

            # 构造 .xlsx 文件路径
            file_dir, file_name = os.path.split(file_path)
            file_base, _ = os.path.splitext(file_name)
            xlsx_file_path = os.path.join(file_dir, f"{file_base}.xlsx")

            # 保存为 .xlsx
            df.to_excel(xlsx_file_path, index=False, engine='openpyxl')
            logger.info(f"转换成功: {xlsx_file_path}")

            # 删除原文件（可选）
            os.remove(file_path)
            logger.info(f"已删除原文件: {file_path}")

        except Exception as e:
            logger.error(f"处理失败 {file_path}: {str(e)}")

    logger.info("所有文件处理完成。")


if __name__ == "__main__":
    convert_xls_to_xlsx_and_replace()