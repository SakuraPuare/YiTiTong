import asyncio
import pathlib
import random

import httpx

base_url = 'http://tyclub.hbuas.edu.cn:12010'

base_header = {
    'Authorization': '',
    'DeviceType': 'pc',
    'Host': 'tyclub.hbuas.edu.cn',
    'Connection': 'Keep-Alive',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13)'
                  ' AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/121.0.6167.178 '
                  'Mobile Safari/537.36 agentweb/4.0.2  UCBrowser/11.6.4.950',
    'Access-Control-Allow-Methods': 'POST,GET,OPTIONS',
    'Access-Control-Allow-Origin': '*',
    'Accept': 'application/json, text/plain, */*',
    'Access-Control-Allow-Credentials': 'true',
    'Origin': 'http://tyclub.hbuas.edu.cn',
    'X-Requested-With': 'com.woyi.run',
    # 'Referer': 'http://tyclub.hbuas.edu.cn:12106/',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
}


class User:
    def __init__(self, account: str, password: str):
        self.account = account
        self.password = password
        self._token = ''

        self.name = ''
        self.classes = ''
        self.faculty = ''
        self.school = ''

        self.self_pk = ''
        self.class_pk = ''
        self.school_pk = ''

    def update(self, data: dict):
        data = data.get('data')

        self.name = data.get('name')
        self.classes = data.get('facName')
        self.faculty = data.get('details')[0].get('facName')
        self.school = data.get('orgName')

        self.self_pk = data.get('fk_Std')
        self.class_pk = data.get('fk_Class')
        self.school_pk = data.get('fk_Org')

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        base_header['Authorization'] = self.token

    def __repr__(self):
        return f'{self.name} {self.account} {self.classes} {self.faculty} {self.school}'


class Course:
    def __init__(self, name: str, teacher: list = None, limit: int = 0, pk: str = ''):
        self.name = name
        self.teacher = teacher
        self.limit = limit
        self.course_pk = pk

        if teacher is None:
            self.teacher = list()

    def __repr__(self):
        return f'{self.name} {", ".join(self.teacher)} {self.limit}'

    # custom sort
    def __lt__(self, other):
        return self.name < other.name

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data.get('cozName'), data.get('teachers'), data.get('totalLim'), data.get('pk'))


async def request(url: str, data: dict = None, json: dict = None, headers: dict = None) -> httpx.Response | None:
    if not headers:
        headers = base_header
    try:
        async with limit:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, data=data, json=json, timeout=10)
                if resp.status_code != 200:
                    raise Exception(f'Error: {resp.status_code}')
                return resp
    except Exception as e:
        print(e)
        return None


async def login(account: str, password: str) -> str:
    path = pathlib.Path(f'./{account}.txt')

    if path.exists():
        with open(path, 'r') as f:
            token = f.read()
            return token

    url = base_url + '/connect/token'
    data = {
        'grant_type': 'password',
        'client_secret': '20abf53e-dae2-11ea-80bd-00163e0a4976',
        'client_id': '1971b298-dae2-11ea-80bd-00163e0a4976',
        'username': account,
        'password': password,
    }
    headers = {
        'User-Agent': 'okhttp/4.7.2',
        'Connection': 'Keep-Alive',
        # 'Accept-Encoding': 'gzip',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    resp = await request(url, data=data, headers=headers)
    while resp is None:
        resp = await request(url, data=data, headers=headers)

    data = resp.json()
    # parse as bearer token
    token = data.get('access_token')
    token = f'Bearer {token}'

    with open(path, 'w') as f:
        f.write(token)

    return token


async def get_person_info(account: str):
    url = base_url + '/api/User/Personal'
    json = {
        'data': {
            'LoginName': account
        }
    }

    resp = await request(url, json=json)
    while resp is None:
        resp = await request(url, json=json)

    data = resp.json()
    return data


async def get_all_courses(org_pk: str, person_pk: str) -> list | None:
    url = 'http://tyclub.hbuas.edu.cn:12013/api/app/stuCozSelQuery'
    json = {
        'data': {
            'fkOrg': org_pk,
            'personPk': person_pk,
            'cozName': '',
            'sorts': [],
        }
    }

    resp = await request(url, json=json)
    while resp is None:
        resp = await request(url, json=json)

    data = resp.json()
    assert not data.get('result', {}).get(
        'isError', True), data.get('result', {}).get('message')

    ret = [i for i in data.get('data', {}).get('rows', [])]
    return ret


async def get_term_info(person_pk) -> str:
    url = 'http://tyclub.hbuas.edu.cn:12013/api/app/stuGetSelCozSched'
    json = {
        'data': {
            'personPk': person_pk,
        }
    }

    resp = await request(url, json=json)
    while resp is None:
        resp = await request(url, json=json)

    data = resp.json()
    return data.get('data').get('rows')[0].get('fkCozStuSel')


async def select_course(term_pk, course_pk, person_pk):
    url = 'http://tyclub.hbuas.edu.cn:12013/api/app/stuCozSel'
    json = {
        'data': {
            'pk': term_pk,
            'fkCozSched': course_pk,
            'personPK': person_pk
        }
    }

    resp = await request(url, json=json)
    while resp is None:
        resp = await request(url, json=json)

    data = resp.json()
    return data


async def main():
    account = input('账号: ').strip()
    password = input('密码: ').strip()

    user = User(account, password)
    token = await login(account, password)
    user.token = token
    user.update(await get_person_info(account))

    print(f'欢迎您！{user}')

    courses = sorted([Course.from_dict(i) for i in
                      await get_all_courses(user.school_pk, user.self_pk)])
    term = await get_term_info(user.self_pk)

    print('请选择课程信息，输入序号开始抢课，输入0退出，如果需要同时抢多门课程，请用逗号分隔')
    print('直接回车开始抢所有的课程\n')
    for idx, course in enumerate(courses):
        print(f'{idx + 1}. {course}')
    ids = input('输入序号: ')
    ids.strip().replace('，', ',')
    ids = ids.split(',')

    if '0' in ids:
        return

    is_success = False

    if not ids or not ids[0]:
        ids = list(range(len(courses)))
        random.shuffle(ids)

    try:
        ids = [int(i) for i in ids]
    except ValueError:
        print('输入错误')
        return

    while not is_success:
        for i in ids:
            if i > len(courses):
                continue

            resp = await select_course(term, courses[int(i) - 1].course_pk, user.self_pk)
            message = resp.get('result').get('message')
            print(message)
            for status in ['课程已选，需退课后再次选课!', '执行成功']:
                if status in message:
                    print(f'抢课成功')
                    is_success = True
                    break

            if is_success:
                break


if __name__ == "__main__":
    limit = asyncio.Semaphore(20)

    asyncio.run(main())
