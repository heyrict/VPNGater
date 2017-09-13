#!/usr/bin/env python3
from scrapy.selector import Selector
#from six.moves.urllib import request, parse, response
#from six.moves.urllib.request import urlretrieve
from urllib import request, parse, response
from urllib.request import urlretrieve
from selenium.webdriver import PhantomJS
import os, sys

HEAD = 10
last_percent_reported = None


def download_progress_hook(count, blockSize, totalSize):
    """A hook to report the progress of a download. This is mostly intended for users with
    slow internet connections. Reports every 5% change in download progress.
    """
    global last_percent_reported
    percent = int(count * blockSize * 100 / totalSize)

    if last_percent_reported != percent:
        if percent % 5 == 0:
            sys.stdout.write("%s%%" % percent)
            sys.stdout.flush()
        else:
            sys.stdout.write(".")
            sys.stdout.flush()

    last_percent_reported = percent


def download(filename, dest_filename):
    """Download a file if not present, and make sure it's the right size."""
    dest_filename = os.path.join('.', dest_filename)
    print('Attempting to download:', filename)
    filename, _ = urlretrieve(url + filename, dest_filename, reporthook=download_progress_hook)
    print('\nDownload Complete!')
    return dest_filename


def read_mirrors():
    print('Reading Mirrors')
    if os.path.exists('mirror_list.txt'):
        with open('mirror_list.txt') as f:
            mirror_list = [i for i in f.read().split('\n') if i]
            print("Found preserved mirror list:",end="\n    ")
            print("\n    ".join(mirror_list))
    else:
        mirror_list = ['http://119.193.36.149:27885/cn/',
                       'http://58.229.247.84:7279/cn/',
                       'http://121.151.8.16:62297/cn/',
                       'http://121.151.8.143:62297/cn/',
                       'http://27.35.35.241:63923/cn/',
                      ]

    mirror_list += ['http://www.vpngate.net']
    return mirror_list


def update_mirrors(url):
    # update mirrors
    print('Updating Mirrors..')
    mirrorurl = url + 'sites.aspx'
    for i in range(2):
        try:
            mirror_list = Selector(text=request.urlopen(mirrorurl).read())\
                    .xpath('.//ul[@class="listBigArrow"]/li/strong/span/a/@href')\
                    .extract()
            break
        except:
            if i == 1:
                print('Updating Mirrors Failed')
                return

    with open('mirror_list.txt','w') as f:
        f.write('\n'.join([url]+mirror_list))
    print('Updating Mirrors Succeeded')


def get_ovpn(url, save_to):
    page = Selector(text=request.urlopen(url).read())\
            .xpath('.//ul[@class="listBigArrow"]/li/a')
    cururl = url.rsplit('/',2)[0]
    for link in page:
        if link.xpath('./strong/text()').extract_first().find('UDP') > 0:
            download(cururl+link.xpath('./@href').extract_first(), save_to+'UDP.ovpn')
        elif link.xpath('./strong/text()').extract_first().find('TCP') > 0:
            download(cururl+link.xpath('./@href').extract_first(), save_to+'TCP.ovpn')
        else:
            download(cururl+link.xpath('./@href').extract_first(), save_to+'.ovpn')


def main():
    global HEAD
    if len(sys.argv) > 1:
        try: HEAD = int(sys.argv[1])
        except: HEAD = 10
    # test mirror list
    mirror_list = read_mirrors()
    for i in mirror_list:
        try:
            cururl = i
            print("Testing:",i)
            res = request.urlopen(i)
        except:
            print("Testing on",i,"failed")
            continue
        break
    update_mirrors(cururl)

    try: res
    except: raise Warning('All mirrors unavailable!')
    print('Available mirror:',cururl)

    # get vpn table
    countries = dict()
    dr = PhantomJS()
    dr.get(cururl)
    page = Selector(text=dr.page_source)\
            .xpath('.//td[@id="vpngate_inner_contents_td"]/'
                    'table[@id="vg_hosts_table_id"]//tr')

    if HEAD < len(page): page = page[:HEAD]

    print('Pagelen:',len(page))

    for vpn in page:
        if len(vpn.xpath('./td[@class="vg_table_header"]')) > 0:
            continue

        row = vpn.xpath('./td')
        country = row[0].xpath('./text()').extract_first()
        country = '_'.join(country.split(' '))
        ovpn = row[6].xpath('./a/@href').extract_first()

        if ovpn:
            if country in countries:
                countries[country] += 1
                get_ovpn(url=cururl+ovpn, save_to=country+'/'+str(countries[country]))
            else:
                countries[country] = 0
                if not os.path.exists(country):
                    os.mkdir(country)
                get_ovpn(url=cururl+ovpn, save_to=country+'/'+str(countries[country]))

    dr.quit()


main()
