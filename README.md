# leetcode_cn_generate Usage
![](demo/leetcode.gif)

## Sample
https://github.com/ruanimal/leetcode

## Preparements:
Install essential packages
```cmd
$ pip3 install -r requorements.txt
```

## Config:

Edit your own username, password, language and repo in the **config.cfg.example** file and then rename it to **config.cfg**.

Add `config.cfg` to your `.gitignore` file, to ignore this file from git.

```
[leetcode]

username = username
password = password
language = python,javascript
repo = https://github.com/ruanimal/leetcode
```

## Run

### Fully Download
```cmd
python3 leetcode_cn_generate.py
```
Usually you can always run fully download

### Download By id
```
python3 leetcode_cn_generate.py 1
python3 leetcode_cn_generate.py 1 10 100
```
You can only download the solution you want.

Just add the id arguments behind (seperate by space)

### Download Start From id
```
python3 leetcode_cn_generate.py --sid-start 100
```

You can only download the solution start from which you want.

### Generate Readme
```
python3 leetcode_cn_generate.py --readme
```
By default, readme.md will be generated when the download is complated.

You can also bypass downloading then generate readme.md, by scanning source code of solutions in the `questions` directory.

### Login With LEETCODE_SESSION
```
python3 leetcode_cn_generate.py --session LEETCODE_SESSION
```
Use a token(LEETCODE_SESSION) instead of a password to log in. The token can be found from the browser's devtools.

Logging in with a token prevents session invalidation in the browser.

## Attention
Python 3 have tested

Python 2 maybe

## Changelog
- 2020-03-07: fork from [bonfy](https://github.com/bonfy/leetcode), drop chromedriver requirement, change domain to www.leetcode-cn.com.
- 2022-03-14: fix download bugs, change download directory from current directory to `questions`, change readme generating logic.
- 2022-03-15: add argparser, add token login support
- 2022-03-25: fix bugs, add `sid-start` option, add `FILE_EXPIRE`
