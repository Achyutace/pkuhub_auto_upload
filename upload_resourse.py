import argparse
import yaml
import os
import requests
import logging
from datetime import datetime
import time
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_log.txt'),
        logging.StreamHandler()
    ]
)

DEPARTMENT_DICT = {'选择院系': 0, '中国语言文学系': 40, '人工智能研究院': 30, '体育教研部': 37, '信息科学技术学院': 7, '信息管理系': 25, '元培学院': 9, '光华管理学院': 10, '创新创业学院': 42, '前沿交叉学科研究院': 26, '化学与分子工程学院': 3, '医学部': 16, '医学部教学办': 36, '历史学系': 18, '哲学系': 19, '国家发展研究院': 13, '国际关系学院': 21, '地球与空间科学学院': 5, '城市与环境学院': 20, '外国语学院': 23, '学生工作部人民武装部': 27, '对外汉语教育学院': 41, '工学院': 8, '建筑与景观设计学院': 17, '心理与认知科学学院': 6, '政府管理学院': 31, '教育学院': 14, '数学科学学院': 1, '新闻与传播学院': 15, '材料科学与工程学院': 33, '歌剧研究院': 32, '汇丰商学院': 38, '法学院': 12, '物理学院': 2, '环境科学与工程学院': 24, '现代农学院': 28, '生命科学学院': 4, '社会学系': 34, '经济学院': 11, '考古文博学院': 29, '艺术学院': 39, '英语语言文学系': 22, '马克思主义学院': 35}

# 定义有效选项
VALID_OPTIONS = {
    'material_type': ['试卷', '笔记', '课件', '习题', '答案', '汇编', '其他'],
    'semester': ['2024春季', '2023秋季', '2023春季', '2022秋季', '2022春季', '2021秋季', '2021春季', '其他']
}
VALID_OPTIONS['department'] = list(DEPARTMENT_DICT.keys())

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='基于YAML配置的资料上传工具')
    parser.add_argument('--config', '-c', required=True, help='YAML配置文件路径')
    parser.add_argument('--retry', '-r', type=int, default=3, help='上传失败重试次数')
    parser.add_argument('--delay', '-d', type=int, default=1, help='上传间隔时间(秒)')
    parser.add_argument('--validate', '-v', action='store_true', help='严格验证选项值')
    return parser.parse_args()

def load_yaml_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            logging.info(f"成功加载YAML配置文件: {config_path}")
            return config
    except Exception as e:
        logging.error(f"加载YAML配置文件失败: {e}")
        return None

def validate_option(field, value, strict=True):
    """验证选项值是否有效"""
    if field not in VALID_OPTIONS:
        return True
    if value in VALID_OPTIONS[field]:
        return True
    if strict:
        logging.error(f"'{field}' 的值 '{value}' 无效。有效选项: {', '.join(VALID_OPTIONS[field])}")
        return False
    else:
        logging.warning(f"'{field}' 的值 '{value}' 不在推荐选项中。推荐选项: {', '.join(VALID_OPTIONS[field])}")
        return True

def validate_resource_config(resource, strict_validation=True):
    """验证单个资源的配置是否完整且有效"""
    required_fields = ['title', 'description', 'department', 'course', 'material_type', 'semester', 'file_path']
    for field in required_fields:
        if field not in resource:
            logging.error(f"配置缺少必要字段: {field}")
            return False
    for field in ['material_type', 'semester']:
        if not validate_option(field, resource[field], strict_validation):
            return False
    if not os.path.exists(resource['file_path']):
        logging.error(f"文件不存在: {resource['file_path']}")
        return False
    return True

def get_CSRF_token(session, url):
    """获取 CSRF Token"""
    try:
        response = session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        csrf_token = soup.find("meta", attrs={"name": "csrf-token"})["content"]
        return csrf_token
    except Exception as e:
        logging.error(f"获取 CSRF Token 失败: {e}")
        return None

def upload_resource(resource, retry_count=3):
    """上传单个资源文件"""
    session = requests.Session()
    person_config = load_yaml_config('config.yaml')
    login_url = "https://pkuhub.cn/login"
    # print(person_config['email'], person_config['password'])
    login_data = {"email": person_config['email'], "password": person_config['password'], "remember":False, "csrf_token": get_CSRF_token(session, login_url)}
    r1 = session.post(login_url, data=login_data)
    if r1.status_code != 200:
        logging.error(f"登录失败，状态码: {r1.status_code}")
        return False
    csrf_token = get_CSRF_token(session, "https://pkuhub.cn/upload")
    if not csrf_token:
        logging.error("无法获取 CSRF Token，上传终止")
        return False

    # headers = {
    #     "Origin": "https://pkuhub.cn",
    #     "Referer": "https://pkuhub.cn/upload",
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
    #     "X-CSRFToken": csrf_token
    # }

    for attempt in range(retry_count + 1):
        try:
            with open(resource['file_path'], 'rb') as file:
                data = {
                    'title': resource['title'],
                    'description': resource['description'],
                    'department': DEPARTMENT_DICT[resource['department']],
                    'course': resource['course'],
                    'material_type': resource['material_type'],
                    'semester': resource['semester'],
                    "csrf_token": csrf_token,
                }
                files = {'file': (os.path.basename(resource['file_path']), file)}
                logging.info(f"正在上传文件: {resource['file_path']}")
                logging.info(f"文件元数据: {data}")
                response = session.post("https://pkuhub.cn/upload", files=files, data=data)
                response.raise_for_status()
                logging.info(f"上传响应状态码: {response.status_code}")
                # logging.info(f"上传成功. 响应: {response.headers.get('Content-Type')}")
                logging.info(f"上传成功. 响应网页的长度（若成功应该40000左右）: {len(response.text)}")
                # with open('tem.txt', 'w', encoding='utf-8') as f:
                #     f.write(response.text)
                return True
        except Exception as e:
            if attempt < retry_count:
                wait_time = (attempt + 1) * 2
                logging.warning(f"上传失败 (尝试 {attempt+1}/{retry_count}): {e}")
                logging.warning(f"将在 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logging.error(f"上传失败，已达到最大重试次数: {e}")
                return False
    return False

def process_resources(config, retry_count=3, delay=1, strict_validation=True):
    """处理配置中的所有资源"""
    resources = config.get('resources', [])
    if not resources:
        logging.warning("配置文件中没有找到资源列表")
        return
    total = len(resources)
    success = 0
    failed = 0
    logging.info(f"开始处理 {total} 个资源文件")
    for i, resource in enumerate(resources, 1):
        logging.info(f"处理资源 {i}/{total}: {resource.get('title', '未命名')}")
        if not validate_resource_config(resource, strict_validation):
            logging.error(f"资源 {i} 配置无效，跳过")
            failed += 1
            continue
        if upload_resource(resource, retry_count):
            success += 1
        else:
            failed += 1
        if i < total:
            time.sleep(delay)
    logging.info(f"上传完成. 成功: {success}, 失败: {failed}, 总计: {total}")
    return success, failed, total

def main():
    """主函数"""
    args = parse_arguments()
    config = load_yaml_config(args.config)
    if not config:
        return
    process_resources(config, args.retry, args.delay, args.validate)

if __name__ == "__main__":
    main()