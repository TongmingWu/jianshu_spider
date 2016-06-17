from flask import Flask, request, redirect, abort
from bs4 import BeautifulSoup
import requests
from flask_script import Manager
import json
import random
import re
import time
import grequests
import configparser
import pymysql

pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.debug = True
manager = Manager(app)
domain = 'http://www.jianshu.com'


# 获取热门
@app.route('/hot', methods=['GET'])
def get_hot():
    return get_category(domain, category='0'), 200


# 获取其他类别的文章
@app.route('/article/<cid>', methods=['GET'])
def get_articles(cid):
    url = domain + '/recommendations/notes?category_id='
    if cid == '0':
        return redirect('/hot')
    elif cid == '1':
        url += '56'
        return get_category(url), 200
    elif cid == '2':
        url += '60'
        return get_category(url), 200
    elif cid == '3':
        return redirect('/weekly')
    elif cid == '4':
        return redirect('/monthly')
    elif cid == '5':
        url += '51'
        return get_category(url), 200
    elif cid == '6':
        url += '61'
        return get_category(url), 200
    elif cid == '7':
        url += '62'
        return get_category(url), 200
    elif cid == '8':
        url += '63'
        return get_category(url), 200
    else:
        return abort(404)


# 七日热门
@app.route('/weekly', methods=['GET'])
def get_weekly():
    url = domain + '/trending/weekly'
    return get_category(url), 200


# 三十日热门
@app.route('/monthly', methods=['GET'])
def get_monthly():
    url = domain + '/trending/monthly'
    return get_category(url), 200


# 获取各类别文章
def get_category(url, category=None):
    start = time.time()
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    page = ''
    if category == '0':
        data_url = str(soup.select('.ladda-button')[0]['data-url']).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                       '[]')  # 加载更多的URL
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
    else:
        data_url = soup.select('.ladda-button')[0]['data-url']

    notes_id = re.findall(r'\d{3,}', data_url)  # 每篇文章的真正的id

    article_list, banner, avatar_list = parse_li(li=soup.select('.article-list > li'))
    i = 0
    for li in article_list:
        # print(avatar_list[i])
        li['avatar'] = avatar_list[i]
        if li['img'] == None:
            li['img'] = str(avatar_list[i]).replace('90x90', '200x200')
        i += 1
    L = [('count', len(article_list)), ('results', article_list),
         ('banner', banner),
         # ('data_url', data_url),
         ('ids', notes_id),
         ('page', page)]
    article_dict = dict(L)
    json_data = json.dumps(article_dict, ensure_ascii=False)
    print(str(time.time() - start))  # 话费了6秒左右
    return json_data.encode('utf-8')


# 加载更多文章
@app.route('/more/hot/<ids>', methods=['GET'])
def load_hot(ids):
    return load_more(ids=ids, category='0')


@app.route('/more/normal/<ids>', methods=['GET'])
def load_normal(ids):
    return load_more(ids=ids, category='1')


def load_more(ids, category):
    t = int(time.time())
    # session = requests.session()
    # r = requests.get(domain, cookies=session.cookies).text
    # soup = BeautifulSoup(r, 'html.parser')
    # token = str(soup.find_all('meta')[12]['content'])
    headers = {
        'Accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01',
        # 'X-CSRF-Token': token,
        'X-Requested-With': 'XMLHttpRequest'
    }
    page = ''
    if category == '0':
        url = domain + '/top/daily?' + ids + '_=' + str(t)
        res = requests.get(url=url, headers=headers).text
        append = re.findall(r'append(.*)', res)[0].replace(r'("', '').replace(r'")', '') \
            .replace('\\n', '').replace('\\', '')

        soup = BeautifulSoup(r'<html>' + append + r'</html>', 'html.parser')
        article_list, banner, avatar_list = parse_li(soup.select('li'))
        i = 0
        for li in article_list:
            # print(avatar_list[i])
            li['avatar'] = avatar_list[i]
            if li['img'] == None:
                li['img'] = str(avatar_list[i]).replace('90x90', '200x200')
            i += 1
        data_url = str(re.search(r'/top/daily.*', res).group(0).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                   '[]'))  # 加载更多的URL
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
        notes_id = re.findall(r'\d{3,}', data_url)  # 每篇文章的真正的id
    else:
        url = domain + '/recommendations/notes?max_id=' + ids
        res = requests.get(url=url).text
        soup = BeautifulSoup(res, 'html.parser')
        article_list, banner = parse_li(li=soup.select('.article-list > li'))
        data_url = soup.select('.ladda-button')[0]['data-url']
        notes_id = re.findall(r'\d{3,}', data_url)
    L = [('results', article_list), ('page', page), ('ids', notes_id), ('banner', banner), ('count', len(article_list))]
    dic = dict(L)
    json_data = json.dumps(dic, ensure_ascii=False)
    return json_data.encode('utf-8')


