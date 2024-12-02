# app/search_manager.py
import sqlite3
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class SearchResult:
    url: str
    title: str
    rank: int
    match_count: int

class SearchManager:
    def __init__(self, db_path: str = 'crawler.db', per_page: int = 5):
        self.db_path = db_path
        self.per_page = per_page

    def get_suggestions(self, query: str) -> Dict[str, List]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        word_suggestions = self._get_word_suggestions(cursor, query)
        page_suggestions = self._get_page_suggestions(cursor, query)

        conn.close()
        return {
            "words": word_suggestions,
            "pages": page_suggestions
        }

    def _get_word_suggestions(self, cursor, query: str) -> List[str]:
        cursor.execute("""
            SELECT DISTINCT word 
            FROM lexicon 
            WHERE word LIKE ? || '%'
            ORDER BY (
                SELECT COUNT(*) 
                FROM inverted_index 
                WHERE inverted_index.word_id = lexicon.word_id
            ) DESC
            LIMIT 5
        """, (query.lower(),))
        return [row[0] for row in cursor.fetchall()]

    def _get_page_suggestions(self, cursor, query: str) -> List[Dict]:
        cursor.execute("""
            SELECT url, title
            FROM doc_index
            WHERE LOWER(title) LIKE ?
            ORDER BY page_rank DESC
            LIMIT 3
        """, ('%' + query.lower() + '%',))
        return [{"title": row[1] if row[1] else row[0], "url": row[0]}
                for row in cursor.fetchall()]

    def search(self, keywords: str, page: int = 1, per_page: int = 5) -> Tuple[List[SearchResult], Dict[str, int], int]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        keyword_list = keywords.split()
        result_counts = {}
        doc_id_matches = {}

        for word in keyword_list:
            result_counts[word] = result_counts.get(word, 0) + 1
            word_id_result = cursor.execute("SELECT word_id FROM lexicon WHERE word = ?", (word,)).fetchone()

            if word_id_result:
                word_id = word_id_result[0]
                for (doc_id,) in cursor.execute("SELECT doc_id FROM inverted_index WHERE word_id = ?", (word_id,)):
                    doc_id_matches[doc_id] = doc_id_matches.get(doc_id, 0) + 1

        search_results = []
        total_results = 0

        if doc_id_matches:
            placeholders = ','.join('?' * len(doc_id_matches))
            results = cursor.execute(
                f"SELECT doc_id, url, title, page_rank FROM doc_index WHERE doc_id IN ({placeholders})",
                list(doc_id_matches.keys())
            ).fetchall()

            sorted_results = sorted(results, key=lambda x: (-doc_id_matches[x[0]], -x[3]))
            total_results = len(sorted_results)

            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_results = sorted_results[start_idx:end_idx]

            search_results = [
                SearchResult(
                    url=url,
                    title=title if title else url,
                    rank=idx,
                    match_count=doc_id_matches[doc_id]
                )
                for idx, (doc_id, url, title, _) in enumerate(page_results, start_idx + 1)
            ]

        conn.close()
        return search_results, result_counts, total_results