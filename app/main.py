import logging
import os
import datetime
import pickle
import traceback
from pathlib import Path

import requests

from config import config
from job import jobs_all


def main():
    session = make_session()

    jobs = [job for job in jobs_all if job.__name__ not in config.jobs_skip]
    jobs_failed = []

    for job_class in jobs:
        job = job_class(session)

        try:
            job.run()
        except Exception as e:
            logging.error('# 任务运行出错: ' + repr(e))
            traceback.print_exc()

        if not job.job_success:
            jobs_failed.append(job.job_name)
    logging.info('=' * 5 + datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + '=' * 5)
    logging.info('= 任务数: {}; 失败数: {}'.format(len(jobs), len(jobs_failed)))

    if jobs_failed:
        logging.info('= 失败的任务: {}'.format(jobs_failed))
    else:
        logging.info('= 全部成功 ~')

    logging.info('=' * 26)

    save_session(session)


def make_session() -> requests.Session:
    session = requests.Session()

    session.headers.update({
        'User-Agent': config.ua
    })

    # 代理设置
    if config.proxy['open_proxy']:
        session.proxies = config.proxy['proxies']
        # 开启ssl验证时可以配置ssl证书
        if config.proxy['open_verify']:
            ca_file_name = config.proxy['ca_pem_file']
            if not ca_file_name:
                session.verify = True  # 默认使用Requests自带证书
            else:
                session.verify = Path(__file__).parent.joinpath('../pem/{}'.format(ca_file_name))
        else:
            proxy_patch(session)

    cookies_file = Path(__file__).parent.joinpath('../data/cookies')

    if cookies_file.exists():
        try:
            bytes_data = cookies_file.read_bytes()
            cookies = pickle.loads(bytes_data)
            session.cookies = cookies
            logging.info('# 从文件加载 cookies 成功.')
        except Exception as e:
            logging.info('# 未能成功载入 cookies, 从头开始~')

    return session


def save_session(session):
    data = pickle.dumps(session.cookies)

    data_dir = Path(__file__).parent.joinpath('../data/')
    data_dir.mkdir(exist_ok=True)
    data_file = data_dir.joinpath('cookies')
    data_file.write_bytes(data)


def proxy_patch(session):
    """
    关于requests默认使用的CA证书：
    Requests 默认附带了一套它信任的根证书，来自于 Mozilla trust store。这证书是 certifi 包来管理
    通过更新certifi模块可以得到requests最新的根证书。当然可以通过以下代码找到：
    >>> import certifi
    >>> certifi.where()
    'C:\\Program Files\\Python\\Python36\\lib\\site-packages\\certifi\\cacert.pem'
    cacert.pem中包含很多家CA机构的证书
    可以 不验证 HTTPS 证书
    http://docs.python-requests.org/en/master/user/advanced/#ca-certificates
    """
    import warnings
    from requests.packages.urllib3.exceptions import InsecureRequestWarning

    session.verify = False
    warnings.simplefilter('ignore', InsecureRequestWarning)


if __name__ == '__main__':
    main()