def parse_li(li):
    article_list = list()
    banner = list()
    urls = []

    for article in li:
        s = BeautifulSoup(r'<html>' + str(article) + r'</html>', 'html.parser')
        author_id = s.select('.author-name')[0]['href']
        urls.append(domain + author_id + '/latest_articles')
    urls_first = urls[0:5]
    urls_second = urls[5:10]
    avatar_list = parse_urls(urls_first)
    avatar_list.extend(parse_urls(urls_second))
    if len(urls) > 10:
        urls_third = urls[10:15]
        urls_fourth = urls[15:]
        avatar_list.extend(parse_urls(urls_third))
        avatar_list.extend(parse_urls(urls_fourth))

    for article in li:
        img = None
        s = BeautifulSoup(r'<html>' + str(article) + r'</html>', 'html.parser')
        if s.select('.have-img') != []:
            img = s.select('.wrap-img > img ')[0]['src']
            if len(banner) < 5:
                banner.append(str(img).replace(r'w/300', r'w/640').replace(r'h/300', r'h/240'))
        # author_id = s.select('.author-name')[0]['href']
        avatar = None
        author = s.select('.author-name')[0].string
        date = str(s.select('span')[0]['data-shared-at']).replace('T', ' ').replace('+08:00', '')
        title = s.select('.title')[0].string
        if len(s.select('.list-footer > a')) <= 1:
            read = re.search(r'\d+', s.select('.list-footer > a')[0].string).group(0)
        else:
            read = re.search(r'\d+', s.select('.list-footer > a')[0].string).group(0)
            comment = re.search(r'\d+', s.select('.list-footer > a')[1].string).group(0)
        fav = re.search(r'\d+', s.select('.list-footer > span')[0].string).group(0)
        slug = str(s.select('h4 > a')[0]['href']).replace(r'/p/', '')

        if img is not None:
            L = [('author', author), ('date', date), ('title', title), ('read', read),
                 ('comment', comment), ('fav', fav), ('slug', slug), ('img', img), ('avatar', avatar)]
        else:
            L = [('author', author), ('date', date), ('title', title), ('read', read),
                 ('comment', comment), ('fav', fav), ('slug', slug), ('avatar', avatar),
                 ('img', img)]
        article_dict = dict(L)
        article_list.append(article_dict)
    return article_list, banner, avatar_list


def exception_handler(request, exception):
    print('Request failed')


def parse_urls(urls):
    rs = (grequests.get(u) for u in urls)
    resulsts = grequests.map(rs, exception_handler=exception_handler)
    avatar_list = list()
    for response in resulsts:
        if response.status_code == 200:
            author_soup = BeautifulSoup(response.text, 'html.parser')
            avatar = author_soup.select('.avatar > img')[0]['src']
            avatar_list.append(str(avatar))
        elif response.status_code == 503:
            print('请求过快')
    return avatar_list


# 获取2015年每月一篇好文章
@app.route('/zodiac', methods=['GET'])
def get_zodiac():
    url = domain + '/zodiac/2015'
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    index = 1
    article_list = list()
    for article in soup.select('.swiper-wrapper > div'):
        s = BeautifulSoup(r'<html>' + str(article) + r'</html>', 'html.parser')
        article_url = str(s.select('div')[0]['src']).replace(r'/p/', '')
        title = s.select('.article-title')[0].string
        content = str(s.select('.content')[0]).replace(r'<br/>', '').replace(r'<div class="content">', '').replace(
                r'</div>', '')
        avatar = s.select('.author > img')[0]['src']
        author = s.select('.name')[0].string
        L = [('article_url', article_url), ('title', title), ('content', content), ('avatar', avatar),
             ('author', author)]
        article_dict = dict(L)
        article_list.append(article_dict)
        index += 1
    json_data = json.dumps(article_list, ensure_ascii=False)
    return json_data.encode('utf-8')


