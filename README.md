# leetcode_cn_generate Usage
![](demo/leetcode.gif)

## Demo
https://github.com/ruanima/leetcode

## Preparements:
Install essential packages: `requests`, `pyquery`
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
repo = https://github.com/ruanima/leetcode
```

## Run

### Fully Download
```cmd
python3 leetcode_cn_generate.py
```
Usually you can always run fully download

### Download by id
```
python3 leetcode_cn_generate.py 1
python3 leetcode_cn_generate.py 1 10 100
```
You can only download the solution you want.
Just add the id arguments behind (seperate by space)


## Attention
Python 3 have tested

Python 2 maybe

## Changelog
- 2020-03-07: fork from [bonfy](https://github.com/bonfy/leetcode), drop chromedriver requirement, change domain to www.leetcode-cn.com.
