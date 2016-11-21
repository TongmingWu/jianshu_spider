#!/usr/bin/python3
# coding=utf-8
from flask import Flask, redirect, request, render_template, abort
from bs4 import BeautifulSoup
import requests
from flask_script import Manager
import json
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


@app.route('/')
def home():
    return render_template('welcome.html')


# login
@app.route('/login', methods=['POST'])
def do_login():
    mobile_number = request.form.get('mobile_number')
    name = request.form.get('name')
    password = request.form.get('password')
    gee_url = 'http://120.25.101.52/gee/test.aspx'
    login = requests.session()
    res_login = login.get(url=domain + '/sign_in').text
    soup = BeautifulSoup(res_login, 'html5lib')
    gt = soup.select('.captcha > input')[1]['value']
    cap_id = soup.select('.captcha > input')[4]['value']
    token = soup.select('.form-horizontal > input')[1]['value']
    # driver = webdriver.PhantomJS()
    # driver.get(gee_url)
    # gt_input = driver.find_element_by_id('txtGT')
    # gt_input.clear()
    # gt_input.send_keys(gt)
    # btn = driver.find_element_by_id('test')
    # btn.click()
    # source = driver.page_source
    gee_s = requests.session()
    source = gee_s.get(gee_url).text
    gee_soup = BeautifulSoup(source, 'html.parser')
    __VIEWSTATE = gee_soup.select('#__VIEWSTATE')[0]['value']
    __VIEWSTATEGENERATOR = gee_soup.select('#__VIEWSTATEGENERATOR')[0]['value']
    __EVENTVALIDATION = gee_soup.select('#__EVENTVALIDATION')[0]['value']
    txtSite = 'http://www.geetest.com/'
    data = {
        '__VIEWSTATE': __VIEWSTATE,
        '__VIEWSTATEGENERATOR': __VIEWSTATEGENERATOR,
        '__EVENTVALIDATION': __EVENTVALIDATION,
        'txtGT': gt,
        'txtSite': gee_url,
        'test': 'test'
    }
    source = gee_s.post(gee_url, data=data).text
    while True:
        if re.search(r'"success"', source):
            validate = re.search(r'validate: "(.*?)"', source).group(0).replace('validate: ', '').replace('"', '')
            challenge = re.search(r'challenge: "(.*?)"', source).group(0).replace('challenge: ', '').replace('"', '')
            break
        else:
            source = gee_s.post(gee_url, data=data).text
            time.sleep(1)
    data = {
        'utf8': '✓',
        'authenticity_token': token,
        'sign_in[country_code]': 'CN',
        'sign_in[mobile_number]': mobile_number,
        'sign_in[name]': name,
        'sign_in[password]': password,
        'sign_in[is_foreign]': False,
        'captcha[validation][challenge]': challenge,
        'captcha[validation][gt]': gt,
        'captcha[validation][validate]': validate,
        'captcha[validation][seccode]': validate + '|jordan',
        'captcha[id]': cap_id,
        'geetest_challenge': challenge,
        'geetest_validate': validate,
        'geetest_seccode': validate + '|jordan',
        'sign_in[remember_me]': False
    }
    result = login.post(url=domain + '/sessions', data=data).text
    soup = BeautifulSoup(result, 'html.parser')
    if soup.select('#current_user_id'):
        current_user_id = soup.select('#current_user_id')[0]['value']
        current_user_slug = soup.select('#current_user_slug')[0]['value']
        user_info = json.loads(get_user_latest_articles(current_user_slug).decode('utf-8'))
        return json.dumps({'user_id': current_user_id, 'user_slug': current_user_slug,
                           'status_code': 200, 'user_info': user_info},
                          ensure_ascii=False)
    else:
        return abort(404)


# hot
@app.route('/hot', methods=['GET'])
def get_hot():
    return get_category(domain, category='0'), 200


# other article
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


# weekly
@app.route('/weekly', methods=['GET'])
def get_weekly():
    url = domain + '/trending/weekly'
    return get_category(url), 200


# monthly
@app.route('/monthly', methods=['GET'])
def get_monthly():
    url = domain + '/trending/monthly'
    return get_category(url), 200


