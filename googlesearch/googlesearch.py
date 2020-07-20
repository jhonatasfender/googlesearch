'''
Created on May 5, 2017

@author: anthony
'''
import math
import re
import urllib
from collections import deque
from threading import Thread
from time import sleep
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from numpy import long


class GoogleSearch:
    USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/ 58.0.3029.81 Safari/537.36"
    SEARCH_URL = "https://google.com/search"
    RESULT_SELECTOR = "#rso .g .r a:first-child:not(.fl)"
    TOTAL_SELECTOR = "#result-stats"
    RESULTS_PER_PAGE = 10
    DEFAULT_HEADERS = {
        'User-Agent': USER_AGENT,
        "Accept-Language": "en-US,en;q=0.5",
    }

    __total = None

    @staticmethod
    def build_request(url):
        req = Request(url)
        req.headers = GoogleSearch.DEFAULT_HEADERS

        response = urlopen(req)
        hmlt = response.read()
        response.close()

        return hmlt

    def set_total(self, soup):
        if self.__total is None:
            totalText = soup.select(GoogleSearch.TOTAL_SELECTOR)[0].encode('utf-8')
            self.__total = long(''.join(text for text in str(totalText) if text.isdigit()))

    def search(self, query, num_results=10, prefetch_pages=True, prefetch_threads=10):
        searchResults = []
        pages = int(math.ceil(num_results / float(GoogleSearch.RESULTS_PER_PAGE)))
        fetcher_threads = deque([])
        total = None
        for i in range(pages):
            start = i * GoogleSearch.RESULTS_PER_PAGE
            response = GoogleSearch.build_request(GoogleSearch.SEARCH_URL + "?q=" + urllib.request.quote(query) + ("" if start == 0 else ("&start=" + str(start))))
            soup = BeautifulSoup(response, "lxml")

            results = GoogleSearch.parseResults(soup.select(GoogleSearch.RESULT_SELECTOR))

            self.set_total(soup)

            if len(searchResults) + len(results) > num_results:
                del results[num_results - len(searchResults):]

            searchResults += results
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
        return SearchResponse(searchResults, total)

    @staticmethod
    def parseResults(results):
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
        if self.__text is None:
            soup = BeautifulSoup(self.getMarkup(), "lxml")
            for junk in soup(["script", "style"]):
                junk.extract()
                self.__text = soup.get_text()
        return self.__text

    def getMarkup(self):
        if self.__markup is None:
            self.__markup = GoogleSearch.build_request(self.url)
        return self.__markup

    def __str__(self):
        return str(self.__dict__)

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return self.__str__()


if __name__ == "__main__":
    import sys

    search = GoogleSearch()
    i = 1
    query = " ".join(sys.argv[1:])
    if len(query) == 0:
        query = "python"
    count = 10
    print("Fetching first " + str(count) + " results for \"" + query + "\"...")
    response = search.search(query, count)
    print("TOTAL: " + str(response.total) + " RESULTS")
    for result in response.results:
        print("RESULT #" + str(i) + ": " + result.getText() + "\n\n")
        i += 1
