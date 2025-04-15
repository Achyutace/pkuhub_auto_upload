# pkuhub命令行上传文件

## usage
新建config_yaml按照config_example填写
```python
def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='基于YAML配置的资料上传工具')
    parser.add_argument('--config', '-c', required=True, help='YAML配置文件路径')
    parser.add_argument('--retry', '-r', type=int, default=3, help='上传失败重试次数')
    parser.add_argument('--delay', '-d', type=int, default=1, help='上传间隔时间(秒)')
    parser.add_argument('--validate', '-v', action='store_true', help='严格验证选项值')
    return parser.parse_args()
```