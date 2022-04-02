import os
import re
from datetime import datetime
# from pykospacing import Spacing
# from hanspell import spell_checker
from typing import List

import kss
import requests
import torch
from tika import parser
from transformers import BartForConditionalGeneration
from transformers import PreTrainedTokenizerFast

os.environ["TOKENIZERS_PARALLELISM"] = "true"


class PdfAnalysis:
    max_content_len = 3000  # 리포트 초반의 의견 부분만 처리 -> 문장 분리 속도 고려
    max_sent_len = 500  # 전문가 의견 문장의 최대 길이

    def __init__(self):
        self.model = BartForConditionalGeneration.from_pretrained('gogamza/kobart-summarization').eval()
        self.tokenizer = PreTrainedTokenizerFast.from_pretrained('gogamza/kobart-summarization')
        self.resource = None
        self.content = None
        self.current_est = None
        self.current_est_date = None
        self.summary = None

    def analysis(self, resource: str):
        self.resource = resource
        self.content = self.__get_text()
        self.current_est, self.current_est_date = self.__get_current_est_info()
        self.summary = self.__get_summary()

    def __get_text(self) -> str:
        # url로 텍스트 추출
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/51.0.2704.103 Safari/537.36'}
        with requests.get(url=self.resource, headers=headers) as req:
            response = parser.from_buffer(req.content)
        text: str = response['content'].strip()
        text: str = re.sub('\n', ' ', text)
        return text

    def __get_current_est_info(self):
        try:
            text: str = re.search(r'[^목표]{3}[주종]가\(?[^A-Za-z가-힣]*\)?[\d,]+', self.content).group()[3:]
            raw_current_est: str = re.search(r'\s[\d,]+', text).group().strip().replace(',', '')
            # 현재 주가
            current_est: int = int(raw_current_est) if raw_current_est.isdigit() else 0
            # 현재 주가 기준 날짜
            year = str(datetime.today().year)
            date_text: str = re.sub(r'[/.]', '-', re.search(r'\([\d./]+\)', text).group()[1:-1].strip())
            date_text = year + '-' + date_text if date_text.count('-') < 2 else date_text
            date_text = year[:2] + date_text if date_text.find('-') == 2 else date_text
            date_obj = datetime.strptime(date_text, '%Y-%m-%d')
            current_est_date = str(date_obj.date())
        except AttributeError as e:
            print(e, flush=True)
            return '', ''

        return current_est, current_est_date

    def __get_summary(self) -> str:
        # 필요 없는 정보, 특수문자 제거
        self.content = self.content[:self.max_content_len]
        self.content = re.sub(r'\([^가-힣]{1,30}\)', '', self.content)  # (QoQ -21%, YoY 6%)
        self.content = re.sub(r'\d\)', '', self.content)  # 1) 2) 3) ..
        self.content = re.sub(r'\s+[\->]\s+', '. ', self.content)

        # 문장 분리 (kss, 마침표(.))
        split_sent = kss.split_sentences(
            text=self.content,
            backend="mecab")  # 문장분리 속도 증가
        opinion_sent = []
        for sent in split_sent:
            opinion_sent += sent.split('. ')

        # 전문가 의견 문장만 추출
        opinion_sent: List[str] = [sent for sent in opinion_sent
                                   if 10 < len(sent) < 200
                                   and len(re.findall(r'\s[^가-힣]{1,10}\s', sent)) < 6
                                   and len(re.findall(r'표\d', sent)) == 0]
        opinion: str = '. '.join(opinion_sent)

        # 문장요약 알고리즘
        raw_input_ids = self.tokenizer.encode(opinion)
        input_ids = [self.tokenizer.bos_token_id] + raw_input_ids + [self.tokenizer.eos_token_id]
        summary_ids = self.model.generate(torch.tensor([input_ids]),
                                          max_length=256,
                                          early_stopping=True,
                                          repetition_penalty=12.0)
        summary: str = self.tokenizer.decode(summary_ids.squeeze().tolist(), skip_special_tokens=True)

        return summary


if __name__ == '__main__':
    # example
    url = 'https://consensus.hankyung.com/apps.analysis/analysis.downpdf?report_idx=606859'
    pa = PdfAnalysis()
    pa.analysis(url)
    print(pa.current_est)
    print(pa.current_est_date)
    print(pa.summary)
