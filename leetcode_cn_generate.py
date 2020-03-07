# coding:utf-8

#
# Author: BONFY<ruan.lj@foxmail.com>
# Usage:  Leetcode solution downloader and auto generate readme
#

import random
import requests
import configparser
import os
import json
import time
import re
import sys
import logging

from pyquery import PyQuery as pq
from collections import namedtuple, OrderedDict
from itertools import groupby


HOME = os.getcwd()
CONFIG_FILE = os.path.join(HOME, 'config.cfg')
DOMAIN = 'leetcode-cn.com'
BASE_URL = 'https://{}'.format(DOMAIN)
GRAPHQL_LIMIT = 20

# If you have proxy, change PROXIES below
PROXIES = None
HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
    'Connection': 'keep-alive',
    'Host': DOMAIN,
    'referer': BASE_URL + '/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'  # NOQA
}


def retry(times=3):
    import functools, time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logging.warning('retrying function `%s`, args %s kwargs %s',
                        func.__name__, args, kwargs)
                    if i >= times - 1:
                        # logger.exception(e)
                        raise
                    else:
                        time.sleep((i+1) * 0.5)
        return wrapper
    return decorator


def get_config_from_file():
    cp = configparser.ConfigParser()
    cp.read(CONFIG_FILE)

    if 'leetcode' not in list(cp.sections()):
        raise ValueError('Please create config.cfg first.')

    username = cp.get('leetcode', 'username')
    password = cp.get('leetcode', 'password')

    if not username or not password:    # username and password not none
        raise ValueError('Please input your username and password in config.cfg.')

    language = cp.get('leetcode', 'language')
    if not language:
        language = 'python'    # language default python

    repo = cp.get('leetcode', 'repo')
    if not repo:
        raise ValueError('Please input your Github repo address')

    rst = dict(username=username, password=password, language=language.lower(), repo=repo)
    return rst


def rep_unicode_in_code(code):
    """
    Replace unicode to str in the code
    like '\u003D' to '='
    :param code: type str
    :return: type str
    """
    pattern = re.compile('(\\\\u[0-9a-zA-Z]{4})')
    m = pattern.findall(code)
    for item in set(m):
        code = code.replace(item, chr(int(item[2:], 16)))    # item[2:]åŽ»æŽ‰\u
    return code


def check_and_make_dir(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)


ProgLang = namedtuple('ProgLang', ['language', 'ext', 'annotation'])

ProgLangList = [ProgLang('c++', 'cpp', '//'),
                ProgLang('java', 'java', '//'),
                ProgLang('python', 'py', '#'),
                ProgLang('c', 'c', '//'),
                ProgLang('c#', 'cs', '//'),
                ProgLang('javascript', 'js', '//'),
                ProgLang('ruby', 'rb', '#'),
                ProgLang('swift', 'swift', '//'),
                ProgLang('go', 'go', '//')]

ProgLangDict = dict((item.language, item) for item in ProgLangList)
CONFIG = get_config_from_file()

class Solution:
    def __init__(self, index, title, capital_title, pass_language=None):
        self.id = index
        self.title = title
        self.capital_title = capital_title
        self.pass_language = pass_language.copy() if pass_language is not None else []

class QuizItem:
    def __init__(self, data):
        self.id = int(data['id'])
        self.title = data['title']
        self.capital_title = data['capital_title']
        self.url = data['url']
        self.acceptance = data['acceptance']
        self.difficulty = data['difficulty']
        self.lock = data['lock']
        self.pass_status = True if data['pass'] == 'ac' else False  # 'None', 'ac', 'notac'
        self.article = data['article']
        self.sample_code = None
        self.pass_language = []

    def __repr__(self):
        return '<Quiz: {id}-{title}({difficulty})-{pass_status}>'.format(
            id=self.id, title=self.title, difficulty=self.difficulty, pass_status=self.pass_status)

def md5(my_string):
    import hashlib
    if not isinstance(my_string, bytes):
        b = my_string.encode('utf-8')
    else:
        b = my_string
    m = hashlib.md5()
    m.update(b)
    return m.hexdigest()

# import leveldb, uuid, os
# class LevalCache(object):

#     def __init__(self, name, store_path):
#         if name is None:
#             name = uuid.uuid4()
#         self.name = name
#         self.path = os.path.join(store_path, self.name)
#         self.db = None

#     def check_init_db(self):
#         if self.db is None:
#             path = self.path
#             if not os.path.exists(path):
#                 os.makedirs(path)
#             self.db = leveldb.LevelDB(path)

