import os
import logging
import argparse

from hkrequests import HKRequests
from pdf_analysis import PdfAnalysis

from datetime import datetime, timedelta
from typing import *

from transformers import BartForConditionalGeneration
from transformers import PreTrainedTokenizerFast

os.environ["TOKENIZERS_PARALLELISM"] = "true"
logger = logging.getLogger('transformers.tokenization_utils_base')
logger.setLevel(logging.ERROR)

if __name__ == '__main__':
    now = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', default=str((now - timedelta(days=90)).date()))
    parser.add_argument('--end-date', default=str(now.date()))

    args = parser.parse_args()

    try:
        model = BartForConditionalGeneration.from_pretrained('gogamza/kobart-summarization').eval()
        tokenizer = PreTrainedTokenizerFast.from_pretrained('gogamza/kobart-summarization')

        analyzer = PdfAnalysis(_model=model, _tokenizer=tokenizer)
        hk_reports = HKRequests(_sdate=args.start_date, _edate=args.end_date, _analyzer=analyzer)

        reports_data: List[Dict] = hk_reports.request()
        print(f'sample : {reports_data[0:1]}')

        """
        Insert to DB 
        """

    except AssertionError as e:
        # 한경컨센서스에 올라온 리포트가 없을 때
        print(e)



