import argparse
import logging
import os
from datetime import datetime, timedelta
from typing import *

import pandas as pd
from transformers import BartForConditionalGeneration
from transformers import PreTrainedTokenizerFast

from hkrequests import HKRequests
from pdf_analysis import PdfAnalysis

os.environ["TOKENIZERS_PARALLELISM"] = "true"
logger = logging.getLogger('transformers.tokenization_utils_base')
logger.setLevel(logging.ERROR)

if __name__ == '__main__':
    now = datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', default=str((now - timedelta(days=7)).date()))
    parser.add_argument('--end-date', default=str((now - timedelta(days=0)).date()))

    args = parser.parse_args()

    try:
        model = BartForConditionalGeneration.from_pretrained('gogamza/kobart-summarization').eval()
        tokenizer = PreTrainedTokenizerFast.from_pretrained('gogamza/kobart-summarization')

        analyzer = PdfAnalysis(_model=model, _tokenizer=tokenizer)
        hk_reports = HKRequests(_sdate=args.start_date, _edate=args.end_date, _analyzer=analyzer)

        reports_data: List[Dict] = hk_reports.request()
        print(f'sample : {reports_data[0:1]}')
        df = pd.DataFrame.from_dict(reports_data)
        df.to_csv('res/csv/dataset.csv', encoding='utf-8-sig')

    except AssertionError as e:
        # 한경컨센서스에 올라온 리포트가 없을 때
        print(e)