#     def get(self, key, default=None):
#         self.check_init_db()
#         try:
#             data = self.db.Get(key.encode())
#         except KeyError:
#             return None or default
#         return json.loads(data)

#     def set(self, key, val):
#         self.check_init_db()
#         return self.db.Put(key.encode(), json.dumps(val).encode('utf8'))


# cache = LevalCache('query', 'db')


# @retry()
def _query(session, method, uri, load_json=True, headers=None, **kw):
    req_id = md5(json.dumps([method, uri, load_json, headers, kw], sort_keys=True))
    func = getattr(session, method.lower())
    res = func(BASE_URL + uri, headers=headers, **kw)
    print('request: ', req_id, res.request.url, res.request.body, res.request.headers)
    assert res.ok
    result = json.loads(res.text) if load_json else res.text
    return result

class Leetcode:

    def __init__(self):

        # because only have capital_title in submissions
        # quick find the problem solution by itemdict[capital_title]
        self.itemdict = {}

        # generate items by itemdict.values()
        self.items = []
        self.num_solved = 0
        self.num_total = 0
        self.num_lock = 0

        # change proglang to list
        # config set multi languages
        self.languages = [x.strip() for x in CONFIG['language'].split(',')]
        proglangs = [ProgLangDict[x.strip()] for x in CONFIG['language'].split(',')]
        self.prolangdict = dict(zip(self.languages, proglangs))

        self.solutions = []

        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.proxies = PROXIES
        self.cookies = None
        self.is_login = False

    def login(self):
        if self.is_login:
            return

        if not CONFIG['username'] or not CONFIG['password']:
            raise Exception('Leetcode - Please input your username and password in config.cfg.')

        _query(self.session, 'GET', '/problemset/all/', load_json=False)  # get token
        token = self.session.cookies['csrftoken']

        data = {
            "operationName":"signInWithPassword",
            "query":"mutation signInWithPassword($data: AuthSignInWithPasswordInput!) {\n  authSignInWithPassword(data: $data) {\n    ok\n    __typename\n  }\n}\n",
            "variables":{
                "data":{
                    "username": CONFIG['username'],
                    "password": CONFIG['password'],
                }
            },
        }
        _query(self.session, 'POST', '/graphql/', json=data)  # log in

        if not self.session.cookies.get('LEETCODE_SESSION'):
            raise Exception('Login Error')
        self.cookies = dict(self.session.cookies)
        self.is_login = True

    def _generate_items_from_api(self, json_data):
        difficulty = {1: "Easy", 2: "Medium", 3: "Hard"}
        for quiz in json_data['stat_status_pairs']:
            if quiz['stat']['question__hide']:
                continue
            data = {}
            data['title'] = quiz['stat']['question__title_slug']
            data['capital_title'] = quiz['stat']['question__title']
            data['id'] = quiz['stat']['question_id']
            data['lock'] = not json_data.get('is_paid', False) and quiz['paid_only']
            data['difficulty'] = difficulty[quiz['difficulty']['level']]
            data['favorite'] = quiz['is_favor']
            data['acceptance'] = "%.1f%%" % (float(quiz['stat']['total_acs']) * 100 / float(quiz['stat']['total_submitted']))
            data['url'] = '{base}/problems/{title}'.format(base=self.base_url, title=quiz['stat']['question__title_slug'])
            data['pass'] = quiz['status']
            data['article'] = quiz['stat']['question__title_slug']
            item = QuizItem(data)
            yield item

    def load(self):
        assert self.is_login

        rst = _query(self.session, 'GET', '/api/problems/algorithms/')
        if not rst['user_name']:
            raise Exception("Something wrong with your personal info.\n")

        self.num_solved = rst['num_solved']
        self.num_total = rst['num_total']
        items = list(self._generate_items_from_api(rst))
        items.reverse()
        titles = [item.capital_title for item in items]
        self.itemdict = OrderedDict(zip(titles, items))
        self.num_lock = len([i for i in items if i.lock])

        # generate self.items
        # use for generate readme
        self.items = self.itemdict.values()

        # generate self.solutions
        # use for download code
        self.solutions = [Solution(x.id, x.title, x.capital_title, x.pass_language) for x in self.itemdict.values() if x.pass_status]

    def _generate_submissions_by_solution(self, solution):
        """Generate the submissions by Solution item
        :param solution: type Solution
        """
        data ={
            "operationName": "Submissions",
            "variables": {
                "offset": 0,
                "limit": GRAPHQL_LIMIT,
                "lastKey": None,
                "questionSlug": solution.title,
            },
            "query": "query Submissions($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!) {\n  submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: $questionSlug) {\n    lastKey\n    hasNext\n    submissions {\n      id\n      statusDisplay\n      lang\n      runtime\n      timestamp\n      url\n      isPending\n      memory\n      __typename\n    }\n    __typename\n  }\n}\n"
        }
        res = _query(self.session, 'POST', '/graphql/', json=data)
        submissions = res['data']['submissionList'].get('submissions', []) or []
        for idx, i in enumerate(submissions):
            subTime = i['timestamp']
            statusText = i['statusDisplay']
            status = True if statusText == 'Accepted' else False
            url = i['url']  # "/submissions/detail/28814181/"
            runTime = -1 if i['runtime'] == 'N/A' else int(i['runtime'][:-3])
            language = 'python' if i['lang'] == 'python3' else i['lang']  # handle python and python3
            yield dict(id=idx, subTime=subTime, status=status, url=url,
                        runTime=runTime, language=language)

    def _get_question_detail(self, slug):
        """
        slug: eg "two-sum"
        """
        data = {
            "operationName": "questionData",
            "variables":{"titleSlug": slug},
            "query":"query questionData($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    questionFrontendId\n    boundTopicId\n    title\n    titleSlug\n    content\n    translatedTitle\n    translatedContent\n    isPaidOnly\n    difficulty\n    likes\n    dislikes\n    isLiked\n    similarQuestions\n    contributors {\n      username\n      profileUrl\n      avatarUrl\n      __typename\n    }\n    langToValidPlayground\n    topicTags {\n      name\n      slug\n      translatedName\n      __typename\n    }\n    companyTagStats\n    codeSnippets {\n      lang\n      langSlug\n      code\n      __typename\n    }\n    stats\n    hints\n    solution {\n      id\n      canSeeDetail\n      __typename\n    }\n    status\n    sampleTestCase\n    metaData\n    judgerAvailable\n    judgeType\n    mysqlSchemas\n    enableRunCode\n    envInfo\n    book {\n      id\n      bookName\n      pressName\n      source\n      shortDescription\n      fullDescription\n      bookImgUrl\n      pressImgUrl\n      productUrl\n      __typename\n    }\n    isSubscribed\n    isDailyQuestion\n    dailyRecordStatus\n    editorType\n    ugcQuestionId\n    __typename\n  }\n}\n"
        }
        res = _query(self.session, 'POST', '/graphql/', json=data)
        return res['data']['question']

    def _get_question_title_trans_map(self):
        data = {
            "operationName":"getQuestionTranslation",
            "variables":{},
            "query":"query getQuestionTranslation($lang: String) {\n  translations: allAppliedQuestionTranslations(lang: $lang) {\n    title\n    questionId\n    __typename\n  }\n}\n",
        }
        res = _query(self.session, 'POST', '/graphql/', json=data)
        return {int(i['questionId']): i['title'] for i in res['data']['translations']}

    def _get_code_by_solution_and_language(self, solution):
        def get_question_content(question):
            result = 'English:\n'
            result += pq(question['content']).text()
            result += '\n\n'
            result += '中文:\n'
            result += pq(question['translatedContent']).text()
            return result

        all_submissions = sorted(self._generate_submissions_by_solution(solution),
            key=lambda i: i['language'])

        for language, submissions_language in groupby(all_submissions, key=lambda i: i['language']):
            submissions = [i for i in submissions_language if i['status']]
            if not submissions:
                print('No pass {language} solution in question:{title}'.format(language=language, title=solution.title))
                continue

            self.itemdict[solution.capital_title].pass_language.append(language)
            solution.pass_language.append(language)
            if len(submissions) == 1:
                sub = submissions[0]
            else:
                sub = min(submissions, key=lambda i: i['runTime'])

            question = get_question_content(self._get_question_detail(solution.title))

            pattern = re.compile(r'submissionCode: \'(?P<code>.*)\',\n  editCodeUrl', re.S)
            res = _query(self.session, 'GET', sub['url'], load_json=False)
            m1 = pattern.search(res)
            code = m1.groupdict()['code'] if m1 else None

            if not code:
                raise Exception('Can not find solution code in question:{title}'.format(title=solution.title))

            code = rep_unicode_in_code(code)
            yield language, question, code

    def download_code_to_dir(self, solution):
        for language, question, code in self._get_code_by_solution_and_language(solution):
            if not question and not code:
                continue
            dirname = '{id}-{title}'.format(id=str(solution.id).zfill(3), title=solution.title)
            print('begin download', dirname, language)
            check_and_make_dir(dirname)

            path = os.path.join(HOME, dirname)
            fname = '{title}.{ext}'.format(title=solution.title, ext=self.prolangdict[language].ext)
            filename = os.path.join(path, fname)

            l = []
            for item in question.split('\n'):
                if item.strip() == '':
                    l.append(self.prolangdict[language].annotation)
                else:
                    l.append('{anno} {item}'.format(anno=self.prolangdict[language].annotation, item=item))
            quote_question = '\n'.join(l)

            import codecs
            with codecs.open(filename, 'w', 'utf-8') as f:
                print('write to file ->', fname)
                content = '# -*- coding:utf-8 -*-' + '\n' * 3 if language == 'python' else ''
                content += quote_question
                content += '\n' * 3
                content += code
                content += '\n'
                f.write(content)

    def _download_solution(self, solution):
        """ download solution by Solution item
        :param solution: type Solution
        """
        print('{id}-{title} pass'.format(id=solution.id, title=solution.title))
        self.download_code_to_dir(solution)
        time.sleep(random.randint(0, 10) / 5)   # 避免数据拉取失败

    def _get_solution_by_id(self, sid):
        """ get solution by solution id
        :param sid: type int
        """
        if not self.items:
            raise Exception("Please load self info first")
        for solution in self.solutions:
            if solution.id == sid:
                return solution
        print("No solution id:{id} find in leetcode.please confirm".format(id=sid))
        return

    def download_by_id(self, sid):
        """ download one solution by solution id
        :param sid: type int
        """
        solution = self._get_solution_by_id(sid)
        if solution:
            self._download_solution(solution)

    def download(self):
        """ download all solutions with single thread """
        for solution in self.solutions:
            self._download_solution(solution)

    def download_with_thread_pool(self):
        """ download all solutions with multi thread """
        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(max_workers=4)
        for solution in self.solutions:
            pool.submit(self._download_solution, solution)
        pool.shutdown(wait=True)

    def write_readme(self):
        """Write Readme to current folder"""
        title_trans = self._get_question_title_trans_map()
        languages_readme = ','.join([x.capitalize() for x in self.languages])
        md = '''# :pencil2: Leetcode Solutions with {language}
Update time:  {tm}

Auto created by [leetcode_generate](https://github.com/bonfy/leetcode) [Usage](https://github.com/bonfy/leetcode/blob/master/README_leetcode_generate.md)

I have solved **{num_solved}   /   {num_total}** problems
while there are **{num_lock}** problems still locked.

If you have any question, please give me an [issue]({repo}/issues).

If you are loving solving problems in leetcode, please contact me to enjoy it together!

(Notes: :lock: means you need to buy a book from Leetcode to unlock the problem)

| # | Title | Source Code | Article | Difficulty |
|:---:|:---:|:---:|:---:|:---:|'''.format(language=languages_readme,
                                          tm=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                          num_solved=self.num_solved, num_total=self.num_total,
                                          num_lock=self.num_lock, repo=CONFIG['repo'])
        md += '\n'
        for item in self.items:
            article = ''
            if item.article:
                article = '[:memo:]({base_url}/articles/{article}/)'.format(base_url=BASE_URL, article=item.article)
            if item.lock:
                language = ':lock:'
            else:
                if item.pass_language:
                    dirname = '{id}-{title}'.format(id=str(item.id).zfill(3), title=item.title)
                    language = ''
                    language_lst = item.pass_language.copy()
                    while language_lst:
                        lan = language_lst.pop()
                        language += '[{language}]({repo}/blob/master/{dirname}/{title}.{ext})'.format(language=lan.capitalize(), repo=CONFIG['repo'],
                                                                                                 dirname=dirname, title=item.title,
                                                                                                 ext=self.prolangdict[lan].ext)
                        language += ' '
                else:
                    language = ''

            language = language.strip()
            md += '|{id}|[{title_cn} {title}]({url})|{language}|{article}|{difficulty}|\n'.format(
                id=item.id, title=item.title, title_cn=title_trans[item.id], url=item.url, language=language,
                article=article, difficulty=item.difficulty)
        with open('Readme.md', 'w') as f:
            f.write(md)


def main():
    leetcode = Leetcode()
    leetcode.login()
    print('Leetcode login')
    leetcode.load()
    print('Leetcode load self info')

    if len(sys.argv) == 1:
        # simple download
        leetcode.download()
        # we use multi thread
        # print('download all leetcode solutions')
        # leetcode.download_with_thread_pool()
    else:
        for sid in sys.argv[1:]:
            print('begin leetcode by id: {id}'.format(id=sid))
            leetcode.download_by_id(int(sid))

    print('Leetcode finish dowload')
    leetcode.write_readme()
    print('Leetcode finish write readme')


if __name__ == '__main__':
    main()
