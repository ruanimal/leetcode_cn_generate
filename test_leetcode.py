# content of a/conftest.py
import pytest
from leetcode_cn_generate import Leetcode, Solution

@pytest.fixture(scope="session")
def leetcode():
    l = Leetcode()
    l.login()
    return l

def test_login(leetcode):
    leetcode.login()

def test_load(leetcode):
    leetcode.login()
    leetcode.load()

def test_get_question_detail(leetcode):
    leetcode._get_question_detail("two-sum")

def test_get_code_by_solution_and_language(leetcode):
    s = Solution(1, "two-sum", "Two Sum", "python")
    question, code = leetcode._get_code_by_solution_and_language(s, 'python')
    print(question)
    print(code)

def test_generate_submissions_by_solution(leetcode):
    s = Solution(1, "two-sum", "Two Sum", "python")
    res = leetcode._generate_submissions_by_solution(s)
    print(list(res))