# 获取文章详情
@app.route('/detail/<slug>', methods=['GET'])
def get_detail(slug):
    url = domain + '/p/' + slug
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    avatar = soup.select('.avatar > img')[0]['src']
    title = soup.select('title')[0].string
    created_at = str(soup.select('.author-info > span')[1].string)
    num_list = soup.select('.author-info > div > span')
    font_count = re.search(r'\d+', str(num_list[0])).group(0)
    content = str(soup.select('.show-content')[0])
    script_list = soup.find_all(name='script', type='application/json')
    note = script_list[0].string
    uuid = script_list[1].string
    json_note = dict(json.loads(note))
    json_note['title'] = title
    json_note['created_at'] = created_at
    json_note['content'] = content
    author = script_list[2].string
    json_author = dict(json.loads(author))
    json_author['avatar'] = avatar
    json_author['font_count'] = font_count
    if len(script_list) > 3:
        current_user = script_list[3].string
        print(current_user)
    json_data = '{"article":' + json.dumps(json_note,
                                           ensure_ascii=False).replace(r'"\\', '"').replace(r'\n',
                                                                                            '') + ',"uuid":' + uuid + ',"author":' + json.dumps(
            json_author, ensure_ascii=False) + '}'
    return json_data.encode('utf-8')


# 获取专题数据
@app.route('/collections/<category>')
def get_collection(category):
    if category == '53':
        url = domain + '/collections'
    elif category == '58':
        url = domain + '/collections?category_id=58'
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    json_data = list()
    # print(res.decode('gbk'))
    for zhuanti in soup.select('.collections-list > li'):
        s = BeautifulSoup('<html>' + str(zhuanti) + '</html>', 'html.parser')
        title = s.select('h5 > a')[0].string
        avatar = s.select('.avatar > img')[0]['src']
        collection_id = re.search('\d+', re.search(r'images/\d{1,3}', str(avatar)).group(0)).group(0)
        att_num = s.select('.follow > span')[0].string
        description = s.select('.description')[0].string
        href = s.a['href'].replace(r'/collection/', '')
        aticle_num = s.select('.blue-link')[0].string.replace('篇文章', '')
        L = [('title', title), ('avatar', avatar), ('att_num', att_num), ('description', description),
             ('article_num', aticle_num), ('collection_id', collection_id), ('slug', href)]
        dic = dict(L)
        json_data.append(dic)
    return ('{"results":' + json.dumps(json_data, ensure_ascii=False) + '}').encode('utf-8')


# 获取专题详细信息
@app.route('/collection/<slug>')
def get_collection_detail(slug):
    url = domain + '/collection/' + slug
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    title = soup.select('h3 > a')[0].string
    topic_avatar = soup.select('.header > img')[0]['src']
    desc = str(soup.select('.description')[0]).replace(' class="description"', '')
    a_list = soup.select('.author > a')
    i = 0
    admin_list = list()
    while i < len(a_list):
        if i == 0:
            article_num = a_list[i].string.replace('篇文章', '')
        else:
            admin_list.append(a_list[i].string)
        i += 1
    follow_num = soup.select('.follow > span')[0].string
    followers = list()
    for follower in soup.select('.unstyled > li'):
        name = re.search(r"(?<=data-nickname=\").+?(?=\")|(?<=data-nickname=\').+?(?=\')", str(follower)).group(0)
        date = re.search(r'(?<=data-created-at=\").+?(?=\")', str(follower)).group(0)
        avatar = re.search(r'(?<=src=\").+?(?=\")', str(follower)).group(0)
        href = re.search(r'(?<=href=\").+?(?=\")', str(follower)).group(0).replace(r'/user/', '')
        L = [('name', name), ('date', date), ('avatar', avatar), ('href', href)]
        dic = dict(L)
        followers.append(dic)
    article_list, banner, avatar_list = parse_li(soup.select('.article-list > li'))
    i = 0
    for li in article_list:
        # print(avatar_list[i])
        li['avatar'] = avatar_list[i]
        if li['img'] == None:
            li['img'] = str(avatar_list[i]).replace('90x90', '200x200')
        i += 1
    L = [('title', title), ('desc', desc), ('article_num', article_num), ('admin_list', admin_list),
         ('follow_num', follow_num), ('followers', followers), ('article_list', article_list),
         ('topic_avatar', topic_avatar)]
    json_data = json.dumps(dict(L), ensure_ascii=False).encode('utf-8')
    return json_data