# 获取各分类文章
def get_category(url, category=None):
    start = time.time()
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    page = ''
    if category == '0':
        data_url = str(soup.select('.ladda-button')[0]['data-url']).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                       '[]')  # load_more
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
    else:
        data_url = soup.select('.ladda-button')[0]['data-url']

    notes_id = re.findall(r'\d{3,}', data_url)  # the article real id
    article_list, banner, avatar_list = parse_li(li=soup.select('.article-list > li'), get_avatar=True)
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
    print(str(time.time() - start))
    return json_data.encode('utf-8')


@app.route('/more/hot/<ids>', methods=['GET'])
def load_hot(ids):
    return load_more(ids=ids, category='0')


@app.route('/more/normal/<ids>', methods=['GET'])
def load_normal(ids):
    return load_more(ids=ids, category='1')


def load_more(ids, category):
    t = int(time.time())
    headers = {
        'Accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }
    page = ''
    if category == '0':
        print(ids)
        url = domain + '/top/daily?' + ids + '_=' + str(t)
        res = requests.get(url=url, headers=headers).text
        append = re.findall(r'append(.*)', res)[0].replace(r'("', '').replace(r'")', '') \
            .replace('\\n', '').replace('\\', '')

        soup = BeautifulSoup(r'<html>' + append + r'</html>', 'html.parser')
        article_list, banner, avatar_list = parse_li(soup.select('li'), get_avatar=True)
        i = 0
        for li in article_list:
            li['avatar'] = avatar_list[i]
            if li['img'] == None:
                li['img'] = str(avatar_list[i]).replace('90x90', '200x200')
            i += 1
        data_url = str(re.search(r'/top/daily.*', res).group(0).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                   '[]'))
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
        notes_id = re.findall(r'\d{3,}', data_url)
    else:
        url = domain + '/recommendations/notes?max_id=' + ids
        res = requests.get(url=url).text
        soup = BeautifulSoup(res, 'html.parser')
        article_list, banner, avatar_list = parse_li(li=soup.select('.article-list > li'), get_avatar=True)
        data_url = soup.select('.ladda-button')[0]['data-url']
        notes_id = re.findall(r'\d{3,}', data_url)
    L = [('results', article_list), ('page', page), ('ids', notes_id), ('banner', banner), ('count', len(article_list))]
    dic = dict(L)
    json_data = json.dumps(dic, ensure_ascii=False)
    return json_data.encode('utf-8')


def parse_li(li, get_avatar=False):
    article_list = list()
    banner = list()
    urls = []
    avatar_list = []

    if get_avatar is True:
        ind = 0
        for article in li:
            if len(article.select('.app-download-btn')) == 0:
                author_id = article.select('.author-name')[0]['href']
                urls.append(domain + author_id + '/latest_articles')
                ind += 1
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
        if len(article.select('.app-download-btn')) == 0:
            img = None
            if re.search('have-img', str(article)):
                img = article.select('.wrap-img > img ')[0]['src']
                if len(banner) < 5:
                    banner.append(str(img).replace(r'w/300', r'w/640').replace(r'h/300', r'h/200'))
            author_slug = article.select('.author-name')[0]['href'].replace('/users/', '')
            avatar = None
            author = article.select('.author-name')[0].string
            date = str(article.select('span')[0]['data-shared-at']).replace('T', ' ').replace('+08:00', '')
            title = article.select('.title')[0].string
            if len(article.select('.list-footer > a')) <= 1:
                read = re.search(r'\d+', article.select('.list-footer > a')[0].string).group(0)
            else:
                read = re.search(r'\d+', article.select('.list-footer > a')[0].string).group(0)
                comment = re.search(r'\d+', article.select('.list-footer > a')[1].string).group(0)
            fav = re.search(r'\d+', article.select('.list-footer > span')[0].string).group(0)
            slug = str(article.select('h4 > a')[0]['href']).replace(r'/p/', '')

            if img is not None:
                L = [('author', author), ('date', date), ('title', title), ('read', read),
                     ('comment', comment), ('fav', fav), ('slug', slug), ('author_slug', author_slug), ('img', img),
                     ('avatar', avatar)]
            else:
                L = [('author', author), ('date', date), ('title', title), ('read', read),
                     ('comment', comment), ('fav', fav), ('slug', slug), ('author_slug', author_slug), ('avatar', avatar),
                     ('img', img)]
            article_dict = dict(L)
            article_list.append(article_dict)
    return article_list, banner, avatar_list


