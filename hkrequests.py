from typing import *
import pandas as pd
import requests


class HKRequests:
    """
    날짜 포맷 : 2022-01-01
    _sdate : start date(시작날짜)
    _edate : end date(종료날짜)
    투자 의견 : [BUY, HOLD, NR, OUTPERFORM, REDUCE, STRONGBUY, SUSPENDED, TRADINGBUY, UNDERPERFORM, ...]
    """
    def __init__(self, _sdate: str, _edate: str, _analyzer):
        self.target_corp = {'대신증권', '유안타증권', '유진투자증권', '키움증권', '하이투자증권'}
        self.suggestion_correction = {'-': 'NR', 'NOTRATED': 'NR', 'NA': 'NR', 'N/A': 'NR', '중립': 'HOLD',
                                      '매수': 'BUY', 'MARKETPERFORM': 'HOLD', 'NEUTRAL': 'HOLD',
                                      '적극매수': 'STRONGBUY', '투자의견없음': 'NR'}

        self.url = 'https://markets.hankyung.com/api/consensus/search/report'
        self.params = {
            'page': 1,
            'reportType': 'CO',
            'fromDate': _sdate,
            'toDate': _edate,
            'gradeCode': 'ALL',
            'changePrices': 'ALL',
            'searchType': 'ALL',
        }

        self.analyzer = _analyzer

        self.last_page = self.__get_last_page()
        assert self.last_page >= 1, "잘못된 요청"

        self.category_file_path = 'corplist.csv'
        self.category_df = self.__get_category_dataframe()

    def __get_category_dataframe(self):
        return pd.read_csv(self.category_file_path, encoding='euc-kr', converters={'종목코드': lambda x: str(x)})

    def __get_last_page(self) -> int:
        with requests.get(url=self.url, params=self.params) as response:
            return response.json().get('last_page', 0)

    def request(self) -> List[Dict]:
        reports_list = []

        while self.params['page'] <= self.last_page:
            try:
                with requests.get(url=self.url, params=self.params) as response:
                    response_data = response.json().get('data', [])

                    if type(response_data) is dict:
                        response_data = response_data.values()

                    for report in response_data:
                        # 목표증권사가 아니면 reject
                        report_corp = report.get('OFFICE_NAME', '').replace(' ', '')
                        if report_corp not in self.target_corp:
                            continue

                        # 종목 코드가 없으면 reject
                        company_code = report.get('BUSINESS_CODE', '')
                        if not company_code:
                            continue

                        title = report.get('REPORT_TITLE', '')
                        company_name = report.get('BUSINESS_NAME', '')
                        report_date = report.get('REPORT_DATE', '')
                        pdf_link = report.get('REPORT_FILEPATH', '')
                        target_est = int(report.get('TARGET_STOCK_PRICES', 0))
                        writer = report.get('REPORT_WRITER', '')

                        suggestion = report.get('GRADE_VALUE', '').upper().replace(' ', '')
                        if suggestion in self.suggestion_correction:
                            suggestion = self.suggestion_correction[suggestion]

                        category = ''
                        label = self.category_df.loc[self.category_df['종목코드'] == company_code]['업종']
                        if not label.empty:
                            category = label.iloc[0]

                        # url -> 현재 주가, 기준 날짜, 리포트 요약
                        self.analyzer.analysis(pdf_link)
                        current_est: int = self.analyzer.current_est
                        current_est_date: str = self.analyzer.current_est_date
                        summary: str = self.analyzer.summary

                        report: Dict = {'title': title, 'company_name': company_name, 'company_code': company_code,
                                        'category': category, 'report_date': report_date, 'suggestion': suggestion,
                                        'writer': writer, 'report_corp': report_corp, 'target_est': target_est,
                                        'current_est': current_est, 'current_est_date': current_est_date,
                                        'pdf_link': pdf_link, 'summary': summary}

                        # 속성 값이 모두 비어있지 않은 경우만 리스트에 추가
                        if None not in report.values():
                            reports_list.append(report)

            except Exception as e:
                print(e, flush=True)
                return reports_list

            self.params['page'] += 1

        return reports_list
