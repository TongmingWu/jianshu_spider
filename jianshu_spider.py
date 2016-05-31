import json
import re

import time

from flask import Flask, request, redirect, abort
from bs4 import BeautifulSoup
import requests
from flask.ext.script import Manager

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
    soup = BeautifulSoup(response, 'lxml')
    page = ''
    if category == '0':
        data_url = str(soup.select('.ladda-button')[0]['data-url']).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                       '[]')  # 加载更多的URL
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
    else:
        data_url = soup.select('.ladda-button')[0]['data-url']

    notes_id = re.findall(r'\d{3,}', data_url)  # 每篇文章的真正的id

    article_list, banner = parse_li(li=soup.select('.article-list > li'))
    L = [('count', len(article_list)), ('results', article_list),
         ('banner', banner),
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
    # soup = BeautifulSoup(r, 'lxml')
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

        soup = BeautifulSoup(r'<html>' + append + r'</html>', 'lxml')
        article_list, banner = parse_li(soup.select('li'))
        data_url = str(re.search(r'/top/daily.*', res).group(0).replace('/top/daily?', '').replace('%5B%5D',
                                                                                                   '[]'))  # 加载更多的URL
        page = re.search(r'page=\d{1,2}', data_url).group(0).replace('page=', '')
        notes_id = re.findall(r'\d{3,}', data_url)  # 每篇文章的真正的id
    else:
        url = domain + '/recommendations/notes?max_id=' + ids
        res = requests.get(url=url).text
        soup = BeautifulSoup(res, 'lxml')
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
    for article in li:
        img = None
        s = BeautifulSoup(r'<html>' + str(article) + r'</html>', 'lxml')
        if s.select('.have-img') != []:
            img = s.select('.wrap-img > img ')[0]['src']
            if len(banner) < 5:
                banner.append(str(img).replace(r'w/300', r'w/640').replace(r'h/300', r'h/240'))
        author_id = s.select('.author-name')[0]['href']
        res_author = requests.get(domain + author_id + '/latest_articles').text
        # res_author = urllib.request.urlopen(domain+author_id+'/latest_articles').read()
        author_soup = BeautifulSoup(res_author, 'lxml')
        avatar = author_soup.select('.avatar > img')[0]['src']
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
        # note_id = notes_id[index]

        if img is not None:
            L = [('author', author), ('date', date), ('title', title), ('read', read),
                 ('comment', comment), ('fav', fav), ('slug', slug), ('img', img), ('avatar', avatar)]
        else:
            L = [('author', author), ('date', date), ('title', title), ('read', read),
                 ('comment', comment), ('fav', fav), ('slug', slug), ('avatar', avatar),
                 ('img', str(avatar).replace('90x90', '200x200'))]
        article_dict = dict(L)
        article_list.append(article_dict)
    return article_list, banner


# 获取2015年每月一篇好文章
@app.route('/zodiac', methods=['GET'])
def get_zodiac():
    url = domain + '/zodiac/2015'
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'lxml')
    index = 1
    article_list = list()
    for article in soup.select('.swiper-wrapper > div'):
        s = BeautifulSoup(r'<html>' + str(article) + r'</html>', 'lxml')
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
    # slug = request.args['slug']
    url = domain + '/p/' + slug
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'lxml')
    # nid = re.search(r'\d+', re.search(r'notes/\d+', response).group(0)).group(0)
    avatar = soup.select('.avatar > img')[0]['src']
    title = soup.select('title')[0].string
    # author = soup.select('.author-name > span')[0].string
    created_at = str(soup.select('.author-info > span')[1].string)
    # end_edited = str(soup.select('.author-info > span')[1]['data-original-title']).replace('最后编辑于 ', '')
    num_list = soup.select('.author-info > div > span')
    font_count = re.search(r'\d+', str(num_list[0])).group(0)
    # att_num = re.search(r'\d+', str(num_list[1])).group(0)
    # like_num = re.search(r'\d+', str(num_list[2])).group(0)
    content = str(soup.select('.show-content')[0])
    # comment_num = re.search(r'\d+', str(soup.select('.comment-head')[0])).group(0)
    script_list = soup.find_all(name='script', type='application/json')
    note = script_list[0].string
    uuid = script_list[1].string
    json_note = dict(json.loads(note))
    json_note['title'] = title
    json_note['created_at'] = created_at
    # json_note['end_edited'] = end_edited
    json_note['content'] = content
    author = script_list[2].string
    json_author = dict(json.loads(author))
    json_author['avatar'] = avatar
    json_author['font_count'] = font_count
    if len(script_list) > 3:
        current_user = script_list[3].string
        print(current_user)

    # text = ''
    # for p in content:
    #     text += str(p)
    # L = [('img', img), ('slug', slug), ('id', nid), ('author', author), ('created_at', created_at),
    #      ('end_edited', end_edited), ('comment_num', comment_num),
    #      ('font_num', font_num), ('att_num', att_num), ('like_num', like_num), ('title', title),
    #      ('content', content)]
    # dic = dict(L)
    # json_data = json.dumps(dic, ensure_ascii=False).replace(r'\"', '"').replace(r'"\\', '"').replace(r'\n', '')
    json_data = '{"article":' + json.dumps(json_note,
                                           ensure_ascii=False).replace(r'"\\', '"').replace(r'\n',
                                                                                            '') + ',"uuid":' + uuid + ',"author":' + json.dumps(
            json_author, ensure_ascii=False) + '}'
    return json_data.encode('utf-8')


# 获取文章的评论
@app.route('/comment/<nid>', methods=['GET'])
def get_comment(nid):
    url = domain + '/notes/' + nid + '/comments'
    response = requests.get(url).text
    soup = BeautifulSoup(response, 'lxml')
    comment_list = soup.select('.note-comment')
    review_list = list()
    for comment in comment_list:
        s = BeautifulSoup(r'<html>' + str(comment) + r'</html>', 'lxml')
        avatar = s.select('.avatar > img')[0]['src']
        author = s.select('.author-name')[0].string
        floor = re.search(r'\d+', str(s.select('.reply-time > small')[0].string)).group(0)
        date = s.select('.reply-time > a')[0].string
        content = s.select('.content > p')[0].get_text()
        child_list = list()
        if s.select('.child-comment') is not None:
            child_comment_list = s.select('.child-comment')
            for child in child_comment_list:
                c = BeautifulSoup(r'<html>' + str(child) + r'</html>', 'lxml')
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