def parse_urls(urls):
    rs = (grequests.get(u) for u in urls)
    resulsts = grequests.map(rs)
    avatar_list = list()
    for response in resulsts:
        if response.status_code == 200:
            author_soup = BeautifulSoup(response.text, 'html.parser')
            avatar = author_soup.select('.avatar > img')[0]['src']
            avatar_list.append(str(avatar))
        elif response.status_code == 503:
            print('request too fast')
    return avatar_list


# 2015
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


# article detail
@app.route('/detail/<slug>', methods=['GET'])
def get_detail(slug):
    url = domain + '/p/' + slug
    print(url)
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    avatar = soup.select('.avatar > img')[0]['src']
    # author_slug = soup.select('avatar')[0]['href'].replace('/users/', '')
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
    # json_author['author_slug'] = author_slug
    json_author['font_count'] = font_count
    if len(script_list) > 3:
        current_user = script_list[3].string
        print(current_user)
    json_data = '{"article":' + json.dumps(json_note,
                                           ensure_ascii=False).replace(r'"\\', '"').replace(r'\n',
                                                                                            '') + ',"uuid":' + uuid + ',"author":' + json.dumps(
            json_author, ensure_ascii=False) + '}'
    return json_data.encode('utf-8')


# collections
@app.route('/collections/<category>')
def get_collection(category):
    if category == '53':
        url = domain + '/collections'
    elif category == '58':
        url = domain + '/collections?category_id=58'
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    json_data = list()
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


# collection detail
@app.route('/collection/<slug>')
def get_collection_detail(slug):
    url = domain + '/collection/' + slug
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    title = soup.select('h3 > a')[0].string
    topic_avatar = soup.select('.header > img')[0]['src']
    desc = str(soup.select('.description')[0])
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
    article_list, banner, avatar_list = parse_li(soup.select('.article-list > li'), get_avatar=True)
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


