"""
Created on May 5, 2017

@author: anthony
"""
import math
import tempfile
import urllib
from collections import deque
from threading import Thread
from time import sleep
from urllib.request import urlopen
from urllib.request import urlretrieve

import numpy as np
import requests
from PIL.PpmImagePlugin import PpmImageFile
from bs4 import BeautifulSoup
from numpy import long
from pdf2image import convert_from_path
from pytesseract import image_to_string


class GoogleSearch:
    USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/ 58.0.3029.81 Safari/537.36"
    SEARCH_URL = "https://google.com/search"
    RESULT_SELECTOR = "#rso .g .r a:first-child:not(.fl)"
    TOTAL_SELECTOR = "#result-stats"
    RESULTS_PER_PAGE = 10
    DEFAULT_HEADERS = {
        'User-Agent': USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    __total = None

    @staticmethod
    def build_request(url, headers=None):
        payload = {}
        headers = GoogleSearch.DEFAULT_HEADERS if headers is None else headers

        resp = requests.request("GET", url, headers=headers, data=payload)

        html = ''
        if resp.raw.headers.get('Content-Type') == 'application/pdf':
            tf = tempfile.NamedTemporaryFile()
            urlretrieve(url, tf.name)
            images = np.array(convert_from_path(tf.name), dtype=PpmImageFile.__class__)
            extracted_text = np.array([image_to_string(img, lang='por') for img in images])
            html = "\n".join(extracted_text)
        else:
            html = resp.text
        resp.close()

        return html

    def set_total(self, soup):
        if self.__total is None:
            element_html_total = soup.select(GoogleSearch.TOTAL_SELECTOR)
            total_text = element_html_total[0].encode('utf-8')
            self.__total = long(''.join(text for text in str(total_text) if text.isdigit()))

    def search(self, query, num_results=10, prefetch_pages=True, prefetch_threads=10):
        search_results = []
        pages = int(math.ceil(num_results / float(GoogleSearch.RESULTS_PER_PAGE)))
        fetcher_threads = deque([])
        for i in range(pages):
            start = i * GoogleSearch.RESULTS_PER_PAGE
            resp = GoogleSearch.build_request(GoogleSearch.SEARCH_URL + "?q=" + urllib.request.quote(query) + ("" if start == 0 else ("&start=" + str(start))))
            soup = BeautifulSoup(resp, "lxml")

            results = GoogleSearch.parse_results(soup.select(GoogleSearch.RESULT_SELECTOR))

            self.set_total(soup)

            if len(search_results) + len(results) > num_results:
                del results[num_results - len(search_results):]

            search_results += results
            if prefetch_pages:
                for result in results:
                    while True:
                        running = 0
                        for thread in fetcher_threads:
                            if thread.is_alive():
                                running += 1
                        if running < prefetch_threads:
                            break
                        sleep(1)
                    fetcher_thread = Thread(target=result.getText)
                    fetcher_thread.start()
                    fetcher_threads.append(fetcher_thread)
        for thread in fetcher_threads:
            thread.join()
        return SearchResponse(search_results, self.__total)

    @staticmethod
    def parse_results(results):
        return [SearchResult(result.text, result.get('href')) for result in results if result.get('href') and result.text]


class SearchResponse:
    def __init__(self, results, total):
        self.results = results
        self.total = total


class SearchResult:
    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.__text = None
        self.__markup = None

    def getText(self):
        markup = self.getMarkup()
        if self.__text is None and markup:
            soup = BeautifulSoup(markup, "lxml")
            for junk in soup(["script", "style"]):
                junk.extract()
                self.__text = soup.get_text()
        return self.__text

    def getMarkup(self):
        if self.__markup is None:
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'}
            self.__markup = GoogleSearch.build_request(self.url, headers)
        return self.__markup

    def __str__(self):
        return str(self.__dict__)

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return self.__str__()


if __name__ == "__main__":
    # search = GoogleSearch()
    # i = 1
    # query = " ".join(sys.argv[1:])
    # if len(query) == 0:
    #     query = "python"
    # count = 10
    # print("Fetching first " + str(count) + " results for \"" + query + "\"...")
    # response = search.search(query, count)
    # print("TOTAL: " + str(response.total) + " RESULTS")
    # for result in response.results:
    #     print("RESULT #" + str(i) + ": " + result.url + "\n\n")
    #     i += 1

    response = GoogleSearch.build_request(
        "https://ww2.stj.jus.br/processo/dj/documento?seq_documento=20012703&data_pesquisa=02/10/2018&parametro=42",
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'
        }
    )

    print(response)
