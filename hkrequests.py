import re
from typing import *
import requests
from bs4 import BeautifulSoup


class HKRequests:
    # 날짜 포맷 : 2022-01-01
    # _sdate : start date(시작날짜)
    # _edate : end date(종료날짜)
    # 투자 의견 : [BUY, HOLD, NR, OUTPERFORM, REDUCE, STRONGBUY, SUSPENDED, TRADINGBUY, UNDERPERFORM, ...]
    def __init__(self, _sdate: str, _edate: str, _analyzer):
        self.target_corp = {'대신증권', '유안타증권', '유진투자증권', '키움증권' '하이투자증권'}  # '한양증권', '한화투자증권'
        self.suggestion_correction = {'-': 'NR', 'NOTRATED': 'NR', 'NA': 'NR', 'N/A': 'NR', '중립': 'HOLD',
                                      '매수': 'BUY', 'MARKETPERFORM': 'HOLD', 'NEUTRAL': 'HOLD',
                                      '적극매수': 'STRONGBUY', '투자의견없음': 'NR'}

        self.url = 'https://consensus.hankyung.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/51.0.2704.103 Safari/537.36'
        }

        self.sdate = _sdate
        self.edate = _edate
        self.analyzer = _analyzer
        self.now_page = 1
        self.end_page = self.__get_end_page()
        assert self.end_page >= 1, "검색된 날짜에 리포트가 없음"

    def __get_end_page(self) -> int:
        params = {
            'report_type': 'CO', 'sdate': self.sdate, 'edate': self.edate, 'now_page': self.now_page, 'pagenum': 80
        }

        try:
            with requests.get(url=f'{self.url}/apps.analysis/analysis.list', headers=self.headers, params=params) as req:
                html = BeautifulSoup(req.content, 'html.parser')

                # 결과 없음
                if html.select('tr.listNone'):
                    return 0

                # 마지막 페이지 설정
                _end_page = html.select_one('a.btn.last')['href'].split('=').pop()
                return int(_end_page) if _end_page.isdigit() else 0

        except Exception as e:
            print(e, flush=True)
            return 0

    def request(self) -> List[Dict]:
        raw_code_compiler = re.compile(r'(\(\d{6}[\D]*)')
        company_code_compiler = re.compile(r'(\d{6})')
        reports_list = []

        while self.now_page <= self.end_page:
            params = {
                'report_type': 'CO', 'sdate': self.sdate, 'edate': self.edate, 'now_page': self.now_page, 'pagenum': 80
            }

            try:
                with requests.get(url=f'{self.url}/apps.analysis/analysis.list', headers=self.headers, params=params) as req:
                    html = BeautifulSoup(req.content, 'html.parser')

                    for tag in html.select('tbody>tr'):
                        # 목표증권사가 아니면 reject
                        report_corp = tag.select('td')[5].get_text().strip()
                        if report_corp not in self.target_corp:
                            continue

                        title: str = tag.select_one('div>strong').get_text().strip()
                        raw_code: Match = raw_code_compiler.search(title)

                        # 제목에 종목코드가 없으면 reject
                        if raw_code is None:
                            continue

                        in_raw_code: Match = company_code_compiler.search(raw_code.group())
                        company_code: str = in_raw_code.group() if in_raw_code is not None else '000000'
                        company_name: str = re.sub(pattern=r'[\[\(]([가-힣\w\s])+[\]\)]', repl='',
                                                   string=title[:raw_code.start()]).strip()

                        date: str = tag.select_one('.first.txt_number').get_text().strip()
                        raw_target_est: str = tag.select('td')[2].get_text().strip().replace(',', '')
                        target_est: int = int(raw_target_est) if raw_target_est.isdigit() else 0

                        suggestion = tag.select('td')[3].get_text().strip().upper().replace(' ', '')
                        if suggestion in self.suggestion_correction:
                            suggestion = self.suggestion_correction[suggestion]

                        writer: str = tag.select('td')[4].get_text().strip()
                        pdf_link: str = self.url + tag.select_one('a')['href']

                        # url -> 현재 주가, 기준 날짜, 리포트 요약
                        self.analyzer.analysis(pdf_link)
                        current_est: int = self.analyzer.current_est
                        current_est_date: str = self.analyzer.current_est_date
                        summary: str = self.analyzer.summary

                        report: Dict = {'title': title, 'company_name': company_name, 'company_code': company_code,
                                        'date': date, 'suggestion': suggestion, 'writer': writer, 'report_corp': report_corp,
                                        'target_est': target_est, 'current_est': current_est, 'current_est_date': current_est_date,
                                        'pdf_link': pdf_link, 'summary': summary}

                        # 속성 값이 모두 비어있지 않은 경우만 리스트에 추가
                        if None not in report.values():
                            reports_list.append(report)

            except Exception as e:
                print(e, flush=True)
                return reports_list

            self.now_page += 1

        return reports_list