# user detail
@app.route('/users/<slug>/latest_articles')
def get_user_latest_articles(slug):
    url = domain + '/users/' + slug + '/latest_articles'
    res = requests.get(url)
    if res.status_code == 404:
        return abort(404)
    soup = BeautifulSoup(res.text, 'html.parser')
    avatar = soup.select('.avatar > img')[0]['src']
    nickname = soup.select('h3')[0].string
    about = str(soup.select('.about > p')[0].get_text())
    li = soup.select('.user-stats > ul')
    m = re.findall(r'<b>(\d+)</b>', str(li))
    subscription_num = m[0]
    follower_num = m[1]
    article_num = m[2]
    word_age = m[3]
    like_num = m[4]
    books = []
    if re.search('my-books', res.text):
        for li in soup.select('.my-books > ul > li'):
            book_id = re.search(r'\d+', str(li)).group(0)
            book_name = li.get_text()
            L = [('book_id', book_id), ('book_name', book_name)]
            books.append(dict(L))
    collections = []
    if re.search('my-collections', res.text):
        for li in soup.select('.my-collections > ul > li'):
            title = li.get_text()
            my_collection_slug = re.search(r'(?<=href=\").+?(?=\")', str(li)).group(0).replace(r'/collection/', '')
            L = [('title', title), ('slug', my_collection_slug)]
            collections.append(dict(L))
    latest_articles, banner, avatar_list = parse_li(soup.select('.latest-notes > li'))
    latest_article_page = 0
    for li in soup.select('.hidden > div > ul > li'):
        if re.search(r'\d+', str(li.get_text())):
            latest_article_page += 1
    # 用户关注的专题/文集
    sub_url = domain + '/users/' + slug + '/subscriptions'
    sub = requests.get(sub_url).text
    s = BeautifulSoup(sub, 'html.parser')
    notebooks_num = 0
    collection_num = 0
    sub_notebooks = []
    sub_collections = []
    for li in s.select('.subscribing > li'):
        if re.search('/collection', str(li)):
            collection_num += 1
            collection_slug = li.select('h4 > a')[0]['href'].replace('/collection/', '')
            collection_name = li.select('h4 > a')[0].string
            collection_author = li.select('.article-info > a')[0].string
            L = [('slug', collection_slug), ('name', collection_name), ('author', collection_author)]
            sub_collections.append(dict(L))
        else:
            notebooks_num += 1
            notebook_id = re.search('\d+', li.select('h4 > a')[0]['href']).group(0)
            notebook_name = li.select('h4 > a')[0].string
            notebook_author = li.select('.article-info > a')[0].string
            L = [('id', notebook_id), ('name', notebook_name), ('author', notebook_author)]
            sub_notebooks.append(dict(L))
    # 获取用户关注的专题的avatar
    urls = []
    for entry in sub_collections:
        urls.append(domain + '/collection/' + entry['slug'])
    rs = (grequests.get(u) for u in urls)
    resulsts = grequests.map(rs)
    for (response, entry) in zip(resulsts, sub_collections):
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            avatar = soup.select('.header > img')[0]['src']
            entry['avatar'] = avatar
        else:
            print('失败')
    # User所关注的用户
    following_url = domain + '/users/' + slug + '/following'
    following = requests.get(following_url).text
    s = BeautifulSoup(following, 'html.parser')
    user_list = s.select('.users > li')
    following_num = len(user_list)
    followings = []
    for li in user_list:
        following_avatar = li.select('.avatar > img')[0]['src']
        following_slug = li.select('a')[0]['href'].replace('/users/', '')
        following_nickname = li.select('h4 > a')[0].string
        fol_fol = re.search('\d+', li.select('p > a')[0].string).group(0)
        fol_followers = re.search('\d+', li.select('p > a')[1].string).group(0)
        fol_atricles = re.search('\d+', li.select('p > a')[1].string).group(0)
        L = [('avatar', str(following_avatar)), ('slug', following_slug), ('following_num', fol_fol),
             ('nickname', following_nickname),
             ('follower_num', fol_followers), ('article_num', fol_atricles)]
        followings.append(dict(L))

    # User的粉丝列表
    fans_url = domain + '/users/' + slug + '/followers'
    s = BeautifulSoup(requests.get(fans_url).text, 'html.parser')
    fans = []
    for li in s.select('.users > li'):
        fans_avatar = li.select('.avatar > img')[0]['src']
        fans_slug = li.select('.avatar')[0]['href'].replace('/users/', '')
        fans_name = li.select('h4 > a')[0].string
        a_list = li.select('p > a')
        fans_following = a_list[0].string
        fans_followers = a_list[1].string
        fans_articles = a_list[2].string
        fans_notebooks = a_list[3].string
        fans_article_info = li.select('.article-info')[0].string
        L = [('avatar', fans_avatar), ('slug', fans_slug), ('nickname', fans_name), ('following_num', fans_following),
             ('followers_num', fans_followers), ('articles_num', fans_articles), ('notebooks_num', fans_notebooks),
             ('article_info', fans_article_info)]
        fans.append(dict(L))

    L = [('slug', slug), ('avatar', avatar), ('nickname', nickname), ('about', str(about)),
         ('subscription_num', subscription_num), ('fans', fans),
         ('follower_num', follower_num), ('article_num', article_num), ('word_age', word_age),
         ('like_num', like_num), ('collection_num', collection_num), ('notebook_num', notebooks_num),
         ('books', books), ('collections', collections), ('latest_articles', latest_articles),
         ('page', latest_article_page), ('followings', followings), ('following_num', following_num),
         ('sub_collections', sub_collections),
         ('sub_notebooks', sub_notebooks)]
    return json.dumps(dict(L), ensure_ascii=False).encode('utf-8')


@app.route('/users/<slug>/top_articles')
def get_user_top_articles(slug):
    url = domain + '/users/' + slug + '/top_articles'
    res = requests.get(url).text
    soup = BeautifulSoup(res, 'html.parser')
    hot_articles, banner, avatar_list = parse_li(soup.select('.top-notes > li'))
    hot_article_page = 0
    for li in soup.select('.hidden > div > ul > li'):
        if re.search(r'\d+', str(li.get_text())):
            hot_article_page += 1
    L = [('hot_articles', hot_articles), ('page', hot_article_page)]
    return json.dumps(dict(L), ensure_ascii=False).encode('utf-8')