# 搜索
@app.route('/search/<q>')
def search(q):
    # 存在问题:未登录用户10秒内只能搜索一次
    # 解决方案:利用代理ip(已解决),但速度过慢
    s = requests.session()
    s.get(domain + '/search?q=' + q + '&type=notes')
    s_type = ['notes', 'notebooks', 'collections', 'users']
    # proxy_pool = get_proxy()
    urls = []
    json_data = ''
    i = 0
    while i < len(s_type):
        t = s_type[i]
        url = domain + '/search/do?q=' + q + '&type=' + t
        urls.append(url)
        # proxy = random.choice(proxy_pool)
        res = s.get(url=url
                    # , proxies={'http': proxy},timeout=1
                    )
        if res.status_code != 200:
            continue
        else:
            i += 1
        if t == 'users':
            json_data += '"' + t + '":' + res.text
        else:
            json_data += '"' + t + '":' + res.text + ','
    return ('{' + json_data + '}').encode('utf-8')


# 获取代理ip池
def get_proxy():
    parser = configparser.ConfigParser()
    parser.read("config")
    conn = pymysql.connect(
            host=parser.get('mysql', 'db_host'),
            port=parser.getint('mysql', 'db_port'),
            user=parser.get('mysql', 'db_user'),
            passwd=parser.get('mysql', 'db_pass'),
            db=parser.get('mysql', 'db_name'),
            charset=parser.get('mysql', 'charset')
    )
    cur = conn.cursor()
    sql = 'select * from proxy where isUse = TRUE'
    cursor = cur.execute(sql)
    proxies = cur.fetchmany(cursor)
    proxy_pool = []
    for proxy in proxies:
        protocol = proxy[1]
        ip = proxy[2]
        port = proxy[3]
        proxy_pool.append(protocol + '://' + ip + ':' + port)
    return proxy_pool


# 获取文章的评论
@app.route('/comment/<nid>', methods=['GET'])
def get_comment(nid):
    url = domain + '/notes/' + nid + '/comments'
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    comment_list = soup.select('.note-comment')
    review_list = list()
    for comment in comment_list:
        s = BeautifulSoup(r'<html>' + str(comment) + r'</html>', 'html.parser')
        avatar = s.select('.avatar > img')[0]['src']
        author = s.select('.author-name')[0].string
        floor = re.search(r'\d+', str(s.select('.reply-time > small')[0].string)).group(0)
        date = s.select('.reply-time > a')[0].string
        content = s.select('.content > p')[0].get_text()
        child_list = list()
        if s.select('.child-comment') is not None:
            child_comment_list = s.select('.child-comment')
            for child in child_comment_list:
                c = BeautifulSoup(r'<html>' + str(child) + r'</html>', 'html.parser')
                child_name = c.select('p > a')[0].string
                replay = re.search(r'@.*', c.select('p')[0].get_text()).group(0)
                replay_time = s.select('.reply-time > a')[0].string
                tmp = [('name', child_name), ('replay', replay), ('replay_time', replay_time)]
                tmp_dict = dict(tmp)
                child_list.append(tmp_dict)
        L = [('avatar', avatar), ('author', author), ('floor', floor), ('date', date),
             ('content', content), ('child_list', child_list)]
        com_dict = dict(L)
        review_list.append(com_dict)
    L = [('results', len(review_list)), ('nid', nid), ('review_list', review_list)]
    dic = dict(L)
    json_data = json.dumps(dic, ensure_ascii=False)
    return json_data.encode('utf-8')


if __name__ == '__main__':
    # app.run('10.12.243.252', 5000)
    manager.run()
