# Analysis Pipeline

| #   | Analysis                     | Module         | What it produces                                                                              |
| --- | ---------------------------- | -------------- | --------------------------------------------------------------------------------------------- |
| 1   | **Basic Stats**              | `analysis.py`  | Token count from cleaned/tokenized text                                                       |
| 2   | **Section Extraction**       | `sections.py`  | Splits transcript into **Prepared Remarks** and **Q&A** sections                              |
| 3   | **Speaker Identification**   | `sections.py`  | Enriched speaker profiles with **role** (executive/analyst/operator), **title**, and **firm** |
| 4   | **Q&A Exchanges**            | `sections.py`  | Structured question-answer threads grouped by analyst                                         |
| 5   | **Keywords** (TF-IDF)        | `keywords.py`  | Top 20 salient **terms and bigrams** ranked by importance                                     |
| 6   | **Themes** (NMF)             | `themes.py`    | 5 **topic clusters** of related terms representing major discussion areas                     |
| 7   | **Key Takeaways** (TextRank) | `takeaways.py` | Top 10 most **central statements** with speaker attribution                                   |

Layers 1–4 are structural (parsing _who said what_), while 5–7 are conceptual (understanding _what matters_).