@app.route('/users/<slug>/timeline')
def get_user_timeline(slug):
    url = domain + '/users/' + slug + '/timeline'
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    nickname = soup.select('h3')[0].string
    trends = []  # 动态
    for li in soup.select('.timeline-content > li'):
        if len(li['class']) > 1:
            title = li.select('.article-content > a')[0].string
            action = nickname + ' 发表了 ' + title
            content = li.select('.article-content > p')[0].string
            category = 'issue'
            # comment_num = li.select('meta > a')[0].string
        if li['class'][0] == 'comment':
            action = li.select('p')[0].get_text()
            content = li.select('.comment-content')[0].get_text()
            data_user_slug = re.findall(r'data-user-slug="(.*?)"', str(li.select('.comment-content > a')))
            category = 'comment'
            if len(data_user_slug) > 0:
                data_user_slug = str(data_user_slug[0])
        if len(li['class']) == 1 and li['class'][0] == 'like-comment':
            # action = '关注'
            action = li.select('p')[0].get_text()
            content = li.select('.comment-content')[0].get_text()
            category = 'like-comment'
        if len(li['class']) == 1 and li['class'][0] == 'user-update':
            action = li.select('span')[0].get_text()
            content = None
            category = 'attention'
        avatar = li.select('.avatar > a > img')[0]['src']
        date = li.select('time')[0].string
        L = [('action', action), ('content', content), ('date', date), ('category', category), ('avatar', avatar)]
        trends.append(dict(L))
    return json.dumps(dict([('trends', trends)]), ensure_ascii=False).encode('utf-8')


# search
@app.route('/search/<q>')
def search(q):
    s = requests.session()
    s.get(domain + '/search?q=' + q + '&type=notes')
    s_type = ['notes', 'notebooks', 'collections', 'users']
    # proxy_pool = get_proxy()
    json_data = ''
    i = 0
    while i < len(s_type):
        t = s_type[i]
        url = domain + '/search/do?q=' + q + '&type=' + t
        # proxy = random.choice(proxy_pool)
        res = s.get(url=url
                    # , proxies={'http': proxy},timeout=1
                    )
        if res.status_code != 200:
            print('error')
            time.sleep(1)
            continue
        if t == 'users':
            json_data += '"' + t + '":' + res.text
            i += 1
        elif t == 'collections':
            dic = json.loads(res.text)
            urls = []
            for entry in dic['entries']:
                urls.append(domain + '/collection/' + entry['slug'])
            rs = (grequests.get(u) for u in urls)
            resulsts = grequests.map(rs)
            for (response, entry) in zip(resulsts, dic['entries']):
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    avatar = soup.select('.header > img')[0]['src']
                    entry['avatar'] = avatar
            data = json.dumps(dic, ensure_ascii=False)
            json_data += '"' + t + '":' + data + ','
            i += 1
        else:
            json_data += '"' + t + '":' + res.text + ','
            i += 1
    print('search succeed')
    return ('{' + json_data + '}').encode('utf-8')


# proxy_pool
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


# article comment
@app.route('/comment/<nid>', methods=['GET'])
def get_comment(nid):
    url = domain + '/notes/' + nid + '/comments'
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    comment_list = soup.select('.note-comment')
    review_list = list()
    for comment in comment_list:
        avatar = comment.select('.avatar > img')[0]['src']
        author = comment.select('.author-name')[0].string
        floor = re.search(r'\d+', str(comment.select('.reply-time > small')[0].string)).group(0)
        date = comment.select('.reply-time > a')[0].string
        content = comment.select('.content > p')[0].get_text()
        child_list = list()
        if comment.select('.child-comment') is not None:
            child_comment_list = comment.select('.child-comment')
            for child in child_comment_list:
                child_name = child.select('p > a')[0].string
                replay = re.search(r'@.*', child.select('p')[0].get_text()).group(0)
                replay_time = comment.select('.reply-time > a')[0].string
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
    manager.run()
